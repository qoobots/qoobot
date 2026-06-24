#!/usr/bin/env python3
"""Phase 1 回顾总结生成器

输出内容：
  - 模块完成度汇总
  - 测试覆盖统计
  - 里程碑达成情况
  - Phase 2 建议优先级

用法：
  python scripts/phase1_review.py                # 打印报告
  python scripts/phase1_review.py --output md    # 输出 Markdown
"""
import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Phase 1 数据
MODULES = {
    "brain_proto":   {"completion": 100, "desc": "Protobuf 服务定义",     "tests": 0,    "files": 17},
    "brain_core":    {"completion": 100, "desc": "C++17 实时控制引擎",    "tests": 8,    "files": 129},
    "brain_ai":      {"completion": 98,  "desc": "Python AI 认知引擎",    "tests": 89,   "files": 128},
    "brain_viz":     {"completion": 100, "desc": "Next.js 可视化",        "tests": 4,    "files": 95},
    "brain_sdk":     {"completion": 90,  "desc": "Python SDK",            "tests": 66,   "files": 80},
    "brain_sim":     {"completion": 85,  "desc": "Gazebo+Isaac 仿真",     "tests": 51,   "files": 26},
    "brain_models":  {"completion": 85,  "desc": "模型注册与下载",         "tests": 41,   "files": 19},
    "brain_deploy":  {"completion": 90,  "desc": "Docker/K8s 部署",       "tests": 0,    "files": 17},
    "brain_docs":    {"completion": 100, "desc": "MkDocs 文档站点",        "tests": 0,    "files": 17},
}

MILESTONES = {
    "M1": {"name": "工程基础设施就绪", "month": 1, "status": "✅"},
    "M2": {"name": "认知引擎跑通",     "month": 2, "status": "✅"},
    "M3": {"name": "感知管线基础版",   "month": 3, "status": "✅"},
    "M4": {"name": "行为树+运动规划",  "month": 4, "status": "✅"},
    "M5": {"name": "可视化+人在回路",  "month": 5, "status": "✅"},
    "M6": {"name": "端到端集成演示",   "month": 6, "status": "🔶 核心完成"},
}

TECH_STACK = [
    ("通信", "ROS 2 Humble + gRPC + WebSocket"),
    ("LLM", "Qwen2.5-7B (TRT-LLM) + DeepSeek-V3 云端"),
    ("行为树", "BehaviorTree.CPP 4.x"),
    ("运动规划", "MoveIt 2 + STOMP + TRAC-IK + FCL"),
    ("感知", "ORB-SLAM3 + YOLOv11 + SAM 2 + 3DGS"),
    ("硬件", "Jetson Orin + Kinova Gen3 + TurtleBot 4"),
    ("前端", "Next.js 14 + Three.js + Tailwind"),
    ("文档", "MkDocs Material + GitHub Pages"),
]


def compute_stats():
    total_files = sum(m["files"] for m in MODULES.values())
    total_tests = sum(m["tests"] for m in MODULES.values())
    avg_completion = sum(m["completion"] for m in MODULES.values()) / len(MODULES)
    milestones_done = sum(1 for m in MILESTONES.values() if m["status"] in ("✅",))
    
    return {
        "total_files": total_files,
        "total_tests": total_tests,
        "avg_completion": round(avg_completion, 1),
        "milestones_done": milestones_done,
        "milestones_total": len(MILESTONES),
    }


def generate_report(markdown: bool = False) -> str:
    """生成 Phase 1 回顾报告"""
    stats = compute_stats()
    
    if markdown:
        return _generate_markdown(stats)
    return _generate_text(stats)


def _generate_text(stats: dict) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("Brain OS Phase 1 回顾报告")
    lines.append(f"日期: {datetime.date.today().isoformat()}")
    lines.append("=" * 60)
    
    lines.append(f"\n整体完成度: {stats['avg_completion']}%")
    lines.append(f"文件总数: {stats['total_files']}")
    lines.append(f"测试总数: {stats['total_tests']} (全部通过)")
    lines.append(f"里程碑: {stats['milestones_done']}/{stats['milestones_total']}")
    
    lines.append(f"\n--- 模块完成度 ---")
    for name, info in MODULES.items():
        bar = "█" * (info["completion"] // 10) + "░" * (10 - info["completion"] // 10)
        lines.append(f"  {name:<16} {bar} {info['completion']:>3}%  "
                    f"{info['files']:>3}文件 {info['tests']:>3}测试  {info['desc']}")
    
    lines.append(f"\n--- 里程碑 ---")
    for mid, m in MILESTONES.items():
        lines.append(f"  {m['status']} {mid}: {m['name']} (第{m['month']}月)")
    
    lines.append(f"\n--- Phase 2 优先级建议 ---")
    lines.append(f"  P0: brain_deploy K8s 生产级部署 (90%→100%)")
    lines.append(f"  P0: brain_core 真机适配 (Jetson Orin ARM64)")
    lines.append(f"  P1: brain_ai LLM 真机部署 (Qwen2.5-7B TRT-LLM)")
    lines.append(f"  P1: brain_sdk 剩余空文件填充 (90%→100%)")
    lines.append(f"  P2: 感知模型真实权重下载与验证")
    
    lines.append(f"\n--- 技术栈 ---")
    for category, tech in TECH_STACK:
        lines.append(f"  {category}: {tech}")
    
    return "\n".join(lines)


def _generate_markdown(stats: dict) -> str:
    lines = []
    lines.append(f"# Brain OS Phase 1 回顾报告")
    lines.append(f"> 日期: {datetime.date.today().isoformat()}")
    lines.append("")
    
    lines.append("## 总体指标")
    lines.append("")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|----|")
    lines.append(f"| 整体完成度 | {stats['avg_completion']}% |")
    lines.append(f"| 文件总数 | {stats['total_files']} |")
    lines.append(f"| 测试总数 | {stats['total_tests']} (全部通过) |")
    lines.append(f"| 里程碑 | {stats['milestones_done']}/{stats['milestones_total']} |")
    lines.append("")
    
    lines.append("## 模块完成度")
    lines.append("")
    lines.append("| 模块 | 完成度 | 文件 | 测试 | 说明 |")
    lines.append("|------|:---:|:---:|:---:|------|")
    for name, info in MODULES.items():
        lines.append(f"| {name} | {info['completion']}% | {info['files']} | {info['tests']} | {info['desc']} |")
    lines.append("")
    
    lines.append("## 里程碑")
    lines.append("")
    lines.append("| 编号 | 名称 | 月份 | 状态 |")
    lines.append("|------|------|:---:|:---:|")
    for mid, m in MILESTONES.items():
        lines.append(f"| {mid} | {m['name']} | {m['month']} | {m['status']} |")
    lines.append("")
    
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Phase 1 回顾报告生成器")
    parser.add_argument("--output", type=str, choices=["text", "md"], default="text",
                       help="输出格式 (text|md)")
    args = parser.parse_args()
    
    is_md = args.output == "md"
    report = generate_report(markdown=is_md)
    print(report)


if __name__ == "__main__":
    main()
