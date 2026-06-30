"""
qoodev fuzz testing — sensor noise injection and physics parameter perturbation robustness testing.

对标：OSS-Fuzz + AFL
提供传感器噪声注入、物理参数扰动、边界值测试、崩溃检测。
"""

from __future__ import annotations

import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FuzzStrategy(str, Enum):
    RANDOM = "random"  # uniform random within bounds
    BOUNDARY = "boundary"  # min/max/zero/NaN/Inf
    MUTATION = "mutation"  # small perturbations of valid inputs
    ADVERSARIAL = "adversarial"  # gradient-guided perturbations


class NoiseDistribution(str, Enum):
    UNIFORM = "uniform"
    GAUSSIAN = "gaussian"
    LAPLACE = "laplace"
    IMPULSE = "impulse"  # spike noise
    DRIFT = "drift"  # gradual bias drift


class Severity(str, Enum):
    CRASH = "crash"  # process terminated
    HANG = "hang"  # timeout
    ASSERTION = "assertion"  # assertion failure
    INVALID_OUTPUT = "invalid_output"  # NaN/Inf in output
    DEGRADED = "degraded"  # significant accuracy drop
    PASS = "pass"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FuzzConfig:
    """Configuration for a single fuzzing parameter."""
    name: str
    min_val: float
    max_val: float
    strategy: FuzzStrategy = FuzzStrategy.RANDOM
    distribution: NoiseDistribution = NoiseDistribution.UNIFORM
    mutation_rate: float = 0.1  # for MUTATION strategy


@dataclass
class FuzzResult:
    """Result of a single fuzz iteration."""
    iteration: int
    severity: Severity
    input_params: Dict[str, float]
    output: Any = None
    error_message: str = ""
    execution_time_ms: float = 0.0
    stack_trace: str = ""


@dataclass
class FuzzReport:
    """Aggregated fuzzing report."""
    total_iterations: int
    crashes: int = 0
    hangs: int = 0
    assertion_failures: int = 0
    invalid_outputs: int = 0
    degraded: int = 0
    passed: int = 0
    results: List[FuzzResult] = field(default_factory=list)
    coverage: Dict[str, int] = field(default_factory=dict)
    duration_s: float = 0.0


# ---------------------------------------------------------------------------
# Fuzzers
# ---------------------------------------------------------------------------

