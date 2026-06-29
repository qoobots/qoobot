# QooBot Brain 文档站点

欢迎使用 **QooBot Brain** 文档！

QooBot Brain 是一套面向仿生人的操作系统，提供从自然语言指令到机器人物理执行的完整技术栈。

---

## 快速导航

<div class="grid cards" markdown>

- :material-rocket-launch: **快速开始**

    ---

    从零开始，5 分钟内启动仿真演示。

    [:octicons-arrow-right-24: 安装指南](getting-started/installation.md)

- :material-monitor-dashboard: **Dashboard**

    ---

    了解 Web 可视化界面与人在回路（HITL）操作流程。

    [:octicons-arrow-right-24: Dashboard 指南](user-guide/dashboard.md)

- :material-code-braces: **Python SDK**

    ---

    用 Python 控制机器人，只需几行代码。

    [:octicons-arrow-right-24: SDK 文档](sdk/python-sdk.md)

- :material-architecture: **架构设计**

    ---

    深入了解五层架构与核心设计原则。

    [:octicons-arrow-right-24: 架构文档](development/architecture.md)

</div>

---

## 系统概述

```
自然语言指令 → 意图解析 → 任务分解 → 行为树 → 轨迹规划 → 运动执行
                                              ↕  HITL
                                         3D 可视化 Dashboard
```

### 核心特性

| 特性 | 描述 |
|------|------|
| 🧠 **LLM 认知引擎** | Qwen2.5-7B，支持中文自然语言指令 |
| 👁️ **实时感知** | ORB-SLAM3 定位 + YOLOv11 目标检测 |
| 🌳 **行为树执行** | BehaviorTree.CPP，预定义技能库 |
| 🛤️ **多轨迹规划** | MoveIt 2 生成 3-5 条候选轨迹 |
| 👤 **人在回路** | 3 秒内人类选择轨迹，超时自动执行 |
| 🔒 **安全监控** | 1000Hz 硬件级检测，< 5ms 急停 |

---

## 技术栈

=== "C++17 (brain_core)"
    - ROS 2 Humble
    - BehaviorTree.CPP v4
    - MoveIt 2 + TRAC-IK
    - gRPC（与 brain_ai 通信）

=== "Python 3.11 (brain_ai)"
    - Qwen2.5-7B / TensorRT-LLM
    - ORB-SLAM3 封装
    - YOLOv11 ONNX
    - gRPC 服务 + WebSocket 推送

=== "TypeScript (brain_viz)"
    - Next.js 14
    - Three.js / React Three Fiber
    - Zustand 状态管理
    - Tailwind CSS
