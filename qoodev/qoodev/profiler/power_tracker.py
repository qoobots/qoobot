"""
qoodev power tracking — per-module power attribution and energy efficiency analysis.

对标：Instruments Energy Log + Android Battery Historian
提供模块级功耗归因、能效比（TOPS/W）计算、热节流监测。
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

import psutil  # type: ignore


# ---------------------------------------------------------------------------
# Enums & data structures
# ---------------------------------------------------------------------------

class PowerDomain(str, Enum):
    CPU = "cpu"
    GPU = "gpu"
    NPU = "npu"
    MEMORY = "memory"
    IO = "io"
    NETWORK = "network"
    TOTAL = "total"


class ThermalState(str, Enum):
    NOMINAL = "nominal"
    FAIR = "fair"
    SERIOUS = "serious"
    CRITICAL = "critical"


@dataclass
class PowerSample:
    timestamp: float
    domain: PowerDomain
    power_mw: float
    temperature_c: float = 0.0
    utilization_pct: float = 0.0


@dataclass
class ModulePowerProfile:
    """Power attribution for a single module."""
    module_name: str
    avg_power_mw: float = 0.0
    peak_power_mw: float = 0.0
    total_energy_mj: float = 0.0
    duty_cycle_pct: float = 0.0
    samples: List[PowerSample] = field(default_factory=list)


@dataclass
class PowerSession:
    """Aggregated power report for a profiling session."""
    session_id: str
    duration_s: float = 0.0
    modules: Dict[str, ModulePowerProfile] = field(default_factory=dict)
    domain_totals: Dict[PowerDomain, float] = field(default_factory=dict)
    thermal_history: List[Tuple[float, ThermalState]] = field(default_factory=list)
    tops_per_watt: float = 0.0


# ---------------------------------------------------------------------------
# PowerTracker
# ---------------------------------------------------------------------------

class PowerTracker:
    """Continuously samples power across domains and attributes to modules.

    Usage::

        tracker = PowerTracker(sample_interval_ms=100)
        tracker.start()
        tracker.register_module("perception_pipeline")
        # ... run workload ...
        session = tracker.stop()
        print(f"TOPS/W: {session.tops_per_watt:.2f}")
    """

    def __init__(self, sample_interval_ms: int = 100):
        self._interval = sample_interval_ms / 1000.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._samples: List[PowerSample] = []
        self._active_modules: Dict[str, float] = {}  # module_name -> start_time
        self._module_samples: Dict[str, List[PowerSample]] = defaultdict(list)
        self._thermal_state: ThermalState = ThermalState.NOMINAL
        self._thermal_history: List[Tuple[float, ThermalState]] = []
        self._start_time: float = 0.0
        self._total_ops: int = 0  # for TOPS/W calculation
        self._lock = threading.Lock()

        # platform-specific power readers
        self._cpu_reader: Optional[Callable[[], float]] = None
        self._gpu_reader: Optional[Callable[[], float]] = None
        self._thermal_reader: Optional[Callable[[], float]] = None
        self._setup_readers()

    # -- platform readers ---------------------------------------------------

    def _setup_readers(self) -> None:
        """Detect and configure platform-specific power/thermal readers."""
        import platform

        system = platform.system()

        # CPU power — use psutil as fallback
        self._cpu_reader = self._read_cpu_power_psutil

        # GPU power attempt
        try:
            if system == "Linux":
                # NVIDIA GPU via nvidia-smi
                import subprocess
                result = subprocess.run(["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                                        capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    self._gpu_reader = self._read_nvidia_power
        except Exception:
            pass

        # thermal
        self._thermal_reader = self._read_thermal_psutil

    def _read_cpu_power_psutil(self) -> float:
        """Estimate CPU power via utilization model."""
        cpu_pct = psutil.cpu_percent(interval=0)
        # rough model: TDP * utilization
        tdp = getattr(psutil, "cpu_tdp", 15000) if hasattr(psutil, "cpu_tdp") else 15000  # mW default
        return tdp * (cpu_pct / 100.0)

    def _read_nvidia_power(self) -> float:
        import subprocess
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=1,
            )
            return float(result.stdout.strip()) * 1000  # W -> mW
        except Exception:
            return 0.0

    def _read_thermal_psutil(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current > 0:
                        return entry.current
        except Exception:
            pass
        return 40.0  # fallback

    # -- module registration ------------------------------------------------

    def register_module(self, module_name: str) -> None:
        """Register an active module for power attribution."""
        with self._lock:
            self._active_modules[module_name] = time.perf_counter()

    def unregister_module(self, module_name: str) -> None:
        """Stop tracking a module."""
        with self._lock:
            if module_name in self._active_modules:
                start = self._active_modules.pop(module_name)
                # finalize module samples
                elapsed = time.perf_counter() - start
                self._module_samples[module_name].append(
                    PowerSample(timestamp=time.perf_counter(), domain=PowerDomain.CPU, power_mw=0, utilization_pct=elapsed)
                )

    def report_ops(self, module_name: str, ops_count: int) -> None:
        """Report operations completed by a module (for TOPS/W)."""
        self._total_ops += ops_count

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        self._running = True
        self._start_time = time.perf_counter()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> PowerSession:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

        end_time = time.perf_counter()
        duration_s = end_time - self._start_time
        session_id = time.strftime("%Y%m%d-%H%M%S")

        session = PowerSession(session_id=session_id, duration_s=duration_s)

        # aggregate by module
        with self._lock:
            for mod_name, mod_samples in self._module_samples.items():
                profile = ModulePowerProfile(module_name=mod_name)
                if mod_samples:
                    powers = [s.power_mw for s in mod_samples if s.power_mw > 0]
                    profile.avg_power_mw = sum(powers) / len(powers) if powers else 0
                    profile.peak_power_mw = max(powers) if powers else 0
                    profile.total_energy_mj = profile.avg_power_mw * duration_s / 1000.0  # mW*s -> mJ
                    profile.samples = mod_samples
                session.modules[mod_name] = profile

        # domain totals
        for sample in self._samples:
            session.domain_totals[sample.domain] = session.domain_totals.get(sample.domain, 0) + sample.power_mw

        # average domain totals
        for domain in session.domain_totals:
            session.domain_totals[domain] /= max(len(self._samples), 1)

        # thermal history
        session.thermal_history = list(self._thermal_history)

        # TOPS/W efficiency
        total_power_w = session.domain_totals.get(PowerDomain.TOTAL, 1) / 1000.0
        session.tops_per_watt = (self._total_ops / duration_s / 1e12) / total_power_w if total_power_w > 0 else 0

        return session

    # -- sampling loop ------------------------------------------------------

    def _sample_loop(self) -> None:
        while self._running:
            ts = time.perf_counter()

            cpu_power = self._cpu_reader() if self._cpu_reader else 0
            gpu_power = self._gpu_reader() if self._gpu_reader else 0
            temp = self._thermal_reader() if self._thermal_reader else 0

            with self._lock:
                self._samples.append(PowerSample(ts, PowerDomain.CPU, cpu_power, temperature_c=temp, utilization_pct=psutil.cpu_percent(interval=0)))
                if gpu_power > 0:
                    self._samples.append(PowerSample(ts, PowerDomain.GPU, gpu_power, temperature_c=temp))

                # attribute to active modules
                n_active = len(self._active_modules)
                if n_active > 0:
                    per_module = cpu_power / n_active
                    for mod_name in self._active_modules:
                        self._module_samples[mod_name].append(
                            PowerSample(ts, PowerDomain.CPU, per_module, temperature_c=temp, utilization_pct=psutil.cpu_percent(interval=0))
                        )

                # thermal state classification
                new_state = self._classify_thermal(temp)
                if new_state != self._thermal_state:
                    self._thermal_state = new_state
                    self._thermal_history.append((ts, new_state))

            time.sleep(self._interval)

    @staticmethod
    def _classify_thermal(temp_c: float) -> ThermalState:
        if temp_c < 60:
            return ThermalState.NOMINAL
        elif temp_c < 75:
            return ThermalState.FAIR
        elif temp_c < 90:
            return ThermalState.SERIOUS
        else:
            return ThermalState.CRITICAL

    # -- reporting ----------------------------------------------------------

    def generate_report(self, session: PowerSession) -> str:
        """Generate human-readable power report."""
        lines = [
            "# Power Analysis Report",
            f"Session: {session.session_id}",
            f"Duration: {session.duration_s:.2f} s",
            f"TOPS/W: {session.tops_per_watt:.4f}",
            "",
            "## Domain Breakdown",
        ]
        for domain, power_mw in sorted(session.domain_totals.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- **{domain.value}**: {power_mw:.1f} mW  ({power_mw/1000:.2f} W)")

        lines.append("\n## Module Attribution")
        for mod_name, profile in sorted(session.modules.items(), key=lambda x: x[1].avg_power_mw, reverse=True):
            lines.append(f"### {mod_name}")
            lines.append(f"- Avg Power: {profile.avg_power_mw:.1f} mW")
            lines.append(f"- Peak Power: {profile.peak_power_mw:.1f} mW")
            lines.append(f"- Total Energy: {profile.total_energy_mj:.2f} mJ")

        if session.thermal_history:
            lines.append("\n## Thermal History")
            for ts, state in session.thermal_history:
                elapsed = ts - self._start_time
                lines.append(f"- t={elapsed:.1f}s: **{state.value}**")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Energy efficiency scoring
# ---------------------------------------------------------------------------

class EfficiencyScorer:
    """Score model or pipeline energy efficiency."""

    @staticmethod
    def compute_efficiency_score(
        tops_per_watt: float,
        latency_ms: float,
        accuracy: float,
        target_tops_w: float = 1.0,
        target_latency_ms: float = 100.0,
        target_accuracy: float = 0.9,
    ) -> Dict[str, float]:
        """Compute weighted efficiency score (0–100)."""
        tops_score = min(tops_per_watt / target_tops_w * 40, 40) if target_tops_w > 0 else 0
        latency_score = max(0, (1 - latency_ms / target_latency_ms) * 30) if target_latency_ms > 0 else 0
        accuracy_score = accuracy / target_accuracy * 30 if target_accuracy > 0 else 0

        total = tops_score + latency_score + accuracy_score
        return {
            "total_score": round(total, 1),
            "tops_watt_score": round(tops_score, 1),
            "latency_score": round(latency_score, 1),
            "accuracy_score": round(accuracy_score, 1),
        }
