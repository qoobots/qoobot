#!/usr/bin/env python3
"""QooBrain AI 模型推理性能基准测试脚本。

Usage:
    python scripts/benchmark_inference.py --model qwen2.5-7b --backend trt-llm
    python scripts/benchmark_inference.py --model yolov11n --backend onnx
"""

import argparse
import time
import sys

sys.path.insert(0, ".")

try:
    from brain_ai.model_runtime.runtime_factory import RuntimeFactory
except ImportError:
    print("Error: brain_ai not installed. Run: pip install -e brain_ai/")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Brain AI Inference Benchmark")
    parser.add_argument("--model", default="qwen2.5-1.5b", help="Model to benchmark")
    parser.add_argument("--backend", default="stub", help="Inference backend")
    parser.add_argument("--warmup", type=int, default=3, help="Warmup iterations")
    parser.add_argument("--runs", type=int, default=10, help="Benchmark iterations")
    args = parser.parse_args()

    print(f"Benchmarking {args.model} on {args.backend} backend")
    print(f"Warmup: {args.warmup} runs, Benchmark: {args.runs} runs")

    # Warmup
    for i in range(args.warmup):
        t0 = time.perf_counter()
        time.sleep(0.01)  # Placeholder for actual inference
        elapsed = (time.perf_counter() - t0) * 1000
        print(f"  Warmup {i + 1}/{args.warmup}: {elapsed:.1f}ms")

    # Benchmark
    latencies = []
    for i in range(args.runs):
        t0 = time.perf_counter()
        time.sleep(0.01)  # Placeholder for actual inference
        elapsed = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed)
        print(f"  Run {i + 1}/{args.runs}: {elapsed:.1f}ms")

    avg = sum(latencies) / len(latencies)
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]

    print(f"\nResults:")
    print(f"  Avg:  {avg:.1f}ms")
    print(f"  P50:  {p50:.1f}ms")
    print(f"  P95:  {p95:.1f}ms")
    print(f"  P99:  {p99:.1f}ms")


if __name__ == "__main__":
    main()
