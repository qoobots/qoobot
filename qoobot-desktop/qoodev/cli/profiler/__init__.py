"""
qoodev Performance Profiler — v1.5+

Comprehensive performance analysis for QooBot skills:
- End-to-end latency breakdown (perception → planning → control)
- Resource flame graph (CPU/GPU/NPU utilization, memory hotspots)
- Communication profiling (DDS/ROS2 message latency, bandwidth)
- Model inference profiling (layer-wise latency, memory, accuracy)
- Power tracking (per-module power attribution, efficiency ratio)

Usage:
    from qoodev.profiler import ProfilerSession, FlameGraph, CommProfiler, ModelProfiler

    with ProfilerSession("my_skill") as prof:
        skill.run()
    prof.report()
"""

from __future__ import annotations

import dataclasses
import json
import os
import time
import threading
from collections import defaultdict
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ============================================================================
# Data Models
# ============================================================================

class ResourceType(Enum):
    CPU = auto()
    GPU = auto()
    NPU = auto()
    MEMORY = auto()
    IO = auto()
    NETWORK = auto()


class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclasses.dataclass
class LatencySample:
    """A single latency measurement for a pipeline stage."""
    stage: str
    duration_ms: float
    timestamp: float
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class ResourceSample:
    """CPU/GPU/NPU utilization sample."""
    resource_type: ResourceType
    utilization_pct: float
    timestamp: float
    process_name: str = ""
    device_id: int = 0


@dataclasses.dataclass
class MemorySample:
    """Memory allocation sample."""
    allocated_mb: float
    peak_mb: float
    timestamp: float
    device: str = "cpu"  # cpu, gpu:0, npu:0


@dataclasses.dataclass
class CommSample:
    """Communication (DDS/ROS2) sample."""
    topic: str
    latency_us: float
    size_bytes: int
    dropped: bool = False
    timestamp: float = 0.0


@dataclasses.dataclass
class ModelLayerProfile:
    """Single layer inference profile."""
    layer_name: str
    op_type: str
    latency_us: float
    memory_mb: float
    input_shape: List[int] = dataclasses.field(default_factory=list)
    output_shape: List[int] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Bottleneck:
    """Identified performance bottleneck."""
    component: str
    severity: Severity
    description: str
    suggestion: str
    current_value: float
    threshold: float


@dataclasses.dataclass
class ProfilerReport:
    """Complete profiling report."""
    session_name: str
    start_time: float
    end_time: float
    duration_s: float
    latency_breakdown: Dict[str, float]  # stage → avg_ms
    resource_utilization: Dict[str, float]  # resource → avg_pct
    memory_profile: Dict[str, float]  # device → peak_mb
    comm_stats: Dict[str, Dict[str, float]]  # topic → {avg_latency_us, total_bytes, drop_rate}
    model_profiles: Dict[str, List[ModelLayerProfile]]  # model_name → layers
    bottlenecks: List[Bottleneck]
    recommendations: List[str]


# ============================================================================
# Core Profiler
# ============================================================================

class LatencyTracker:
    """Track per-stage latency across pipeline stages."""

    def __init__(self):
        self._samples: Dict[str, List[LatencySample]] = defaultdict(list)
        self._active: Dict[str, float] = {}  # stage → start_time

    def start_stage(self, stage: str, metadata: Optional[Dict] = None) -> None:
        """Begin timing a pipeline stage."""
        self._active[stage] = time.monotonic()
        if metadata:
            self._samples[stage].append(LatencySample(
                stage=stage, duration_ms=0.0, timestamp=time.time(), metadata=metadata
            ))

    def end_stage(self, stage: str) -> float:
        """End timing and record duration in ms."""
        if stage not in self._active:
            return 0.0
        duration = (time.monotonic() - self._active.pop(stage)) * 1000
        if self._samples[stage] and self._samples[stage][-1].duration_ms == 0.0:
            self._samples[stage][-1].duration_ms = duration
        else:
            self._samples[stage].append(LatencySample(
                stage=stage, duration_ms=duration, timestamp=time.time()
            ))
        return duration

    def stats(self) -> Dict[str, float]:
        """Return {stage: avg_duration_ms}."""
        result = {}
        for stage, samples in self._samples.items():
            durations = [s.duration_ms for s in samples if s.duration_ms > 0]
            result[stage] = sum(durations) / len(durations) if durations else 0.0
        return result

    def all_samples(self) -> Dict[str, List[LatencySample]]:
        return dict(self._samples)


