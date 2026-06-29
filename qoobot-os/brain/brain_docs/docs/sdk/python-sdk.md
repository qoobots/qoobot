# Python SDK 概览

Brain OS Python SDK 提供简洁的编程接口，让你通过 Python 代码控制机器人。

---

## 安装

```bash
pip install brain-sdk
# 或从源码安装
pip install -e brain_sdk/
```

---

## 快速开始

```python
from brain_sdk import RobotClient

# 创建客户端（自动连接 gRPC 和 WebSocket）
robot = RobotClient("localhost:50052")

# 一句话控制机器人
result = robot.execute("把桌上的红色杯子拿给我")
print(f"任务{'成功' if result.success else '失败'}，耗时 {result.total_ms:.0f}ms")
```

---

## 客户端架构

`RobotClient` 是统一的入口，内部包含 5 个模块：

```
RobotClient
├── cognition   -- 意图解析、任务分解、行为树生成
├── decision    -- 轨迹生成、选择、计划管理
├── perception  -- 场景图、定位、目标查询
├── control     -- 关节控制、轨迹执行、抓手操作
├── safety      -- 安全状态、急停、警报
└── knowledge   -- 技能库、经验存储、知识检索
```

---

## 模块一览

### Cognition（认知）

```python
# 解析意图
intent = robot.cognition.parse_intent("把杯子拿给我")
print(intent.type, intent.confidence)  # INTENT_PICK 0.88

# 分解任务
subtasks = robot.cognition.decompose_task(intent)

# 生成行为树
bt = robot.cognition.generate_bt(plan_id, subtasks)
```

### Decision（决策）

```python
# 生成轨迹
trajs = robot.decision.generate_trajectories(
    plan_id, target_pose, num_candidates=5
)

# 选择轨迹
selected = robot.decision.select_trajectory(plan_id, trajs[0].id)

# 取消计划
robot.decision.cancel_plan(plan_id, reason="user_request")
```

### Perception（感知）

```python
# 获取场景图
scene = robot.perception.get_scene_graph()

# 查询特定物体
objects = robot.perception.query_objects(label="cup", min_conf=0.7)

# 获取定位
pose = robot.perception.get_localization()
```

### Control（控制）

```python
# 控制关节（弧度/秒）
robot.control.send_joint_command({"elbow": 0.5})

# 控制抓手
robot.control.open_gripper()
robot.control.close_gripper()

# 执行轨迹
robot.control.execute_trajectory(trajectory)

# 回到初始位姿
robot.control.go_home()
```

### Safety（安全）

```python
# 查询安全状态
status = robot.safety.get_status()

# 紧急停止
robot.safety.emergency_stop()

# 释放急停
robot.safety.release_emergency_stop()

# 确认警报
robot.safety.acknowledge_alert(alert_id)
```

### Knowledge（知识库）

```python
# 搜索历史经验
episodes = robot.knowledge.search_episodes(
    "抓取红色物体", top_k=5, success_only=True
)

# 查询技能库
skills = robot.knowledge.list_skills()

# 存储经验
robot.knowledge.store_episode(episode)
```

---

## 事件监听

通过 WebSocket 订阅实时事件：

```python
def on_plan_status(event):
    print(f"计划状态更新: {event.status}")

def on_safety_alert(event):
    print(f"安全警报: {event.level} - {event.message}")

# 注册监听器
robot.subscribe("plan_status", on_plan_status)
robot.subscribe("safety_alert", on_safety_alert)

# 开始事件循环
robot.listen()
```

---

## 配置

```python
robot = RobotClient(
    host="192.168.1.100",        # gRPC 主机
    port=50052,                   # gRPC 端口
    ws_port=8765,                 # WebSocket 端口
    timeout=5.0,                  # 默认超时（秒）
    mock_mode=False,              # 离线模式（用模拟数据）
)
```

---

## 错误处理

```python
from brain_sdk.exceptions import (
    ConnectionError, TimeoutError, SafetyError
)

try:
    robot.control.execute_trajectory(traj)
except SafetyError as e:
    print(f"安全异常: {e}")
    robot.safety.emergency_stop()
except ConnectionError as e:
    print(f"连接丢失: {e}")
except TimeoutError as e:
    print(f"操作超时: {e}")
```

---

## 下一步

- [API 参考](api-reference.md) — 完整的 API 文档
- [示例代码](examples.md) — 更多场景示例