class SensorNoiseFuzzer:
    """Inject various noise types into sensor data streams."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = np.random.default_rng(seed)

    def inject_noise(
        self,
        data: np.ndarray,
        noise_type: NoiseDistribution,
        intensity: float = 0.1,
        probability: float = 0.3,
    ) -> np.ndarray:
        """Apply noise injection to sensor data."""
        result = data.astype(np.float32)

        if noise_type == NoiseDistribution.GAUSSIAN:
            noise = self._rng.normal(0, intensity * result.std(), result.shape)
            mask = self._rng.random(result.shape) < probability
            result[mask] += noise[mask]

        elif noise_type == NoiseDistribution.UNIFORM:
            noise = self._rng.uniform(-intensity, intensity, result.shape)
            mask = self._rng.random(result.shape) < probability
            result[mask] += noise[mask] * result[mask]

        elif noise_type == NoiseDistribution.LAPLACE:
            noise = self._rng.laplace(0, intensity, result.shape)
            mask = self._rng.random(result.shape) < probability
            result[mask] += noise[mask]

        elif noise_type == NoiseDistribution.IMPULSE:
            # spike noise: set random pixels to extreme values
            mask = self._rng.random(result.shape) < probability
            result[mask] = self._rng.choice([result.max() * 2, -result.max() * 2], size=mask.sum())

        elif noise_type == NoiseDistribution.DRIFT:
            # gradual bias drift along time axis
            if result.ndim >= 2:
                drift = np.linspace(0, intensity, result.shape[0])[:, np.newaxis]
                result = result + drift

        return result

    def dropout_sensor(self, data: np.ndarray, dropout_prob: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        """Simulate sensor dropout — return (data, dropout_mask)."""
        mask = self._rng.random(data.shape) > dropout_prob
        return data * mask, mask

    def delay_sensor(self, data: np.ndarray, max_delay_frames: int = 5) -> np.ndarray:
        """Simulate sensor latency by shifting frames."""
        delay = self._rng.integers(0, max_delay_frames + 1)
        if delay == 0:
            return data
        delayed = np.roll(data, delay, axis=0)
        delayed[:delay] = 0
        return delayed


class PhysicsFuzzer:
    """Perturb physics parameters for robustness testing."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = np.random.default_rng(seed)

    # Common physics parameters to fuzz
    DEFAULT_PARAMS = [
        FuzzConfig("gravity", 0.0, 20.0, strategy=FuzzStrategy.BOUNDARY),
        FuzzConfig("friction_coefficient", 0.0, 2.0),
        FuzzConfig("restitution", 0.0, 1.0),
        FuzzConfig("joint_damping", 0.0, 100.0),
        FuzzConfig("joint_stiffness", 0.0, 10000.0),
        FuzzConfig("actuator_force_max", 0.0, 1000.0),
        FuzzConfig("sensor_noise_std", 0.0, 0.5),
        FuzzConfig("timestep_s", 0.0001, 0.1, strategy=FuzzStrategy.BOUNDARY),
        FuzzConfig("mass_scale", 0.1, 10.0),
        FuzzConfig("inertia_scale", 0.1, 10.0),
    ]

    def generate_perturbation(
        self,
        params: List[FuzzConfig],
        strategy: FuzzStrategy = FuzzStrategy.RANDOM,
    ) -> Dict[str, float]:
        """Generate a set of perturbed physics parameters."""
        result: Dict[str, float] = {}
        for param in params:
            if strategy == FuzzStrategy.RANDOM:
                result[param.name] = self._rng.uniform(param.min_val, param.max_val)
            elif strategy == FuzzStrategy.BOUNDARY:
                boundaries = [param.min_val, param.max_val, 0.0, float("nan"), float("inf")]
                result[param.name] = boundaries[self._rng.integers(0, len(boundaries))]
            elif strategy == FuzzStrategy.MUTATION:
                base = (param.min_val + param.max_val) / 2
                result[param.name] = base + self._rng.normal(0, param.mutation_rate * (param.max_val - param.min_val))
        return result

    def generate_adversarial_perturbation(
        self,
        params: List[FuzzConfig],
        gradient_fn: Callable[[Dict[str, float]], Dict[str, float]],
        epsilon: float = 0.01,
        iterations: int = 10,
    ) -> Dict[str, float]:
        """Generate adversarial perturbation using gradient signals."""
        current = {p.name: (p.min_val + p.max_val) / 2 for p in params}

        for _ in range(iterations):
            grads = gradient_fn(current)
            for p in params:
                if p.name in grads:
                    current[p.name] += epsilon * np.sign(grads[p.name])
                    current[p.name] = np.clip(current[p.name], p.min_val, p.max_val)

        return current


# ---------------------------------------------------------------------------
# FuzzRunner
# ---------------------------------------------------------------------------

