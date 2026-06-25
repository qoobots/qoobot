# Brain OS --dry-run Release Notes

> 2026-06-24 | Phase 1 原型验证发布

## Overview

Brain OS --dry-run 是 Phase 1 的完整原型验证版本，包含：
- 9 个子项目，404 个源文件
- 6 个 gRPC 服务
- 143 个测试用例（100% 通过）
- 13 页 MkDocs 技术文档

## What's Included

### brain_core (C++17)
- ROS2 Bridge (pub/sub/service/action)
- Behavior Engine (BehaviorTree.CPP v4 + 10 Action Nodes)
- Motion Planner (TRAC-IK + Trajectory Generator)
- Safety Monitor (FCL Collision + Emergency Stop)
- 8 gtest unit tests

### brain_ai (Python 3.11)
- LLM Agent (Qwen2.5-7B)
- Perception Pipeline (YOLOv11 + ORB-SLAM3 + SceneGraph)
- Cognition Pipeline (Intent Parse → Task Decompose → BT Generate)
- Decision Pipeline (Trajectory Generate → HITL Select)
- 118 pytest unit tests

### brain_viz (TypeScript)
- 3D Scene View (Three.js / React Three Fiber)
- HITL Panel (trajectory selection, score chart)
- Status Monitor (health, alerts, metrics, logs)
- Dev Panel (API tester, skill registry, BT viewer)
- 5 tests (components + store + E2E)

### Tests & Tools
- 12 E2E integration tests (instruction → execution pipeline)
- Performance benchmark framework (8 metrics + SLA comparison)
- C++ build verification script
- E2E demo script (4 scenarios)

## Installation

```bash
pip install -e brain_ai/ -e brain_sdk/
cd brain_viz && npm install
```

## Quick Start

```bash
python brain_sim/demo/e2e_demo.py --scenario pick_cup
```

## Documentation

```bash
cd brain_docs && mkdocs serve
```

## Statistics

| Metric | Value |
|--------|-------|
| Total source files | 404 |
| C++ files | 107 |
| Python files | 221 |
| TypeScript files | 91 |
| Proto files | 13 |
| Doc files | 25 |
| Test files | 17 |
| Total tests passing | 143 |

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for full details.
