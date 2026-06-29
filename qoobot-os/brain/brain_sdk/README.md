# QooBot Brain Python SDK

**仿生人操作系统 Python SDK** — 自然语言到机器人执行的完整工具链。

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)
[![Phase](https://img.shields.io/badge/Phase-1%20原型验证-brightgreen.svg)](https://github.com/qoobots/qoobot)

---

## 特性

| 功能 | 说明 |
|------|------|
| **自然语言交互** | 中文自然语言指令 → 意图解析 → 任务分解 → 行为树生成 |
| **场景感知** | 场景图、目标检测查询、SLAM 定位 |
| **运动规划** | 多候选轨迹生成、HITL 人工选择、紧急停止 |
| **安全监控** | 实时安全快照、告警流订阅、速度限幅 |
| **知识记忆** | 知识库检索、情景记忆存储与搜索 |
| **语音交互** | ASR 语音识别、TTS 语音合成、唤醒词 |
| **直接控制** | 关节/笛卡尔空间直接控制（调试/遥操作） |

## 安装

```bash
# PyPI (发布后)
pip install brain-os-sdk

# 从源码安装 (开发)
pip install -e .
```

## 快速开始

```python
import asyncio
from brain_os import BrainOSClient

async def main():
    async with BrainOSClient() as robot:
        # 1. 自然语言指令
        intent = await robot.cognition.parse_intent("把红色杯子放到桌上")
        print(f"意图: {intent['type']}, 置信度: {intent['confidence']}")

        # 2. 感知场景
        scene = await robot.perception.get_scene()
        objects = await robot.perception.query_objects("cup")
        print(f"场景中物体: {len(objects)} 个杯子")

        # 3. 任务分解 + 行为树
        plan = await robot.cognition.decompose_task(intent, scene_graph=scene)
        tree = await robot.cognition.generate_behavior_tree(plan["plan_id"], plan["subtasks"])

        # 4. 执行规划
        result = await robot.decision.execute_plan(tree, require_hitl=True)
        if result.get("hitl_event"):
            trajs = await robot.decision.generate_trajectories(result["plan_id"], {})
            best = trajs[0]
            print(f"选择轨迹: {best['description']} (评分: {best['score']})")
            await robot.decision.select_trajectory(result["plan_id"], best["trajectory_id"])

        # 5. 检查安全
        safety = await robot.safety.get_snapshot()
        print(f"安全状态: {safety['state']}")

asyncio.run(main())
```

## API 命名空间

```python
client = BrainOSClient()

# 认知 — 自然语言理解
client.cognition.parse_intent("...")       # 意图解析
client.cognition.decompose_task(intent)     # 任务分解
client.cognition.generate_behavior_tree()   # 行为树生成

# 决策 — 规划执行
client.decision.execute_plan(tree)          # 执行规划
client.decision.generate_trajectories()     # 轨迹生成
client.decision.select_trajectory()         # HITL 选择
client.decision.cancel_plan()               # 取消规划

# 感知 — 场景理解
client.perception.get_scene()               # 场景图
client.perception.query_objects("cup")      # 目标查询
client.perception.get_localization()        # SLAM 定位

# 控制 — 运动执行
client.control.execute_trajectory()         # 执行轨迹
client.control.emergency_stop()             # 紧急停止
client.control.open_gripper()              # 打开夹爪
client.control.close_gripper()             # 关闭夹爪
client.control.move_joints({"joint_1": 0.5}) # 直接关节控制
client.control.move_to_pose(pose)          # 笛卡尔位姿控制

# 安全 — 监控保护
client.safety.get_snapshot()               # 安全快照
client.safety.set_velocity_scale(0.5)      # 速度限幅

# 知识 — 记忆检索
client.knowledge.search("如何抓取玻璃杯")    # 知识库检索
client.knowledge.search_episodes("pick")    # 情景记忆搜索
client.knowledge.store_episode(episode)     # 存储情景

# 语音 — 语音交互
client.speech.recognize_speech(audio)      # 语音识别
client.speech.say("任务完成")               # 语音播报
client.speech.listen_for_wake_word()        # 唤醒词监听
```

## 配置

支持环境变量和代码初始化：

```python
from brain_os import BrainOSConfig

# 环境变量
config = BrainOSConfig.from_env()

# 代码初始化
config = BrainOSConfig(
    grpc_host="192.168.1.100",
    grpc_port=50051,
    robot_id="kinova_01",
    grpc_timeout_sec=30.0,
)
client = BrainOSClient(config)
```

环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BRAIN_OS_GRPC_HOST` | localhost | gRPC 服务地址 |
| `BRAIN_OS_GRPC_PORT` | 50051 | gRPC 端口 |
| `BRAIN_OS_WS_URL` | ws://localhost:8765 | WebSocket 事件流 |
| `BRAIN_OS_TLS` | false | 启用 TLS |
| `BRAIN_OS_TLS_CERT` | — | TLS 证书路径 |
| `BRAIN_OS_ROBOT_ID` | robot_01 | 机器人标识 |
| `BRAIN_OS_LOG_LEVEL` | INFO | 日志级别 |

## 示例

完整示例见 `examples/` 目录：

- `basic_connect.py` — 最小连接示例
- `voice_interaction.py` — 语音交互示例
- `task_execution.py` — 端到端任务执行
- `hitl_mode.py` — HITL 人机协同流程

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 代码检查
ruff check brain_os/
mypy brain_os/
```

## 架构

```
brain_os/                   # SDK 主包
├── client.py               # 统一客户端入口 (BrainOSClient)
├── config.py               # 配置管理 (BrainOSConfig)
├── connection.py           # gRPC 连接管理
├── cognition/              # 认知: 意图解析 + 任务分解
├── decision/               # 决策: 规划执行 + 轨迹选择
├── perception/             # 感知: 场景图 + 目标查询
├── control/                # 控制: 运动执行 + 直接控制
├── safety/                 # 安全: 监控 + 紧急停止
├── knowledge/              # 知识: 检索 + 情景记忆
├── speech/                 # 语音: ASR + TTS + 唤醒词
├── types/                  # 公共数据类型
├── utils/                  # 工具: 异常 + 异步辅助
└── proto_gen/              # gRPC/Protobuf 自动生成
```

## 许可证

Apache-2.0