class FuzzRunner:
    """Orchestrate fuzzing campaigns.

    Usage::

        runner = FuzzRunner(target_fn=my_controller, timeout_per_test_s=5.0)
        runner.add_param(FuzzConfig("sensor_gain", 0.1, 10.0))
        report = runner.run(iterations=1000)
    """

    def __init__(
        self,
        target_fn: Callable[..., Any],
        timeout_per_test_s: float = 10.0,
        seed: Optional[int] = None,
    ):
        self.target_fn = target_fn
        self.timeout_s = timeout_per_test_s
        self._rng = np.random.default_rng(seed)
        self._params: List[FuzzConfig] = []
        self._assertion_checks: List[Callable[[Any], bool]] = []
        self._output_validators: List[Callable[[Any], bool]] = []

    def add_param(self, param: FuzzConfig) -> None:
        self._params.append(param)

    def add_params(self, params: List[FuzzConfig]) -> None:
        self._params.extend(params)

    def add_assertion_check(self, check: Callable[[Any], bool]) -> None:
        self._assertion_checks.append(check)

    def add_output_validator(self, validator: Callable[[Any], bool]) -> None:
        self._output_validators.append(validator)

    def run(
        self,
        iterations: int = 1000,
        strategy: FuzzStrategy = FuzzStrategy.RANDOM,
    ) -> FuzzReport:
        """Execute fuzzing campaign."""
        report = FuzzReport(total_iterations=iterations)
        t_start = time.perf_counter()

        for i in range(iterations):
            # generate input
            inputs = {p.name: self._rng.uniform(p.min_val, p.max_val) for p in self._params}

            t0 = time.perf_counter()
            try:
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError("Fuzz test timed out")

                # set timeout
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(self.timeout_s))

                output = self.target_fn(**inputs)
                signal.alarm(0)

                elapsed_ms = (time.perf_counter() - t0) * 1000

                # check assertions
                assertion_failed = False
                for check in self._assertion_checks:
                    if not check(output):
                        assertion_failed = True
                        break

                if assertion_failed:
                    result = FuzzResult(
                        iteration=i, severity=Severity.ASSERTION,
                        input_params=inputs, output=output,
                        execution_time_ms=elapsed_ms,
                    )
                    report.assertion_failures += 1
                else:
                    # validate output
                    valid = True
                    for validator in self._output_validators:
                        if not validator(output):
                            valid = False
                            break

                    if not valid:
                        result = FuzzResult(
                            iteration=i, severity=Severity.INVALID_OUTPUT,
                            input_params=inputs, output=output,
                            execution_time_ms=elapsed_ms,
                        )
                        report.invalid_outputs += 1
                    else:
                        result = FuzzResult(
                            iteration=i, severity=Severity.PASS,
                            input_params=inputs, output=output,
                            execution_time_ms=elapsed_ms,
                        )
                        report.passed += 1

            except TimeoutError:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                result = FuzzResult(
                    iteration=i, severity=Severity.HANG,
                    input_params=inputs,
                    error_message="Test timed out",
                    execution_time_ms=elapsed_ms,
                )
                report.hangs += 1

            except Exception as e:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                result = FuzzResult(
                    iteration=i, severity=Severity.CRASH,
                    input_params=inputs,
                    error_message=str(e),
                    execution_time_ms=elapsed_ms,
                    stack_trace=traceback.format_exc(),
                )
                report.crashes += 1

            report.results.append(result)

        report.duration_s = time.perf_counter() - t_start

        # simple coverage: count unique parameter combinations
        coverage_set = set()
        for r in report.results:
            for k, v in r.input_params.items():
                coverage_set.add(f"{k}:{v:.3f}")
        report.coverage = {"unique_param_values": len(coverage_set)}

        return report

    def print_report(self, report: FuzzReport) -> None:
        """Print human-readable fuzz report."""
        print(f"""
╔══════════════════════════════════════════╗
║          Fuzz Testing Report             ║
╠══════════════════════════════════════════╣
║ Total Iterations:  {report.total_iterations:>6}                ║
║ Duration:          {report.duration_s:>6.1f}s               ║
╠══════════════════════════════════════════╣
║ ✅ Passed:         {report.passed:>6}                ║
║ 💀 Crashes:        {report.crashes:>6}                ║
║ ⏱️  Hangs:          {report.hangs:>6}                ║
║ ❗ Assertions:      {report.assertion_failures:>6}                ║
║ ⚠️  Invalid Output:  {report.invalid_outputs:>6}                ║
║ 📉 Degraded:        {report.degraded:>6}                ║
╚══════════════════════════════════════════╝
""")

        # print crash details
        crashes = [r for r in report.results if r.severity == Severity.CRASH]
        if crashes:
            print("\n=== Crash Details ===")
            for c in crashes[:5]:
                print(f"  Iteration {c.iteration}: {c.error_message}")
                print(f"    Inputs: {c.input_params}")
                if c.stack_trace:
                    print(f"    Trace: {c.stack_trace[:200]}...")


# ---------------------------------------------------------------------------
# Pre-built validators
# ---------------------------------------------------------------------------

def no_nan_inf_validator(output: Any) -> bool:
    """Check output contains no NaN or Inf."""
    if isinstance(output, np.ndarray):
        return bool(np.all(np.isfinite(output)))
    if isinstance(output, (list, tuple)):
        return all(no_nan_inf_validator(o) for o in output)
    return True


def bounded_output_validator(low: float, high: float) -> Callable[[Any], bool]:
    """Check output is within bounds."""
    def validator(output: Any) -> bool:
        if isinstance(output, np.ndarray):
            return bool(np.all((output >= low) & (output <= high)))
        return True
    return validator


def tensor_shape_validator(expected_shape: Tuple[int, ...]) -> Callable[[Any], bool]:
    """Check output tensor has expected shape."""
    def validator(output: Any) -> bool:
        if isinstance(output, np.ndarray):
            return output.shape == expected_shape
        return True
    return validator