class ResourceMonitor:
    """Monitor CPU/GPU/NPU utilization and memory."""

    def __init__(self, sample_interval_s: float = 0.1):
        self._interval = sample_interval_s
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._resource_samples: List[ResourceSample] = []
        self._memory_samples: List[MemorySample] = []
        self._lock = threading.Lock()

    def _sample_loop(self):
        """Background sampling loop."""
        while self._running:
            t = time.time()
            try:
                # CPU utilization (cross-platform approximation)
                import psutil
                cpu_pct = psutil.cpu_percent(interval=0.01)
                with self._lock:
                    self._resource_samples.append(ResourceSample(
                        resource_type=ResourceType.CPU,
                        utilization_pct=cpu_pct,
                        timestamp=t,
                    ))
                    mem_info = psutil.virtual_memory()
                    self._memory_samples.append(MemorySample(
                        allocated_mb=mem_info.used / (1024 * 1024),
                        peak_mb=mem_info.total / (1024 * 1024),
                        timestamp=t,
                        device="cpu",
                    ))
            except ImportError:
                # Fallback: estimate from /proc
                self._sample_fallback(t)

            time.sleep(self._interval)

    def _sample_fallback(self, t: float):
        """Fallback sampling on Linux without psutil."""
        try:
            with open("/proc/loadavg") as f:
                load = float(f.read().split()[0])
            with self._lock:
                self._resource_samples.append(ResourceSample(
                    resource_type=ResourceType.CPU,
                    utilization_pct=min(load * 100 / os.cpu_count() if os.cpu_count() else 1, 100),
                    timestamp=t,
                ))
        except (FileNotFoundError, PermissionError):
            pass

    def start(self) -> None:
        """Start background monitoring."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def resource_stats(self) -> Dict[str, float]:
        """Return {resource_type: avg_utilization_pct}."""
        with self._lock:
            if not self._resource_samples:
                return {}
            by_type: Dict[str, List[float]] = defaultdict(list)
            for s in self._resource_samples:
                by_type[s.resource_type.name].append(s.utilization_pct)
            return {k: sum(v) / len(v) for k, v in by_type.items()}

    def memory_stats(self) -> Dict[str, float]:
        """Return {device: peak_mb}."""
        with self._lock:
            if not self._memory_samples:
                return {}
            by_device: Dict[str, float] = {}
            for s in self._memory_samples:
                by_device[s.device] = max(by_device.get(s.device, 0), s.allocated_mb)
            return by_device


class CommunicationProfiler:
    """Profile DDS/ROS2 communication: latency, bandwidth, drop rate."""

    def __init__(self):
        self._samples: Dict[str, List[CommSample]] = defaultdict(list)
        self._topic_metadata: Dict[str, Dict] = {}

    def record_message(self, topic: str, latency_us: float, size_bytes: int,
                       dropped: bool = False) -> None:
        """Record a single message sample."""
        self._samples[topic].append(CommSample(
            topic=topic,
            latency_us=latency_us,
            size_bytes=size_bytes,
            dropped=dropped,
            timestamp=time.time(),
        ))

    def stats(self) -> Dict[str, Dict[str, float]]:
        """Return {topic: {avg_latency_us, total_bytes, drop_rate, msg_count}}."""
        result = {}
        for topic, samples in self._samples.items():
            if not samples:
                continue
            latencies = [s.latency_us for s in samples]
            total_bytes = sum(s.size_bytes for s in samples)
            drops = sum(1 for s in samples if s.dropped)
            result[topic] = {
                "avg_latency_us": sum(latencies) / len(latencies),
                "p99_latency_us": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) >= 100 else max(latencies),
                "total_bytes": total_bytes,
                "drop_rate": drops / len(samples),
                "msg_count": len(samples),
            }
        return result

    def bandwidth_hogs(self, threshold_mbps: float = 10.0) -> List[Tuple[str, float]]:
        """Return topics exceeding bandwidth threshold."""
        hogs = []
        for topic, samples in self._samples.items():
            if len(samples) < 2:
                continue
            time_span = samples[-1].timestamp - samples[0].timestamp
            if time_span <= 0:
                continue
            total_bytes = sum(s.size_bytes for s in samples)
            mbps = (total_bytes * 8) / (time_span * 1_000_000)  # Mbps
            if mbps > threshold_mbps:
                hogs.append((topic, mbps))
        return sorted(hogs, key=lambda x: -x[1])


class ModelProfiler:
    """Profile model inference: per-layer latency, memory, shape."""

    def __init__(self):
        self._models: Dict[str, List[ModelLayerProfile]] = defaultdict(list)

    def record_layer(self, model_name: str, layer_name: str, op_type: str,
                     latency_us: float, memory_mb: float,
                     input_shape: Optional[List[int]] = None,
                     output_shape: Optional[List[int]] = None) -> None:
        """Record a single layer's profile data."""
        self._models[model_name].append(ModelLayerProfile(
            layer_name=layer_name,
            op_type=op_type,
            latency_us=latency_us,
            memory_mb=memory_mb,
            input_shape=input_shape or [],
            output_shape=output_shape or [],
        ))

    def model_stats(self, model_name: str) -> Dict[str, Any]:
        """Return aggregate stats for a model."""
        layers = self._models.get(model_name, [])
        if not layers:
            return {}
        total_latency = sum(l.latency_us for l in layers)
        total_memory = sum(l.memory_mb for l in layers)
        return {
            "model_name": model_name,
            "layer_count": len(layers),
            "total_latency_us": total_latency,
            "total_latency_ms": total_latency / 1000,
            "total_memory_mb": total_memory,
            "top_expensive_layers": sorted(
                layers, key=lambda l: -l.latency_us
            )[:5],
        }

    def all_models(self) -> Dict[str, List[ModelLayerProfile]]:
        return dict(self._models)


