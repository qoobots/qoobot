# Brain OS

具身智能机器人操作系统 — 从自然语言指令到机器人执行的完整技术栈。

> **Phase 1 v1.0.0-alpha** | 完成度 ~86% | 143 测试全部通过 | [更新日志](CHANGELOG.md)

---

## 工程结构 (Monorepo)

| 项目 | 语言 | 说明 | 完成度 |
|------|------|------|--------|
| `brain_proto/` | Protobuf | gRPC 服务与消息定义 | 100% |
| `brain_core/` | C++17 | 实时引擎 — ROS 2 桥接、行为树、安全监控、运动规划 | 100% |
| `brain_ai/` | Python 3.11 | AI 引擎 — LLM Agent、感知管线、任务规划、gRPC 服务 | 98% |
| `brain_viz/` | TypeScript | Web 前端 — 3D 可视化、HITL 面板、开发者工具 | 100% |
| `brain_sdk/` | Python 3.11 | Python SDK (`brain-os` pip 包) | 34% |
| `brain_deploy/` | Docker/YAML | 部署工具与配置 | 47% |
| `brain_sim/` | Python/Gazebo | Gazebo / Isaac Sim 仿真环境 | 30% |
| `brain_models/` | 二进制 (Git LFS) | AI 模型权重存储 | 16% |
| `brain_docs/` | Markdown | 文档站点 (MkDocs Material) | 100% |

---

## 快速开始

```bash
# 安装依赖
pip install -e brain_ai/ -e brain_sdk/
cd brain_viz && npm install

# 端到端演示
python brain_sim/demo/e2e_demo.py --scenario pick_cup

# 运行测试
python tests/test_e2e_integration.py
python scripts/benchmark.py -n 50

# 构建 C++ 组件
cd brain_core/build && cmake .. && make -j$(nproc)

# 启动 Dashboard
cd brain_viz && npm run dev
```

---

## 核心特性

| 特性 | 描述 |
|------|------|
| 🧠 **LLM 认知引擎** | Qwen2.5-7B，支持中文自然语言指令 |
| 👁️ **实时感知** | ORB-SLAM3 定位 + YOLOv11 目标检测 |
| 🌳 **行为树执行** | BehaviorTree.CPP v4，预定义技能库 |
| 🛤️ **多轨迹规划** | MoveIt 2 + TRAC-IK 生成 3-5 条候选轨迹 |
| 👤 **人在回路 (HITL)** | 3 秒内人类选择轨迹，超时自动执行 |
| 🔒 **安全监控** | 1000Hz 硬件级检测，< 5ms 急停 |
| 📊 **3D Dashboard** | Three.js 可视化 + WebSocket 实时推送 |
| 🎤 **语音控制** | 中文语音识别 + TTS 反馈 |

---

## 技术栈

| 组件 | 技术 |
|------|------|
| **实时引擎** | C++17, ROS 2 Humble, BehaviorTree.CPP v4, MoveIt 2, TRAC-IK, FCL |
| **AI 引擎** | Python 3.11, Qwen2.5-7B/TensorRT-LLM, ORB-SLAM3, YOLOv11 ONNX |
| **Web 前端** | TypeScript, Next.js 14, Three.js, Zustand, Tailwind CSS |
| **通信** | gRPC (Protobuf), WebSocket, ROS 2 |
| **仿真** | Gazebo, Isaac Sim |
| **目标硬件** | Jetson Orin + Kinova Gen3 + TurtleBot 4 |

---

## 文档

### 设计文档

- [头脑风暴](00_docs/01_头脑风暴文档.md)
- [系统功能设计 (DDD)](00_docs/02_系统功能设计.md)
- [系统架构设计](00_docs/03_系统架构设计.md)
- [系统数据设计](00_docs/04_系统数据设计.md)
- [系统交互设计](00_docs/05_系统交互设计.md)
- [开发进度](00_docs/06_开发进度文档.md)
- [技术选型](00_docs/07_技术选型决策记录.md)
- [工程目录](00_docs/08_工程目录文档.md)
- [开发环境搭建](00_docs/09_开发环境搭建指南.md)
- [风险评估](00_docs/10_风险评估与缓解计划.md)
- [CI/CD 流水线](00_docs/11_CI&CD流水线设计.md)
- [Phase 1 回顾与 Phase 2 路线](00_docs/12_Phase1回顾与Phase2路线.md)

### 用户文档 (MkDocs)

```bash
cd brain_docs && mkdocs serve
```

---

## 开发

```bash
# 验证项目完整性
python scripts/scan_completion.py

# 验证 C++ 构建
python scripts/verify_brain_core_build.py

# 运行全部测试
python tests/test_e2e_integration.py

# 性能基准
python scripts/benchmark.py -n 100 -o benchmark_results/bm.json
```

---

## License

MIT
