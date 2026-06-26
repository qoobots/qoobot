<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)">
    <img alt="Brain OS" src="brain_docs/assets/logo.svg" width="420">
  </picture>
</p>

<p align="center">
  <strong>Humanoid Robot Operating System</strong><br>
  Full-stack platform from natural language commands to robot execution
</p>

<p align="center">
  <a href="https://github.com/brain-os/brain-os/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/C++-17-blue.svg" alt="C++"></a>
  <a href="#"><img src="https://img.shields.io/badge/version-1.0.0--alpha-orange.svg" alt="Version"></a>
  <a href="#"><img src="https://img.shields.io/badge/build-passing-brightgreen.svg" alt="Build"></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-143%20passed-success.svg" alt="Tests"></a>
  <a href="#"><img src="https://img.shields.io/badge/ROS-2%20Humble-22314E.svg" alt="ROS 2"></a>
</p>

<p align="center">
  <a href="README_zh.md">中文文档</a>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Features](#core-features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage Examples](#usage-examples)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Community & Support](#community--support)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

Brain OS is a robot operating system purpose-built for **humanoid robots**. It unifies large language models (LLM), computer vision, motion planning, and real-time control into a single end-to-end pipeline — enabling robots to **understand natural language, perceive their environment, plan actions, and execute safely**.

### Why Brain OS?

|  | Traditional Robot Frameworks | Brain OS |
|------|-------------|----------|
| **Interaction** | Programming / Teach pendant | Natural language conversation |
| **Task Understanding** | Predefined scripts | LLM semantic understanding + task decomposition |
| **Perception** | Single sensor | Multi-modal fusion (RGB-D + LiDAR + SLAM) |
| **Motion Planning** | Single trajectory | Multi-strategy candidates + human selection (HITL) |
| **Safety** | External dependency | Hardware-level 1000Hz built-in safety monitor |
| **Visualization** | 2D panels | Web 3D real-time dashboard |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Layer 5  Application                         │
│        Home Service   •   Industrial   •   Logistics            │
├─────────────────────────────────────────────────────────────────┤
│                     Layer 4  Interface                           │
│        gRPC API   │   ROS 2 Bridge   │   WebSocket              │
├─────────────────────────────────────────────────────────────────┤
│                   Layer 3  Business Logic                        │
│  Cognition Engine   │   Decision Engine   │   Safety Engine     │
│     (brain_ai)      │                     │    (brain_core)     │
├─────────────────────────────────────────────────────────────────┤
│                   Layer 2  Foundation Services                   │
│  Perception   │   Motion Control   │   Knowledge   │   Viz      │
├─────────────────────────────────────────────────────────────────┤
│                   Layer 1  Foundation Models                     │
│  LLM Service (Qwen2.5-7B)  │  CV Service (YOLOv11/ORB-SLAM3)   │
├─────────────────────────────────────────────────────────────────┤
│                   Layer 0  Infrastructure                        │
│       ROS 2 Humble  │  NVIDIA CUDA  │  Docker                   │
└─────────────────────────────────────────────────────────────────┘
```

### Communication Topology

```
                  gRPC-Web                              gRPC
  brain_viz ──────────────────▶ Envoy Proxy ──────────────────────┐
  (TypeScript)                 (Proxy)                            │
      │                                                            ▼
      │                                                     brain_ai (Python)
      └──────── WebSocket ─────────────────────────────────▶ LLM + Perception
                                                                │
                                                          gRPC  │
                                                                │
                                                          ROS 2 ▼
                                                         brain_core (C++)
                                                       Real-Time Engine
                                                              │
                                                       ROS 2 DDS
                                                              │
                                                      Robot Hardware
                                                    (Kinova + TurtleBot)
```

---

## Core Features

### 🧠 LLM Cognition Engine
Powered by **Qwen2.5-7B** for Chinese semantic understanding:
- Natural language command → structured intent parsing
- Intent → automatic DAG task decomposition
- Subtasks → BehaviorTree XML code generation
- Function calling with multi-tool orchestration and context memory

### 👁️ Multi-Modal Perception Pipeline
- **Localization**: ORB-SLAM3 real-time SLAM (mono/stereo/RGB-D)
- **Detection**: YOLOv11 ONNX inference at >30 FPS
- **Segmentation**: SAM 2 instance segmentation
- **Reconstruction**: 3D Gaussian Splatting scene reconstruction
- **Fusion**: Multi-sensor Scene Graph aggregation

### 🌳 Behavior Tree Execution Engine
- **BehaviorTree.CPP v4**: Production-grade behavior tree runtime
- **10 predefined action nodes**: `pick` / `place` / `navigate` / `detect` / `HITL_confirm` and more
- **100Hz Tick**: Real-time response and re-planning

### 🛤️ Multi-Strategy Trajectory Planning
- **MoveIt 2 + TRAC-IK**: Kinematic solving and collision detection
- **5 planning strategies**: OPTIMAL / CONSERVATIVE / AGGRESSIVE / EXPLORATORY / ADVERSARIAL
- Generates 3–5 candidate trajectories per instruction with scoring and ranking

### 👤 Human-in-the-Loop (HITL)
- **3-second countdown**: Human operators select optimal trajectory from dashboard
- **Auto-execution on timeout**: Falls back to highest-scored trajectory
- **Parameter tuning**: Real-time adjustment of execution parameters

### 🔒 Real-Time Safety Monitoring
- **1000Hz monitoring**: Hardware-level collision prediction
- **4-level safety state machine**: NORMAL → WARNING → CRITICAL → EMERGENCY
- **<5ms emergency stop**: FCL collision detection + force/torque monitoring
- **Watchdog mechanism**: Automatic degradation on communication loss

### 📊 3D Web Dashboard
- **Three.js + React Three Fiber**: Real-time 3D scene rendering
- **5 camera presets**: Top-down / Follow / Free / First-person / Fixed
- **Ghost trajectories**: Visualize multiple candidate trajectories simultaneously
- **WebSocket push**: Real-time sync of status, logs, and perception results

### 🎤 Voice Interaction
- **ASR**: Chinese speech recognition (Whisper / Web Speech API)
- **TTS**: Natural speech synthesis feedback
- **Full-duplex**: Interruption handling and multi-turn dialogue

---

## Project Structure

```
brain-os/
├── brain_proto/         Protobuf       gRPC service & message definitions (13 .proto)
├── brain_core/          C++17          Real-time engine — ROS 2 bridge, behavior trees, safety, motion
├── brain_ai/            Python 3.11    AI engine — LLM agent, perception pipeline, task planning, gRPC
├── brain_viz/           TypeScript     Web frontend — 3D visualization, HITL panel, developer tools
├── brain_sdk/           Python 3.11    Python SDK (brain-os pip package, full gRPC client)
├── brain_deploy/        Docker/YAML    Deployment tooling (Docker/Compose/K8s/DEB/Envoy)
├── brain_sim/           Python         Gazebo / Isaac Sim simulation (643-line e2e demo)
├── brain_models/        Binary (LFS)   AI model weights + registry + download/convert scripts
├── brain_docs/          Markdown       MkDocs Material documentation site
├── scripts/             Python/Shell   Developer tool scripts
└── tests/               Python         End-to-end integration tests
```

---

## Quick Start

### Prerequisites

| Dependency | Minimum Version | Notes |
|------|---------|------|
| Python | 3.11+ | AI engine + SDK |
| Node.js | 18+ | Web Dashboard |
| CMake | 3.22+ | C++ real-time engine build |
| ROS 2 | Humble | (Optional) Robot hardware communication |
| Docker | 24+ | (Optional) Containerized deployment |

### 5-Minute Quickstart

```bash
# 1. Clone the repository
git clone https://github.com/brain-os/brain-os.git
cd brain-os

# 2. Install Python dependencies
pip install -e brain_ai/ -e brain_sdk/

# 3. Install frontend dependencies
cd brain_viz && npm install && cd ..

# 4. Run end-to-end demo
python brain_sim/demo/e2e_demo.py --scenario pick_cup

# 5. Launch Dashboard (new terminal)
cd brain_viz && npm run dev
# Visit http://localhost:3000
```

---

## Installation

### Python (AI Engine + SDK)

```bash
# Basic installation
pip install -e brain_ai/
pip install -e brain_sdk/

# Full AI features (with GPU inference)
pip install -e "brain_ai/[ai]"

# Simulation features
pip install -e ".[sim]"

# Development dependencies
pip install -e ".[dev]"
```

### C++ (Real-Time Engine)

```bash
cd brain_core
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

# Verify build
python scripts/verify_brain_core_build.py
```

### TypeScript (Web Dashboard)

```bash
cd brain_viz
npm install
npm run dev          # Development mode
npm run build        # Production build
```

### Docker One-Click Deploy

```bash
docker compose up -d
```

---

## Usage Examples

### Python SDK

```python
from brain_os import BrainOSClient

# Create client
client = BrainOSClient("localhost:50051")

# Send natural language command
response = client.cognition.parse_intent("Pick up the red cup on the table for me")

# Get task decomposition result
print(f"Task type: {response.intent.type}")
print(f"Subtasks: {len(response.plan.subtasks)}")
for task in response.plan.subtasks:
    print(f"  - {task.name}: {task.description}")

# Execute task (with HITL)
result = client.decision.execute(response.plan.id, hitl_timeout=3.0)
print(f"Execution result: {result.status}")
```

### CLI Console

```bash
# Interactive conversation
python -m brain_ai.cli chat

# Batch command testing
python scripts/benchmark.py -n 50 --scenario household
```

### API Testing

```bash
# gRPC call via grpcurl
grpcurl -plaintext -d '{"text":"Move to the kitchen"}' \
  localhost:50051 brain_ai.CognitionService/ParseIntent
```

---

## Documentation

| Document | Description |
|------|------|
| [Brainstorming](00_docs/01_头脑风暴文档.md) | Project origin & vision |
| [Architecture Design](00_docs/03_系统架构设计.md) | C4 model + DDD layered architecture |
| [Functional Design](00_docs/02_系统功能设计.md) | DDD domain modeling |
| [Data Design](00_docs/04_系统数据设计.md) | Data model & storage strategy |
| [Interaction Design](00_docs/05_系统交互设计.md) | gRPC protocol & event flow |
| [Development Progress](00_docs/06_开发进度文档.md) | Sprint plan & completion status |
| [Technology Decisions](00_docs/07_技术选型决策记录.md) | Architecture decision records |
| [Project Directory](00_docs/08_工程目录文档.md) | Full directory structure |
| [Dev Environment Setup](00_docs/09_开发环境搭建指南.md) | From-scratch environment guide |
| [Risk Assessment](00_docs/10_风险评估与缓解计划.md) | Technical risks & mitigations |
| [CI/CD Pipeline](00_docs/11_CI&CD流水线设计.md) | Continuous integration & deployment |
| [Phase 2 Roadmap](00_docs/12_Phase1回顾与Phase2路线.md) | Next-phase planning |

### User Docs

```bash
cd brain_docs && mkdocs serve
# Visit http://localhost:8000
```

---

## Tech Stack

| Layer | Technology |
|------|---------|
| **Real-Time Engine** | C++17, ROS 2 Humble, BehaviorTree.CPP v4, MoveIt 2, TRAC-IK, FCL |
| **AI Engine** | Python 3.11, Qwen2.5-7B/TensorRT-LLM, ORB-SLAM3, YOLOv11 ONNX, SAM 2 |
| **Web Frontend** | TypeScript, Next.js 14, Three.js, React Three Fiber, Zustand, Tailwind CSS |
| **Communication** | gRPC (Protobuf), WebSocket, ROS 2 DDS (Fast-DDS/Cyclone) |
| **Simulation** | Gazebo, Isaac Sim |
| **Deployment** | Docker, Envoy Proxy, Docker Compose |
| **Target Hardware** | NVIDIA Jetson Orin + Kinova Gen3 + TurtleBot 4 |

---

## Roadmap

### Phase 1 (Complete) — Prototype Validation ✅

- [x] Foundation skeleton (Sprint 1)
- [x] LLM cognition engine (Sprint 2)
- [x] Multi-modal perception pipeline (Sprint 3)
- [x] C++ real-time engine (Sprint 4)
- [x] 3D Web Dashboard (Sprint 5)
- [x] 143 test cases all passing
- [x] 12 end-to-end integration tests

### Phase 2 (In Progress) — Hardware Validation & Production Polish

| Priority | Task | Milestone |
|--------|------|----------|
| **P0** | `brain_sim` physics simulation refinement | M6 (Week 28) |
| **P0** | `brain_models` model weight deployment | M6 (Week 28) |
| **P1** | `brain_core` hardware integration (Jetson Orin + Kinova) | M7 (Week 32) |
| **P1** | `brain_sdk` pip package release | M8 (Week 36) |
| **P2** | DeepSeek-V3 cloud integration | M9 (Week 40) |
| **P2** | `brain_viz` performance optimization | M9 (Week 40) |

### Future

- [ ] Multi-robot collaborative scheduling
- [ ] Multi-modal VLA (Vision-Language-Action) end-to-end model
- [ ] Edge-cloud hybrid inference
- [ ] Android/iOS mobile Dashboard
- [ ] Sim2Real transfer learning

---

## Contributing

We welcome contributions of all kinds! Please read the guidelines below:

### Development Workflow

```bash
# 1. Fork the repo and create a branch
git checkout -b feature/your-feature

# 2. Install dev dependencies
pip install -e ".[dev]"
pre-commit install

# 3. Write code and pass checks
ruff check . && mypy brain_ai/ brain_sdk/
pytest brain_ai/tests/ brain_sdk/tests/ -v

# 4. Submit Pull Request
# PR title format: [type] Brief description
# Types: feat / fix / docs / refactor / test / chore
```

### Code Standards

- **Python**: [Ruff](https://docs.astral.sh/ruff/) (PEP 8) + [mypy](https://mypy-lang.org/) (strict mode)
- **C++**: [Google C++ Style Guide](https://google.github.io/styleguide/cppguide.html) + clang-format
- **TypeScript**: ESLint + Prettier
- **Commit**: [Conventional Commits](https://www.conventionalcommits.org/)

### PR Review Checklist

- [ ] All tests pass (`pytest` / `gtest` / `npm test`)
- [ ] Code passes lint checks
- [ ] New features include test cases
- [ ] Relevant documentation updated
- [ ] Commit messages follow the convention

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

---

## Community & Support

- 📖 [Documentation](https://brain-os.readthedocs.io/)
- 🐛 [Issue Tracker](https://github.com/brain-os/brain-os/issues)
- 💬 [Discussions](https://github.com/brain-os/brain-os/discussions)
- 📧 [Mailing List](mailto:dev@brain-os.org)

---

## License

Brain OS is licensed under the [Apache License 2.0](LICENSE).

Copyright 2026 Brain OS Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0

---

## Acknowledgments

Brain OS builds upon the outstanding work of these open-source projects:

- [ROS 2](https://ros.org/) — Robot Operating System
- [BehaviorTree.CPP](https://www.behaviortree.dev/) — Behavior tree engine
- [MoveIt 2](https://moveit.ai/) — Motion planning framework
- [TRAC-IK](https://bitbucket.org/traclabs/trac_ik/) — Inverse kinematics solver
- [Qwen2.5](https://github.com/QwenLM/Qwen2.5) — Large language model
- [YOLOv11](https://github.com/ultralytics/ultralytics) — Object detection
- [ORB-SLAM3](https://github.com/UZ-SLAMLab/ORB_SLAM3) — SLAM system
- [Three.js](https://threejs.org/) — 3D rendering engine
- [gRPC](https://grpc.io/) — High-performance RPC framework

---

<p align="center">
  <sub>Built with ❤️ by the Brain OS Team</sub>
</p>