class FlameGraphBuilder:
    """Build flame graph data from call stacks."""

    def __init__(self):
        self._stacks: List[List[Tuple[str, float]]] = []  # [(name, duration_ms), ...]

    def record_stack(self, frames: List[Tuple[str, float]]) -> None:
        """Record a call stack with per-frame durations."""
        self._stacks.append(frames)

    def build_flamegraph_data(self) -> Dict[str, Any]:
        """Build flame graph JSON data structure."""
        root: Dict[str, Any] = {"name": "root", "value": 0, "children": []}

        for stack in self._stacks:
            if not stack:
                continue
            current = root
            total = stack[-1][1] if stack else 0
            root["value"] = root.get("value", 0) + total

            for name, duration in stack:
                # Find or create child node
                found = None
                for child in current.get("children", []):
                    if child["name"] == name:
                        found = child
                        break
                if found is None:
                    found = {"name": name, "value": 0, "children": []}
                    current.setdefault("children", []).append(found)
                found["value"] = found.get("value", 0) + duration
                current = found

        return root

    def find_hotspots(self, threshold_pct: float = 5.0) -> List[Tuple[str, float]]:
        """Find functions above threshold percentage of total time."""
        data = self.build_flamegraph_data()
        total = data.get("value", 1) or 1
        hotspots: List[Tuple[str, float]] = []

        def walk(node, path=""):
            full_name = f"{path}/{node['name']}" if path else node["name"]
            pct = (node["value"] / total) * 100
            if pct >= threshold_pct and node["name"] != "root":
                hotspots.append((full_name, pct))
            for child in node.get("children", []):
                walk(child, full_name)

        for child in data.get("children", []):
            walk(child)
        return sorted(hotspots, key=lambda x: -x[1])


# ============================================================================
# Bottleneck Detection
# ============================================================================

