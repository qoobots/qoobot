# 架构概览

QooBot Brain 采用分层架构设计，遵循领域驱动设计 (DDD) 原则，将仿生人的完整技术栈组织为五个核心层。

---

## 五层架构

```
┌─────────────────────────────────────────────────────────┐
│                    接口层 (Interface)                     │
│  brain_viz (Web Dashboard) + WebSocket + Voice I/O       │
├─────────────────────────────────────────────────────────┤
│                    认知层 (Cognition)                     │
│  brain_ai: LLM Agent → Intent Parser → Task Decomposer  │
│             → BehaviorTree Generator                     │
├─────────────────────────────────────────────────────────┤
│                    决策层 (Decision)                      │
│  brain_ai: Motion Planning → Trajectory Selection        │
│             → HITL Manager → Event Dispatcher            │
├─────────────────────────────────────────────────────────┤
│                    感知层 (Perception)                    │
│  brain_ai: YOLOv11 → ORB-SLAM3 → Scene Graph            │
│             → Object Tracking → 3DGS Rendering           │
├─────────────────────────────────────────────────────────┤
│                    执行层 (Execution)                     │
│  brain_core: BehaviorTree Executor → IK Solver           │
│              → Trajectory Generator → Joint Controller   │
│              → Safety Monitor → ROS2 Bridge              │
└─────────────────────────────────────────────────────────┘
```

---

## 层间通信

```
brain_viz (Web)
    │ WebSocket (JSON)       │ gRPC (Protobuf)
    ▼                        ▼
brain_ai (Python)
    │ gRPC (Protobuf)
    ▼
brain_core (C++)
    │ ROS 2
    ▼
硬件 (Kinova Gen3 + TurtleBot 4)
```

| 链路 | 协议 | 序列化 | 延迟 |
|------|------|--------|------|
| brain_viz ↔ brain_ai | WebSocket + gRPC | JSON / Protobuf | < 5ms |
| brain_ai ↔ brain_core | gRPC | Protobuf | < 2ms |
| brain_core ↔ 硬件 | ROS 2 | ROS msg | < 1ms |

---

## 三大子系统

### brain_core (C++17 实时引擎)

**定位**：实时控制与安全核心

| 模块 | 功能 | 频率 |
|------|------|------|
| **ROS2 Bridge** | Topic 发布/订阅、Service 调用 | 1000 Hz |
| **Behavior Engine** | BehaviorTree.CPP v4 执行器 | 100 Hz |
| **Motion Planner** | TRAC-IK 逆运动学 + Trajectory Generation | 50 Hz |
| **Safety Monitor** | FCL 碰撞检测 + Emergency Stop | 1000 Hz |
| **HAL Interface** | 硬件抽象层（电机/传感器） | 1000 Hz |
| **gRPC Client** | 与 brain_ai 通信 | on-demand |

### brain_ai (Python 3.11 认知引擎)

**定位**：高层认知与决策

| 模块 | 功能 |
|------|------|
| **LLM Agent** | Qwen2.5-7B，中文 NL 理解 |
| **Intent Parser** | 自然语言 → 结构化意图 |
| **Task Decomposer** | 意图 → 子任务 DAG |
| **BT Generator** | 子任务 → BehaviorTree XML |
| **Planner** | 轨迹生成 + 多策略评分 |
| **HITL Manager** | 人在回路决策管理 |
| **Knowledge Base** | 经验存储、技能库、语义检索 |
| **Perception Service** | 目标检测、定位、场景图 |

### brain_viz (TypeScript 可视化前端)

**定位**：人机交互界面

| 组件 | 功能 |
|------|------|
| **Scene View** | Three.js 3D 场景渲染 |
| **ChatPanel** | 文本/语音指令输入 |
| **HITL Panel** | 轨迹选择、参数微调 |
| **Status Monitor** | 实时指标、日志、警报 |
| **Dev Panel** | API 测试、技能表、行为树查看 |

---

## 数据流

### 指令执行完整链路

```
1. "把杯子拿给我" (中文语音/文本)
        ↓
2. VoiceIO / ChatPanel → brain_ai (WebSocket)
        ↓
3. LLM Agent → Intent Parser → INTENT_PICK {target: "cup", source: "table"}
        ↓
4. Task Decomposer → [navigate → detect → pick → place]
        ↓
5. BT Generator → BehaviorTree XML
        ↓
6. Motion Planner → 3-5 candidate trajectories
        ↓
7. HITL Manager → user selects / auto-select
        ↓
8. Joint Controller → execute on Kinova Gen3
        ↓
9. Safety Monitor → continuous collision check
        ↓
10. Status update → WebSocket → Dashboard rendering
```

---

## 关键设计原则

| 原则 | 实现 |
|------|------|
| **关注点分离** | C++ 实时 vs Python 认知 vs TypeScript 界面 |
| **异步通信** | gRPC 用于服务调用，WebSocket 用于实时推送 |
| **容错优先** | 每层独立 Mock 模式，支持离线开发 |
| **安全第一** | 1000Hz 独立安全线程，< 5ms 急停响应 |
| **人在回路** | 高风险决策始终需要人类确认 |

---

## 部署架构

```
┌──────────────────────────────────────────────┐
│              开发工作站 / 云端                 │
│  ┌─────────────┐  ┌─────────────────────┐    │
│  │ brain_viz    │  │  brain_ai (gRPC)    │    │
│  │ (Next.js)    │  │  + WebSocket Server │    │
│  └──────┬───────┘  └──────────┬──────────┘    │
│         │                     │               │
│         └──── WebSocket ──────┘               │
└──────────────────────────────────────────────┘
                      │ gRPC
┌─────────────────────▼────────────────────────┐
│            Jetson Orin (机器人端)              │
│  ┌─────────────────────────────────────────┐ │
│  │  brain_core (C++17)                     │ │
│  │  ├── ROS 2 Node                         │ │
│  │  ├── Behavior Engine                    │ │
│  │  ├── Motion Planner                     │ │
│  │  └── Safety Monitor                     │ │
│  └──────────────┬──────────────────────────┘ │
│                 │ ROS 2                      │
│  ┌──────────────▼──────────────────────────┐ │
│  │  硬件驱动 (Kinova Gen3 + TurtleBot 4)    │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

---

## 下一步

- [模块说明](modules.md) — 各模块详细技术栈
- [贡献指南](contributing.md) — 参与开发
