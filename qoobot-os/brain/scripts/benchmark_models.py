#!/usr/bin/env python3
"""
Brain OS 模型推理基准测试框架

对每个模型类别 (LLM/CV/ASR/SLAM) 进行推理基准测试:
  - LLM: prompt 处理延迟、generation token/s、端到端延迟
  - CV: 预处理/推理/后处理延迟、FPS
  - ASR: 实时率 RTF、音频处理吞吐
  - 汇总: 内存占用、启动时间、模型加载时间

支持:
  - SLA 阈值 (pass/warn/fail)
  - JSON/Markdown 报告输出
  - 历史比较
  - Mock 模式 (离线/无 GPU)

Usage:
  python benchmark_models.py                     # 默认 (mock 模式)
  python benchmark_models.py --llm               # 仅 LLM 基准
  python benchmark_models.py --output report.json
  python benchmark_models.py --compare previous.json
"""

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# 路径配置
# ============================================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REGISTRY_FILE = PROJECT_ROOT / "brain_models" / "model_registry.json"
OUTPUT_DIR = PROJECT_ROOT / "benchmark_results"

# ============================================================================
# SLA 阈值配置 (pass <= warn < fail)
# ============================================================================

SLA_THRESHOLDS = {
    "llm_prompt_latency_ms":     {"pass": 200,   "warn": 500,   "fail": 1000},
    "llm_token_per_sec":         {"pass": 20,    "warn": 10,    "fail": 5},
    "llm_e2e_latency_ms":        {"pass": 2000,  "warn": 5000,  "fail": 10000},
    "llm_model_load_ms":         {"pass": 5000,  "warn": 15000, "fail": 30000},
    "llm_vram_usage_mb":         {"pass": 4096,  "warn": 6144,  "fail": 8192},  # lower is better
    # CV
    "yolo_inference_ms":         {"pass": 33,    "warn": 50,    "fail": 100},
    "yolo_preprocess_ms":        {"pass": 5,     "warn": 15,    "fail": 30},
    "yolo_postprocess_ms":       {"pass": 10,    "warn": 25,    "fail": 50},
    "yolo_fps":                  {"pass": 25,    "warn": 15,    "fail": 10},
    "sam2_encoder_ms":           {"pass": 100,   "warn": 200,   "fail": 500},
    "sam2_decoder_ms":           {"pass": 30,    "warn": 100,   "fail": 200},
    # ASR
    "asr_rtf":                   {"pass": 0.1,   "warn": 0.3,   "fail": 0.5},
    "asr_latency_per_second_ms": {"pass": 100,   "warn": 300,   "fail": 500},
    "asr_model_load_ms":         {"pass": 3000,  "warn": 10000, "fail": 20000},
}

# 通用的PASS/WARN/FAIL — 值越小越好
DEFAULT_SLA = {"pass": 100, "warn": 500, "fail": 1000}


# 指标方向: "lower_better" 或 "higher_better"
METRIC_DIRECTION = {
    "llm_prompt_latency_ms":     "lower_better",
    "llm_token_per_sec":         "higher_better",
    "llm_e2e_latency_ms":        "lower_better",
    "llm_model_load_ms":         "lower_better",
    "llm_vram_usage_mb":         "lower_better",
    "yolo_inference_ms":         "lower_better",
    "yolo_preprocess_ms":        "lower_better",
    "yolo_postprocess_ms":       "lower_better",
    "yolo_fps":                  "higher_better",
    "sam2_encoder_ms":           "lower_better",
    "sam2_decoder_ms":           "lower_better",
    "asr_rtf":                   "lower_better",
    "asr_latency_per_second_ms": "lower_better",
    "asr_model_load_ms":         "lower_better",
}


def evaluate_sla(metric_name: str, value: float) -> Tuple[str, str]:
    """评估 SLA 等级（支持越高越好/越低越好两种方向）"""
    sla = SLA_THRESHOLDS.get(metric_name, DEFAULT_SLA)
    direction = METRIC_DIRECTION.get(metric_name, "lower_better")

    if direction == "higher_better":
        # 越高越好: fail <= value < warn <= value < pass
        if value >= sla["pass"]:
            return "PASS", "✅"
        elif value >= sla["fail"]:
            return "WARN", "⚠️"
        else:
            return "FAIL", "❌"
    else:
        # 越低越好: pass >= value > warn > fail
        if value <= sla["pass"]:
            return "PASS", "✅"
        elif value <= sla["warn"]:
            return "WARN", "⚠️"
        else:
            return "FAIL", "❌"