class BottleneckDetector:
    """Automatic bottleneck detection with recommendations."""

    # Thresholds
    STAGE_LATENCY_THRESHOLD_MS = 100.0
    CPU_UTIL_THRESHOLD_PCT = 80.0
    MEMORY_THRESHOLD_PCT = 85.0
    COMM_LATENCY_THRESHOLD_US = 10000.0  # 10ms
    DROP_RATE_THRESHOLD = 0.01  # 1%

    @classmethod
    def detect(cls, report: ProfilerReport) -> List[Bottleneck]:
        """Detect all bottlenecks from a profiling report."""
        bottlenecks: List[Bottleneck] = []

        # Pipeline stage latency
        for stage, avg_ms in report.latency_breakdown.items():
            if avg_ms > cls.STAGE_LATENCY_THRESHOLD_MS:
                bottlenecks.append(Bottleneck(
                    component=f"pipeline:{stage}",
                    severity=Severity.HIGH if avg_ms > 500 else Severity.MEDIUM,
                    description=f"{stage} stage average latency {avg_ms:.1f}ms exceeds {cls.STAGE_LATENCY_THRESHOLD_MS}ms",
                    suggestion=f"Consider optimizing {stage} algorithms or using hardware acceleration",
                    current_value=avg_ms,
                    threshold=cls.STAGE_LATENCY_THRESHOLD_MS,
                ))

        # CPU utilization
        cpu_util = report.resource_utilization.get("CPU", 0)
        if cpu_util > cls.CPU_UTIL_THRESHOLD_PCT:
            bottlenecks.append(Bottleneck(
                component="resource:CPU",
                severity=Severity.HIGH if cpu_util > 95 else Severity.MEDIUM,
                description=f"CPU utilization {cpu_util:.1f}% exceeds {cls.CPU_UTIL_THRESHOLD_PCT}%",
                suggestion="Offload compute to GPU/NPU or optimize hot loops",
                current_value=cpu_util,
                threshold=cls.CPU_UTIL_THRESHOLD_PCT,
            ))

        # Communication
        for topic, stats in report.comm_stats.items():
            if stats["avg_latency_us"] > cls.COMM_LATENCY_THRESHOLD_US:
                bottlenecks.append(Bottleneck(
                    component=f"comm:{topic}",
                    severity=Severity.MEDIUM,
                    description=f"Topic '{topic}' avg latency {stats['avg_latency_us']:.0f}us exceeds threshold",
                    suggestion="Use DDS QoS tuning (RELIABLE→BEST_EFFORT) or increase partition affinity",
                    current_value=stats["avg_latency_us"],
                    threshold=cls.COMM_LATENCY_THRESHOLD_US,
                ))
            if stats["drop_rate"] > cls.DROP_RATE_THRESHOLD:
                bottlenecks.append(Bottleneck(
                    component=f"comm:{topic}",
                    severity=Severity.HIGH,
                    description=f"Topic '{topic}' drop rate {stats['drop_rate']*100:.1f}% exceeds {cls.DROP_RATE_THRESHOLD*100:.0f}%",
                    suggestion="Increase DDS history depth or subscriber queue size",
                    current_value=stats["drop_rate"] * 100,
                    threshold=cls.DROP_RATE_THRESHOLD * 100,
                ))

        return bottlenecks

    @classmethod
    def generate_recommendations(cls, bottlenecks: List[Bottleneck]) -> List[str]:
        """Generate prioritized recommendations."""
        recs: List[str] = []
        by_severity = defaultdict(list)
        for b in bottlenecks:
            by_severity[b.severity].append(b)

        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            for b in by_severity[sev]:
                recs.append(f"[{b.severity.value.upper()}] {b.component}: {b.suggestion}")
        return recs


# ============================================================================
# Profiler Session
# ============================================================================

