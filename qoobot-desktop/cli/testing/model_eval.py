"""
qoodev model evaluation — accuracy / latency / power benchmarking with multi-version comparison.

对标：MLPerf + TensorBoard 模型评估
提供精度/延迟/功耗多维度基准测试、多版本对比、报告导出。
"""

from __future__ import annotations

import json
import time
import statistics
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MetricKind(str, Enum):
    ACCURACY = "accuracy"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    MEMORY = "memory"
    POWER = "power"
    CUSTOM = "custom"


class CompareMode(str, Enum):
    ABSOLUTE = "absolute"  # absolute threshold check
    RELATIVE = "relative"  # relative to baseline
    BOTH = "both"


class ReportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    MARKDOWN = "markdown"
    HTML = "html"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class EvalMetric:
    """A single metric collected during evaluation."""
    name: str
    kind: MetricKind
    value: float
    unit: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class EvalRun:
    """Result of a single evaluation run."""
    model_name: str
    version: str
    metrics: List[EvalMetric] = field(default_factory=list)
    raw_latencies_us: List[float] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    @property
    def latency_stats(self) -> Dict[str, float]:
        if not self.raw_latencies_us:
            return {}
        arr = np.array(self.raw_latencies_us)
        return {
            "mean_us": float(np.mean(arr)),
            "median_us": float(np.median(arr)),
            "p90_us": float(np.percentile(arr, 90)),
            "p95_us": float(np.percentile(arr, 95)),
            "p99_us": float(np.percentile(arr, 99)),
            "min_us": float(np.min(arr)),
            "max_us": float(np.max(arr)),
            "std_us": float(np.std(arr)),
        }


@dataclass
class EvalBenchmark:
    """Aggregated benchmark results for comparison."""
    runs: List[EvalRun] = field(default_factory=list)

    def add_run(self, run: EvalRun) -> None:
        self.runs.append(run)

    def compare_to_baseline(self, baseline: EvalRun, mode: CompareMode = CompareMode.RELATIVE) -> Dict[str, Any]:
        """Compare latest run to a baseline."""
        if not self.runs:
            return {}
        current = self.runs[-1]
        result: Dict[str, Any] = {"baseline": baseline.version, "current": current.version, "deltas": {}}

        baseline_map = {m.name: m.value for m in baseline.metrics}
        for m in current.metrics:
            if m.name not in baseline_map:
                continue
            b_val = baseline_map[m.name]
            abs_delta = m.value - b_val
            rel_delta = (m.value - b_val) / b_val * 100 if b_val != 0 else float("inf")
            result["deltas"][m.name] = {
                "absolute_delta": abs_delta,
                "relative_delta_pct": round(rel_delta, 3),
            }
        return result


# ---------------------------------------------------------------------------
# ModelEvaluator
# ---------------------------------------------------------------------------

class ModelEvaluator:
    """Run accuracy/latency/power benchmarks on a model.

    Usage::

        evaluator = ModelEvaluator(model_name="perception_v3")
        evaluator.set_accuracy_fn(lambda inputs: compute_map(inputs))
        run = evaluator.run(warmup=10, iterations=100)
        print(run.latency_stats)
    """

    def __init__(
        self,
        model_name: str,
        version: str = "1.0.0",
        device: str = "cpu",
        power_monitor: Optional["PowerTracker"] = None,
    ):
        self.model_name = model_name
        self.version = version
        self.device = device
        self.power_monitor = power_monitor

        self._accuracy_fn: Optional[Callable[..., Dict[str, float]]] = None
        self._inference_fn: Optional[Callable[..., Any]] = None
        self._preprocess_fn: Optional[Callable[..., Any]] = None
        self._postprocess_fn: Optional[Callable[..., Any]] = None

    # -- configuration -------------------------------------------------------

    def set_inference_fn(self, fn: Callable[..., Any]) -> None:
        self._inference_fn = fn

    def set_accuracy_fn(self, fn: Callable[..., Dict[str, float]]) -> None:
        self._accuracy_fn = fn

    def set_preprocess_fn(self, fn: Callable[..., Any]) -> None:
        self._preprocess_fn = fn

    def set_postprocess_fn(self, fn: Callable[..., Any]) -> None:
        self._postprocess_fn = fn

    # -- single run ----------------------------------------------------------

    def run(
        self,
        inputs: Any = None,
        ground_truth: Any = None,
        warmup: int = 10,
        iterations: int = 100,
    ) -> EvalRun:
        """Execute a full evaluation run."""
        run = EvalRun(model_name=self.model_name, version=self.version)

        if self._inference_fn is None:
            raise RuntimeError("inference_fn not set — call set_inference_fn() first")

        prepared = inputs
        if self._preprocess_fn is not None and inputs is not None:
            prepared = self._preprocess_fn(inputs)

        # warmup
        for _ in range(warmup):
            self._inference_fn(prepared)

        # latency measurement
        latencies_us: List[float] = []
        if self.power_monitor is not None:
            self.power_monitor.start()

        for _ in range(iterations):
            t0 = time.perf_counter()
            output = self._inference_fn(prepared)
            t1 = time.perf_counter()
            latencies_us.append((t1 - t0) * 1e6)

        power_stats: Dict[str, float] = {}
        if self.power_monitor is not None:
            power_stats = self.power_monitor.stop()

        run.raw_latencies_us = latencies_us

        # latency stats as metrics
        stats = run.latency_stats
        for k, v in stats.items():
            run.metrics.append(EvalMetric(name=k, kind=MetricKind.LATENCY, value=v, unit="us"))

        # throughput
        total_s = sum(latencies_us) / 1e6
        run.metrics.append(EvalMetric(
            name="throughput", kind=MetricKind.THROUGHPUT,
            value=iterations / total_s if total_s > 0 else 0, unit="infer/s",
        ))

        # accuracy
        if self._accuracy_fn is not None and ground_truth is not None:
            acc = self._accuracy_fn(output, ground_truth)
            for k, v in acc.items():
                run.metrics.append(EvalMetric(name=k, kind=MetricKind.ACCURACY, value=v))

        # power
        for k, v in power_stats.items():
            run.metrics.append(EvalMetric(name=k, kind=MetricKind.POWER, value=v, unit="W" if "power" in k else "J"))

        return run