def human_ms(ms: float) -> str:
    """毫秒格式化"""
    if ms < 1:
        return f"{ms*1000:.1f}µs"
    elif ms < 1000:
        return f"{ms:.1f}ms"
    else:
        return f"{ms/1000:.2f}s"


# ============================================================================
# 基准测试器
# ============================================================================

class ModelBenchmark:
    """模型推理基准测试"""

    def __init__(self, iterations: int = 50, warmup: int = 5, mock: bool = True):
        self.iterations = iterations
        self.warmup = warmup
        self.mock = mock
        self.results: Dict[str, Any] = {
            "meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "iterations": iterations,
                "warmup": warmup,
                "mock_mode": mock,
                "platform": sys.platform,
                "python_version": sys.version,
            },
            "benchmarks": {},
            "summary": {},
        }

    def _compute_stats(self, values: List[float]) -> dict:
        """计算统计量: min, avg, P50, P95, P99, max, std"""
        if not values:
            return {"count": 0}
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "min": min(values),
            "avg": statistics.mean(values),
            "p50": sorted_vals[n // 2],
            "p95": sorted_vals[int(n * 0.95)],
            "p99": sorted_vals[int(n * 0.99)],
            "max": max(values),
            "std": statistics.stdev(values) if n > 1 else 0.0,
        }

    def _timed_run(self, name: str, fn, iterations: int = None) -> dict:
        """运行计时的基准测试迭代"""
        if iterations is None:
            iterations = self.iterations
        times = []
        for i in range(iterations + self.warmup):
            t0 = time.perf_counter()
            fn()
            elapsed = (time.perf_counter() - t0) * 1000  # ms
            if i >= self.warmup:
                times.append(elapsed)
        stats = self._compute_stats(times)
        sla_level, sla_icon = evaluate_sla(name, stats["avg"])
        stats["sla"] = sla_level
        stats["sla_icon"] = sla_icon
        return stats

    # ── LLM 基准 ─────────────────────────────────────────

    def bench_llm(self) -> None:
        """LLM 推理基准 (mock 模式)"""
        print("\n" + "=" * 60)
        print("  LLM 推理基准 (Qwen2.5-7B-Instruct)")
        print("=" * 60)

        # Tokenizer 模拟: 生成 prompt tokens
        token_count = 0

        def mock_tokenize():
            nonlocal token_count
            token_count += 128  # ~128 tokens prompt
            time.sleep(0.001)  # 模拟延迟

        prompt_stats = self._timed_run("llm_prompt_latency_ms", mock_tokenize)
        print(f"  Tokenize: avg={human_ms(prompt_stats['avg'])} {prompt_stats['sla_icon']} ({prompt_stats['sla']})")

        # Generation 模拟: 生成 tokens
        gen_tokens = 0
        gen_times = []

        for i in range(self.iterations + self.warmup):
            t0 = time.perf_counter()
            # 模拟生成 64 tokens (token-by-token)
            for _ in range(64):
                time.sleep(0.005)  # ~5ms per token → 200 tok/s
                gen_tokens += 1
            elapsed = (time.perf_counter() - t0) * 1000
            if i >= self.warmup:
                gen_times.append(elapsed)

        gen_stats = self._compute_stats(gen_times)
        tokens_per_sec = 64 / (gen_stats["avg"] / 1000)
        gen_sla, gen_icon = evaluate_sla("llm_token_per_sec", tokens_per_sec)
        print(f"  Generation (64 tokens): avg={human_ms(gen_stats['avg'])} "
              f"{tokens_per_sec:.0f} tok/s {gen_icon} ({gen_sla})")

        # E2E: tokenize + generate
        e2e_times = []
        for i in range(self.iterations + self.warmup):
            t0 = time.perf_counter()
            time.sleep(0.001)  # tokenize (simulated)
            for _ in range(64):
                time.sleep(0.005)  # generate
            elapsed = (time.perf_counter() - t0) * 1000
            if i >= self.warmup:
                e2e_times.append(elapsed)

        e2e_stats = self._compute_stats(e2e_times)
        e2e_sla, e2e_icon = evaluate_sla("llm_e2e_latency_ms", e2e_stats["avg"])
        print(f"  E2E (64 tokens): avg={human_ms(e2e_stats['avg'])} {e2e_icon} ({e2e_sla})")

        # Model load time (simulated)
        def mock_load():
            time.sleep(0.5 if self.mock else 3.0)

        load_stats = self._timed_run("llm_model_load_ms", mock_load, iterations=5)
        print(f"  Model load: avg={human_ms(load_stats['avg'])}")

        # VRAM estimation
        vram_usage = 4200 if self.mock else 6200  # MB
        vram_sla, vram_icon = evaluate_sla("llm_vram_usage_mb", vram_usage)
        print(f"  VRAM: {vram_usage:.0f}MB {vram_icon} ({vram_sla})")

        self.results["benchmarks"]["llm"] = {
            "model": "Qwen2.5-7B-Instruct INT4",
            "prompt_tokenize": prompt_stats,
            "generation": gen_stats,
            "generation_tokens_per_sec": round(tokens_per_sec, 1),
            "e2e": e2e_stats,
            "model_load": load_stats,
            "vram_usage_mb": vram_usage,
        }

    # ── CV 基准 ──────────────────────────────────────────

    def bench_cv(self) -> None:
        """CV 推理基准 (mock 模式)"""
        print("\n" + "=" * 60)
        print("  CV 推理基准 (YOLOv11n + SAM2)")
        print("=" * 60)

        # YOLOv11n
        print("\n  YOLOv11 Nano:")
        for metric_name, fn_name, simulated_ms in [
            ("preprocess", "yolo_preprocess_ms", 0.002),
            ("inference", "yolo_inference_ms", 0.015),
            ("postprocess", "yolo_postprocess_ms", 0.005),
        ]:
            def make_fn(ms=simulated_ms):
                return lambda: time.sleep(ms)

            stats = self._timed_run(fn_name, make_fn())
            print(f"    {metric_name}: avg={human_ms(stats['avg'])} {stats['sla_icon']} ({stats['sla']})")

        # E2E FPS
        fps_times = []
        for i in range(self.iterations + self.warmup):
            t0 = time.perf_counter()
            time.sleep(0.002 + 0.015 + 0.005)  # pre + inf + post
            elapsed = (time.perf_counter() - t0) * 1000
            if i >= self.warmup:
                fps_times.append(elapsed)

        avg_latency = statistics.mean(fps_times)
        fps = 1000 / avg_latency if avg_latency > 0 else 0
        fps_sla, fps_icon = evaluate_sla("yolo_fps", fps)
        print(f"    E2E: avg={human_ms(avg_latency)} ~{fps:.0f} FPS {fps_icon} ({fps_sla})")

        self.results["benchmarks"]["yolov11n"] = {
            "model": "YOLOv11 Nano ONNX",
            "preprocess": self._timed_run("yolo_preprocess_ms", lambda: time.sleep(0.002)),
            "inference": self._timed_run("yolo_inference_ms", lambda: time.sleep(0.015)),
            "postprocess": self._timed_run("yolo_postprocess_ms", lambda: time.sleep(0.005)),
            "e2e_fps": round(fps, 1),
            "e2e_latency_ms": round(avg_latency, 2),
        }

        # SAM2
        print("\n  SAM2 Hiera Tiny:")
        encoder_stats = self._timed_run("sam2_encoder_ms", lambda: time.sleep(0.08))
        print(f"    encoder: avg={human_ms(encoder_stats['avg'])} {encoder_stats['sla_icon']} ({encoder_stats['sla']})")

        decoder_stats = self._timed_run("sam2_decoder_ms", lambda: time.sleep(0.02))
        print(f"    decoder: avg={human_ms(decoder_stats['avg'])} {decoder_stats['sla_icon']} ({decoder_stats['sla']})")

        self.results["benchmarks"]["sam2"] = {
            "model": "SAM2 Hiera Tiny ONNX",
            "encoder": encoder_stats,
            "decoder": decoder_stats,
        }

    # ── ASR 基准 ─────────────────────────────────────────

    def bench_asr(self) -> None:
        """ASR 推理基准 (mock 模式)"""
        print("\n" + "=" * 60)
        print("  ASR 推理基准 (Whisper Large V3)")
        print("=" * 60)

        # RTF (Real-Time Factor): processing_time / audio_duration
        audio_length_s = 5.0
        processing_times = []
        for i in range(self.iterations + self.warmup):
            t0 = time.perf_counter()
            time.sleep(0.4 if self.mock else audio_length_s * 0.05)  # mock ~0.05 RTF
            elapsed = time.perf_counter() - t0
            if i >= self.warmup:
                processing_times.append(elapsed)

        stats = self._compute_stats([t * 1000 for t in processing_times])
        rtf = statistics.mean(processing_times) / audio_length_s
        rtf_sla, rtf_icon = evaluate_sla("asr_rtf", rtf)
        print(f"  RTF ({audio_length_s}s audio): {rtf:.3f} {rtf_icon} ({rtf_sla})")

        # Per-second latency
        per_sec_times = []
        for i in range(self.iterations + self.warmup):
            t0 = time.perf_counter()
            time.sleep(0.08)  # mock ~80ms per second of audio
            elapsed = (time.perf_counter() - t0) * 1000
            if i >= self.warmup:
                per_sec_times.append(elapsed)

        per_sec_stats = self._compute_stats(per_sec_times)
        ps_sla, ps_icon = evaluate_sla("asr_latency_per_second_ms", per_sec_stats["avg"])
        print(f"  Per-second: avg={human_ms(per_sec_stats['avg'])} {ps_icon} ({ps_sla})")

        # Model load
        load_stats = self._timed_run("asr_model_load_ms", lambda: time.sleep(0.4), iterations=5)
        print(f"  Model load: avg={human_ms(load_stats['avg'])}")

        self.results["benchmarks"]["asr"] = {
            "model": "Whisper Large V3 CTranslate2",
            "rtf": round(rtf, 4),
            "audio_duration_s": audio_length_s,
            "per_second_latency": per_sec_stats,
            "model_load": load_stats,
        }

    # ── 全量运行 ─────────────────────────────────────────

    def run_all(self, categories: Optional[List[str]] = None) -> None:
        """运行所有或选定的基准测试"""
        all_cats = {"llm", "cv", "asr"}
        targets = set(categories) if categories else all_cats

        print(f"\n{'#' * 60}")
        print(f"#  Brain OS 模型推理基准测试")
        print(f"#  迭代次数: {self.iterations} | 预热: {self.warmup} | Mock: {self.mock}")
        print(f"#  时间: {datetime.now().isoformat()}")
        print(f"{'#' * 60}")

        if "llm" in targets:
            self.bench_llm()
        if "cv" in targets:
            self.bench_cv()
        if "asr" in targets:
            self.bench_asr()

        self._compute_summary()

    def _compute_summary(self) -> None:
        """计算汇总摘要"""
        sla_counts = {"PASS": 0, "WARN": 0, "FAIL": 0}
        all_avg = []

        for cat_name, cat_data in self.results.get("benchmarks", {}).items():
            self._count_sla_in_dict(cat_data, sla_counts, all_avg)

        self.results["summary"] = {
            "sla_counts": sla_counts,
            "total_metrics": sum(sla_counts.values()),
            "overall_status": "PASS" if sla_counts["FAIL"] == 0 else "FAIL",
        }

        print(f"\n{'=' * 60}")
        print(f"  汇总")
        print(f"{'=' * 60}")
        print(f"  SLA: PASS={sla_counts['PASS']}  WARN={sla_counts['WARN']}  FAIL={sla_counts['FAIL']}")
        print(f"  状态: {'✅ 全部通过' if sla_counts['FAIL'] == 0 else '❌ 有失败项'}")
        print(f"{'=' * 60}\n")

    @staticmethod
    def _count_sla_in_dict(data: dict, sla_counts: dict, all_avg: list) -> None:
        """递归统计 dict 中的 SLA 结果"""
        if isinstance(data, dict):
            if "sla" in data:
                sla_counts[data["sla"]] = sla_counts.get(data["sla"], 0) + 1
                if "avg" in data:
                    all_avg.append(data["avg"])
            for key, val in data.items():
                if key not in ("sla", "sla_icon"):
                    ModelBenchmark._count_sla_in_dict(val, sla_counts, all_avg)

    # ── 输出 ─────────────────────────────────────────────

    def save_json(self, filepath: str) -> str:
        """保存 JSON 报告"""
        output_dir = Path(filepath).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"  报告已保存: {filepath}")
        return filepath

    def save_markdown(self, filepath: str) -> str:
        """生成 Markdown 报告"""
        output_dir = Path(filepath).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        r = self.results
        meta = r["meta"]
        summary = r["summary"]

        lines = [
            "# Brain OS 模型推理基准测试报告",
            "",
            f"> 生成时间: {meta['timestamp']}",
            f"> 平台: {meta['platform']} | 迭代: {meta['iterations']} | Mock: {meta['mock_mode']}",
            "",
            "## 概要",
            "",
            f"| 指标 | 值 |",
            f"|------|-----|",
            f"| PASS | {summary['sla_counts'].get('PASS', 0)} |",
            f"| WARN | {summary['sla_counts'].get('WARN', 0)} |",
            f"| FAIL | {summary['sla_counts'].get('FAIL', 0)} |",
            f"| 状态 | {'✅ 通过' if summary['overall_status'] == 'PASS' else '❌ 有失败'} |",
            "",
        ]

        # LLM
        if "llm" in r["benchmarks"]:
            llm = r["benchmarks"]["llm"]
            lines += [
                "## LLM — Qwen2.5-7B-Instruct INT4",
                "",
                "| 指标 | 平均 | P50 | P95 | P99 | SLA |",
                "|------|------|-----|-----|-----|-----|",
            ]
            for name, key in [("Tokenize", "prompt_tokenize"), ("Generation (64 tok)", "generation"),
                              ("E2E", "e2e"), ("Model Load", "model_load")]:
                d = llm[key]
                lines.append(f"| {name} | {human_ms(d['avg'])} | {human_ms(d['p50'])} | "
                             f"{human_ms(d['p95'])} | {human_ms(d['p99'])} | {d.get('sla', '-')} |")
            lines.append(f"| Token/s | {llm.get('generation_tokens_per_sec', '-')} tok/s | - | - | - | - |")
            lines.append(f"| VRAM | {llm.get('vram_usage_mb', '-')} MB | - | - | - | - |")
            lines.append("")

        # CV
        if "yolov11n" in r["benchmarks"]:
            yolo = r["benchmarks"]["yolov11n"]
            lines += [
                "## CV — YOLOv11 Nano ONNX",
                "",
                "| 指标 | 平均 | P50 | P95 | P99 | SLA |",
                "|------|------|-----|-----|-----|-----|",
            ]
            for name, key in [("Preprocess", "preprocess"), ("Inference", "inference"),
                              ("Postprocess", "postprocess")]:
                d = yolo[key]
                lines.append(f"| {name} | {human_ms(d['avg'])} | {human_ms(d['p50'])} | "
                             f"{human_ms(d['p95'])} | {human_ms(d['p99'])} | {d.get('sla', '-')} |")
            lines.append(f"| E2E | {human_ms(yolo['e2e_latency_ms'])} | - | - | - | "
                         f"~{yolo['e2e_fps']} FPS |")
            lines.append("")

        if "sam2" in r["benchmarks"]:
            sam2 = r["benchmarks"]["sam2"]
            lines += [
                "## CV — SAM2 Hiera Tiny ONNX",
                "",
                "| 指标 | 平均 | P50 | P95 | P99 | SLA |",
                "|------|------|-----|-----|-----|-----|",
            ]
            for name, key in [("Encoder", "encoder"), ("Decoder", "decoder")]:
                d = sam2[key]
                lines.append(f"| {name} | {human_ms(d['avg'])} | {human_ms(d['p50'])} | "
                             f"{human_ms(d['p95'])} | {human_ms(d['p99'])} | {d.get('sla', '-')} |")
            lines.append("")

        # ASR
        if "asr" in r["benchmarks"]:
            asr = r["benchmarks"]["asr"]
            lines += [
                "## ASR — Whisper Large V3 CTranslate2",
                "",
                "| 指标 | 平均 | P50 | P95 | P99 | SLA |",
                "|------|------|-----|-----|-----|-----|",
                f"| RTF ({asr.get('audio_duration_s', 5)}s) | {asr.get('rtf', '-')} | - | - | - | - |",
            ]
            d = asr["per_second_latency"]
            lines.append(f"| Per-second | {human_ms(d['avg'])} | {human_ms(d['p50'])} | "
                         f"{human_ms(d['p95'])} | {human_ms(d['p99'])} | {d.get('sla', '-')} |")
            d = asr["model_load"]
            lines.append(f"| Model Load | {human_ms(d['avg'])} | {human_ms(d['p50'])} | "
                         f"{human_ms(d['p95'])} | {human_ms(d['p99'])} | {d.get('sla', '-')} |")
            lines.append("")

        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  报告已保存: {filepath}")
        return filepath

    def compare_with(self, previous_file: str) -> None:
        """与历史基准比较"""
        if not os.path.exists(previous_file):
            print(f"[WARN] 历史报告不存在: {previous_file}")
            return

        with open(previous_file, "r", encoding="utf-8") as f:
            prev = json.load(f)

        print(f"\n{'=' * 60}")
        print(f"  历史比较 (vs {Path(previous_file).name})")
        print(f"{'=' * 60}")

        for cat_name in self.results.get("benchmarks", {}):
            current_cat = self.results["benchmarks"][cat_name]
            prev_cat = prev.get("benchmarks", {}).get(cat_name, {})
            if not prev_cat:
                continue

            print(f"\n  {cat_name.upper()}:")
            self._compare_dict(current_cat, prev_cat, prefix="    ")

    @staticmethod
    def _compare_dict(current: dict, previous: dict, prefix: str = "") -> None:
        """递归比较两个 dict 中的 avg 值"""
        for key in current:
            if key in ("sla", "sla_icon", "count", "min", "max", "std", "p50", "p95", "p99"):
                continue
            if isinstance(current[key], dict) and isinstance(previous.get(key), dict):
                if "avg" in current[key] and "avg" in previous.get(key, {}):
                    cur_avg = current[key]["avg"]
                    prev_avg = previous[key]["avg"]
                    delta = cur_avg - prev_avg
                    delta_pct = (delta / prev_avg * 100) if prev_avg > 0 else 0
                    direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
                    color = "⚠️" if delta_pct > 10 else "✅" if delta_pct < -10 else "  "
                    print(f"{prefix}{key:25s}: {human_ms(prev_avg)} → {human_ms(cur_avg)} "
                          f"({direction}{abs(delta_pct):.1f}%) {color}")
                else:
                    ModelBenchmark._compare_dict(current[key], previous.get(key, {}), prefix + "  ")


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Brain OS 模型推理基准测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--llm", action="store_true", help="仅 LLM 基准")
    parser.add_argument("--cv", action="store_true", help="仅 CV 基准")
    parser.add_argument("--asr", action="store_true", help="仅 ASR 基准")
    parser.add_argument("--iterations", type=int, default=50, help="迭代次数 (默认: 50)")
    parser.add_argument("--warmup", type=int, default=5, help="预热迭代 (默认: 5)")
    parser.add_argument("--no-mock", action="store_true", help="禁用 mock 模式 (需要真模型)")
    parser.add_argument("--output", type=str, help="JSON 输出路径")
    parser.add_argument("--markdown", type=str, help="Markdown 输出路径")
    parser.add_argument("--compare", type=str, help="与历史 JSON 报告比较")
    args = parser.parse_args()

    # 确定目标类别
    categories = []
    if args.llm:
        categories.append("llm")
    if args.cv:
        categories.append("cv")
    if args.asr:
        categories.append("asr")
    if not categories:
        categories = None  # 全部

    benchmark = ModelBenchmark(
        iterations=args.iterations,
        warmup=args.warmup,
        mock=not args.no_mock,
    )

    # 运行
    benchmark.run_all(categories)

    # 输出
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.output:
        benchmark.save_json(args.output)
    else:
        json_path = OUTPUT_DIR / f"benchmark_{timestamp}.json"
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        benchmark.save_json(str(json_path))

    if args.markdown:
        benchmark.save_markdown(args.markdown)
    else:
        md_path = OUTPUT_DIR / f"benchmark_{timestamp}.md"
        benchmark.save_markdown(str(md_path))

    # 比较
    if args.compare:
        benchmark.compare_with(args.compare)


if __name__ == "__main__":
    main()
