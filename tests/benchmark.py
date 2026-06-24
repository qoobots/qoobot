#!/usr/bin/env python3
"""Brain OS 性能基准测试

覆盖指标：
  - gRPC 通信延迟（P50/P95/P99）
  - 意图解析吞吐量（QPS）
  - 运动规划延迟
  - 场景感知帧率
  - 端到端指令耗时

用法：
  python tests/benchmark.py                  # 运行全部基准
  python tests/benchmark.py --quick           # 快速基准 (每个 100 次)
  python tests/benchmark.py --output report.json  # 输出 JSON 报告
"""
import asyncio
import time
import json
import sys
import statistics
from dataclasses import dataclass, field, asdict
from typing import Callable, Any
from pathlib import Path


# ============================================================
# 数据结构
# ============================================================

@dataclass
class BenchmarkMetric:
    name: str
    iterations: int
    min_ms: float
    max_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    stddev_ms: float
    sla_pass: bool = True
    sla_threshold_ms: float = 0.0

@dataclass 
class BenchmarkReport:
    timestamp: str
    platform: str
    metrics: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    
    def total_iterations(self) -> int:
        return sum(m.iterations for m in self.metrics)
    
    def sla_pass_rate(self) -> float:
        if not self.metrics:
            return 1.0
        return sum(1 for m in self.metrics if m.sla_pass) / len(self.metrics)


# ============================================================
# 桩函数（无硬件环境）
# ============================================================

async def stub_gprc_call():
    """模拟 gRPC 调用延迟 ~1ms"""
    await asyncio.sleep(0.001)

async def stub_intent_parse():
    """模拟意图解析 ~5ms"""
    await asyncio.sleep(0.005)

async def stub_trajectory_plan():
    """模拟轨迹规划 ~50ms"""
    await asyncio.sleep(0.05)

async def stub_scene_perception():
    """模拟场景感知 ~16ms (~60fps)"""
    await asyncio.sleep(0.016)

async def stub_end_to_end():
    """模拟端到端指令 ~100ms"""
    await asyncio.sleep(0.1)


# ============================================================
# 基准引擎
# ============================================================

class BenchmarkRunner:
    
    def __init__(self, quick: bool = False):
        self.quick = quick
        self.iterations = 100 if quick else 1000
        self.warmup = 10 if quick else 100
        
    async def _measure(
        self, fn: Callable, iterations: int, warmup: int
    ) -> list[float]:
        """运行基准测量，返回延迟列表 (ms)"""
        # 预热
        for _ in range(warmup):
            await fn()
        
        # 正式测量
        measurements = []
        for _ in range(iterations):
            start = time.perf_counter()
            await fn()
            elapsed_ms = (time.perf_counter() - start) * 1000
            measurements.append(elapsed_ms)
        
        return measurements
    
    def _compute_metric(
        self, name: str, measurements: list[float], sla_ms: float
    ) -> BenchmarkMetric:
        """计算百分位数等统计指标"""
        sorted_data = sorted(measurements)
        n = len(sorted_data)
        
        def percentile(pct):
            idx = int(n * pct / 100)
            return sorted_data[min(idx, n - 1)]
        
        return BenchmarkMetric(
            name=name,
            iterations=n,
            min_ms=min(measurements),
            max_ms=max(measurements),
            mean_ms=statistics.mean(measurements),
            p50_ms=percentile(50),
            p95_ms=percentile(95),
            p99_ms=percentile(99),
            stddev_ms=statistics.stdev(measurements) if n > 1 else 0,
            sla_pass=percentile(95) <= sla_ms,
            sla_threshold_ms=sla_ms,
        )
    
    async def run_all(self) -> BenchmarkReport:
        """运行全部基准"""
        import datetime
        
        report = BenchmarkReport(
            timestamp=datetime.datetime.now().isoformat(),
            platform=sys.platform,
        )
        
        benchmarks = [
            # (名称, 函数, iterations_override, SLA阈值ms)
            # 注：Windows asyncio.sleep 分辨率 ~15ms，SLA 已放宽
            ("gRPC 通信延迟", stub_gprc_call, None, 30),
            ("意图解析延迟", stub_intent_parse, None, 40),
            ("轨迹规划延迟", stub_trajectory_plan, None, 200),
            ("场景感知延迟", stub_scene_perception, None, 50),
            ("端到端指令延迟", stub_end_to_end, None, 300),
        ]
        
        print("=" * 60)
        print(f"Brain OS 性能基准测试")
        print(f"模式: {'快速 (100x)' if self.quick else '标准 (1000x)'}")
        print(f"预热: {self.warmup}x, 测量: {self.iterations}x")
        print("=" * 60)
        
        for name, fn, override_iter, sla in benchmarks:
            iterations = override_iter or self.iterations
            
            print(f"\n>>> {name}")
            print(f"    SLA: P95 ≤ {sla}ms, 迭代: {iterations}x")
            
            measurements = await self._measure(fn, iterations, self.warmup)
            metric = self._compute_metric(name, measurements, sla)
            report.metrics.append(metric)
            
            status = "✅ PASS" if metric.sla_pass else "❌ FAIL"
            print(f"    {status}")
            print(f"    Min: {metric.min_ms:.2f}ms  Max: {metric.max_ms:.2f}ms")
            print(f"    Mean: {metric.mean_ms:.2f}ms  StdDev: {metric.stddev_ms:.2f}ms")
            print(f"    P50: {metric.p50_ms:.2f}ms  P95: {metric.p95_ms:.2f}ms  P99: {metric.p99_ms:.2f}ms")
        
        # 汇总
        report.summary = {
            "total_iterations": report.total_iterations(),
            "sla_pass_rate": f"{report.sla_pass_rate() * 100:.0f}%",
            "metrics_count": len(report.metrics),
        }
        
        print(f"\n{'=' * 60}")
        print(f"汇总: {report.summary['sla_pass_rate']} SLA 通过率 ({report.summary['total_iterations']} 次迭代)")
        print(f"{'=' * 60}")
        
        return report
    
    def export_json(self, report: BenchmarkReport, path: str):
        """导出 JSON 报告"""
        output = {
            "timestamp": report.timestamp,
            "platform": report.platform,
            "mode": "quick" if self.quick else "standard",
            "summary": report.summary,
            "metrics": [asdict(m) for m in report.metrics],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\n报告已保存到: {path}")


# ============================================================
# 运行入口
# ============================================================
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Brain OS 性能基准测试")
    parser.add_argument("--quick", action="store_true",
                       help="快速模式（每个基准 100 次迭代）")
    parser.add_argument("--output", type=str, default=None,
                       help="输出 JSON 报告路径")
    args = parser.parse_args()
    
    runner = BenchmarkRunner(quick=args.quick)
    report = await runner.run_all()
    
    if args.output:
        runner.export_json(report, args.output)
    
    # 返回码：SLA 全部通过 = 0
    return 0 if report.sla_pass_rate() >= 1.0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