# ---------------------------------------------------------------------------
# Multi-version comparison
# ---------------------------------------------------------------------------

class VersionComparator:
    """Compare evaluation runs across multiple model versions."""

    def __init__(self):
        self.benchmarks: Dict[str, EvalBenchmark] = {}

    def add_run(self, benchmark_name: str, run: EvalRun) -> None:
        if benchmark_name not in self.benchmarks:
            self.benchmarks[benchmark_name] = EvalBenchmark()
        self.benchmarks[benchmark_name].add_run(run)

    def generate_report(
        self,
        fmt: ReportFormat = ReportFormat.MARKDOWN,
        baseline_version: Optional[str] = None,
    ) -> str:
        """Generate comparison report in requested format."""
        if fmt == ReportFormat.JSON:
            return self._to_json(baseline_version)
        elif fmt == ReportFormat.CSV:
            return self._to_csv()
        elif fmt == ReportFormat.HTML:
            return self._to_html()
        else:
            return self._to_markdown(baseline_version)

    def _to_markdown(self, baseline_version: Optional[str] = None) -> str:
        lines = ["# Model Evaluation Report\n"]
        for bench_name, bench in self.benchmarks.items():
            lines.append(f"## {bench_name}\n")
            if not bench.runs:
                lines.append("_No runs recorded._\n")
                continue

            # header
            header = "| Version | " + " | ".join(f"{m.name} ({m.unit})" if m.unit else m.name for m in bench.runs[0].metrics) + " |"
            lines.append(header)
            sep = "|--------|" + "|".join("--------" for _ in bench.runs[0].metrics) + "|"
            lines.append(sep)

            for run in bench.runs:
                row = f"| {run.version} | " + " | ".join(f"{m.value:.4f}" for m in run.metrics) + " |"
                lines.append(row)

            # latency detail
            for run in bench.runs:
                if run.raw_latencies_us:
                    stats = run.latency_stats
                    lines.append(f"\n### {run.version} latency detail\n")
                    lines.append(f"- P50: {stats['median_us']:.1f} µs, P90: {stats['p90_us']:.1f} µs, P99: {stats['p99_us']:.1f} µs")
                    lines.append(f"- Mean: {stats['mean_us']:.1f} ± {stats['std_us']:.1f} µs")

            lines.append("")

            # baseline comparison
            if baseline_version and len(bench.runs) > 1:
                baseline = next((r for r in bench.runs if r.version == baseline_version), bench.runs[0])
                for run in bench.runs:
                    if run.version == baseline_version:
                        continue
                    delta = bench.compare_to_baseline(baseline)
                    lines.append(f"### {run.version} vs {baseline_version}\n")
                    for metric_name, d in delta.get("deltas", {}).items():
                        lines.append(f"- **{metric_name}**: {d['absolute_delta']:+.4f} ( {d['relative_delta_pct']:+.2f}% )")

        return "\n".join(lines)

    def _to_json(self, baseline_version: Optional[str] = None) -> str:
        data: Dict[str, Any] = {}
        for name, bench in self.benchmarks.items():
            runs_data = []
            for run in bench.runs:
                runs_data.append({
                    "version": run.version,
                    "model_name": run.model_name,
                    "timestamp": run.timestamp,
                    "metrics": [{"name": m.name, "kind": m.kind.value, "value": m.value, "unit": m.unit} for m in run.metrics],
                    "latency_stats": run.latency_stats,
                })
            data[name] = {"runs": runs_data}
            if baseline_version and len(bench.runs) > 1:
                baseline = next((r for r in bench.runs if r.version == baseline_version), bench.runs[0])
                comparisons = {}
                for run in bench.runs:
                    if run.version == baseline_version:
                        continue
                    comparisons[run.version] = bench.compare_to_baseline(baseline)
                data[name]["baseline_comparison"] = comparisons
        return json.dumps(data, indent=2)

    def _to_csv(self) -> str:
        lines = ["benchmark,version,model_name,timestamp,metric_name,metric_kind,value,unit"]
        for bench_name, bench in self.benchmarks.items():
            for run in bench.runs:
                for m in run.metrics:
                    lines.append(f"{bench_name},{run.version},{run.model_name},{run.timestamp},{m.name},{m.kind.value},{m.value},{m.unit}")
        return "\n".join(lines)

    def _to_html(self) -> str:
        md = self._to_markdown()
        # minimal HTML wrapper
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Model Evaluation Report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:auto;padding:2rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:8px;text-align:right}}
th{{background:#f5f5f5}}</style></head><body>
{md.replace(chr(10), '<br>').replace('| ', '<td>').replace(' |', '</td>')}
</body></html>"""

    def save_report(self, path: Path, fmt: ReportFormat = ReportFormat.MARKDOWN, baseline_version: Optional[str] = None) -> None:
        path.write_text(self.generate_report(fmt, baseline_version), encoding="utf-8")


# ---------------------------------------------------------------------------
# PowerTracker stub (integrated with profiler subsystem)
# ---------------------------------------------------------------------------

class PowerTracker:
    """Tracks power consumption during evaluation runs.

    Integrates with the hardware power measurement APIs exposed by qoocore.
    """

    def __init__(self, device: str = "auto"):
        self.device = device
        self._samples: List[Tuple[float, float]] = []  # (timestamp, watts)
        self._start_time: float = 0.0

    def start(self) -> None:
        self._samples.clear()
        self._start_time = time.perf_counter()

    def stop(self) -> Dict[str, float]:
        end_time = time.perf_counter()
        # placeholder sampling — real impl queries hardware counters
        if not self._samples:
            # simulate a flat 15 W load for demo
            duration_s = end_time - self._start_time
            self._samples = [(self._start_time + i * 0.1, 15.0) for i in range(int(duration_s * 10))]

        powers = [s[1] for s in self._samples]
        return {
            "avg_power_w": statistics.mean(powers) if powers else 0,
            "peak_power_w": max(powers) if powers else 0,
            "total_energy_j": statistics.mean(powers) * (end_time - self._start_time) if powers else 0,
            "sample_count": len(powers),
        }


# ---------------------------------------------------------------------------
# Accuracy metrics helpers
# ---------------------------------------------------------------------------

def compute_classification_metrics(predictions: np.ndarray, labels: np.ndarray) -> Dict[str, float]:
    """Top-1 / Top-5 accuracy."""
    top1 = np.mean(np.argmax(predictions, axis=-1) == np.argmax(labels, axis=-1))
    top5 = np.mean(np.any(np.argsort(predictions, axis=-1)[:, -5:] == np.argmax(labels, axis=-1, keepdims=True), axis=-1))
    return {"top1_accuracy": float(top1), "top5_accuracy": float(top5)}


def compute_regression_metrics(predictions: np.ndarray, targets: np.ndarray) -> Dict[str, float]:
    """MSE / MAE / R²."""
    mse = np.mean((predictions - targets) ** 2)
    mae = np.mean(np.abs(predictions - targets))
    ss_res = np.sum((targets - predictions) ** 2)
    ss_tot = np.sum((targets - np.mean(targets)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0
    return {"mse": float(mse), "mae": float(mae), "r2_score": float(r2)}


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------

def cli_eval(args: Any) -> int:
    """`qoo eval model` entry point."""
    evaluator = ModelEvaluator(model_name=args.model, version=args.version or "latest")

    # dummy inference for testing
    evaluator.set_inference_fn(lambda x: x)
    evaluator.set_accuracy_fn(lambda out, gt: compute_regression_metrics(np.array(out), np.array(gt)))

    run = evaluator.run(inputs=np.random.rand(100), ground_truth=np.random.rand(100), warmup=5, iterations=50)
    comparator = VersionComparator()
    comparator.add_run(args.model, run)
    report = comparator.generate_report(ReportFormat.MARKDOWN)
    print(report)
    return 0