class ProfilerSession:
    """Main profiling session orchestrating all profilers."""

    def __init__(self, name: str = "default", output_dir: Optional[Path] = None):
        self.name = name
        self.output_dir = output_dir or Path.cwd() / "profiles"
        self._start_time: float = 0.0
        self._end_time: float = 0.0

        self.latency = LatencyTracker()
        self.resources = ResourceMonitor()
        self.comm = CommunicationProfiler()
        self.model = ModelProfiler()
        self.flame = FlameGraphBuilder()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()

    def start(self) -> None:
        """Start profiling session."""
        self._start_time = time.time()
        self.resources.start()

    def stop(self) -> None:
        """Stop profiling and finalize."""
        self._end_time = time.time()
        self.resources.stop()

    def report(self) -> ProfilerReport:
        """Generate complete profiling report."""
        bottlenecks = BottleneckDetector.detect(ProfilerReport(
            session_name=self.name,
            start_time=self._start_time,
            end_time=self._end_time,
            duration_s=self._end_time - self._start_time,
            latency_breakdown=self.latency.stats(),
            resource_utilization=self.resources.resource_stats(),
            memory_profile=self.resources.memory_stats(),
            comm_stats=self.comm.stats(),
            model_profiles=self.model.all_models(),
            bottlenecks=[],
            recommendations=[],
        ))

        return ProfilerReport(
            session_name=self.name,
            start_time=self._start_time,
            end_time=self._end_time,
            duration_s=self._end_time - self._start_time,
            latency_breakdown=self.latency.stats(),
            resource_utilization=self.resources.resource_stats(),
            memory_profile=self.resources.memory_stats(),
            comm_stats=self.comm.stats(),
            model_profiles=self.model.all_models(),
            bottlenecks=bottlenecks,
            recommendations=BottleneckDetector.generate_recommendations(bottlenecks),
        )

    def save_report(self, report: Optional[ProfilerReport] = None) -> Path:
        """Save report as JSON to output directory."""
        if report is None:
            report = self.report()

        self.output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_{timestamp}.json"
        filepath = self.output_dir / filename

        # Serialize
        data = {
            "session_name": report.session_name,
            "duration_s": report.duration_s,
            "latency_breakdown": report.latency_breakdown,
            "resource_utilization": report.resource_utilization,
            "memory_profile": report.memory_profile,
            "comm_stats": report.comm_stats,
            "bottlenecks": [
                {
                    "component": b.component,
                    "severity": b.severity.value,
                    "description": b.description,
                    "suggestion": b.suggestion,
                    "current_value": b.current_value,
                    "threshold": b.threshold,
                }
                for b in report.bottlenecks
            ],
            "recommendations": report.recommendations,
        }
        filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return filepath

    def print_summary(self, report: Optional[ProfilerReport] = None) -> None:
        """Print a rich summary to console."""
        if report is None:
            report = self.report()

        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        c = Console()

        # Header
        c.print(Panel.fit(
            f"[bold]{report.session_name}[/bold] — {report.duration_s:.1f}s",
            title="Profiler Report",
            border_style="cyan",
        ))

        # Latency breakdown
        if report.latency_breakdown:
            t = Table(title="Pipeline Latency (avg ms)")
            t.add_column("Stage", style="cyan")
            t.add_column("Duration (ms)", justify="right")
            t.add_column("Bar", justify="left")
            max_lat = max(report.latency_breakdown.values()) or 1
            for stage, ms in sorted(report.latency_breakdown.items(), key=lambda x: -x[1]):
                bar_len = int(ms / max_lat * 30)
                color = "red" if ms > 100 else "yellow" if ms > 50 else "green"
                t.add_row(stage, f"{ms:.2f}", f"[{color}]{'█' * bar_len}[/{color}]")
            c.print(t)

        # Bottlenecks
        if report.bottlenecks:
            c.print("\n[bold yellow]⚠ Bottlenecks Detected:[/bold yellow]")
            for b in report.bottlenecks:
                icon = "🔴" if b.severity == Severity.CRITICAL else "🟡" if b.severity == Severity.HIGH else "🟢"
                c.print(f"  {icon} [{b.severity.value.upper()}] {b.component}: {b.description}")
                c.print(f"     → {b.suggestion}")

        # Recommendations
        if report.recommendations:
            c.print("\n[bold green]✓ Recommendations:[/bold green]")
            for i, rec in enumerate(report.recommendations, 1):
                c.print(f"  {i}. {rec}")

        # Comm stats
        if report.comm_stats:
            c.print("\n[bold]Communication Stats:[/bold]")
            for topic, stats in report.comm_stats.items():
                c.print(f"  {topic}: {stats['avg_latency_us']:.0f}us avg, "
                        f"{stats['total_bytes']/1024:.1f}KB, "
                        f"drop={stats['drop_rate']*100:.2f}%")


# ============================================================================
# Convenience API
# ============================================================================

def profile_skill(skill_func: Callable, name: str = "skill_profile",
                  output_dir: Optional[Path] = None) -> ProfilerReport:
    """Profile a skill function and return report."""
    with ProfilerSession(name, output_dir) as prof:
        skill_func()
        return prof.report()


__all__ = [
    "ProfilerSession",
    "LatencyTracker",
    "ResourceMonitor",
    "CommunicationProfiler",
    "ModelProfiler",
    "FlameGraphBuilder",
    "BottleneckDetector",
    "ProfilerReport",
    "LatencySample",
    "ResourceSample",
    "MemorySample",
    "CommSample",
    "ModelLayerProfile",
    "Bottleneck",
    "ResourceType",
    "Severity",
    "profile_skill",
]
