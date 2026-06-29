# SDK API 参考

本文档列出 QooBot Brain Python SDK 的全部公开 API。

---

## RobotClient

统一客户端入口。

```python
class RobotClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 50052,
        ws_port: int = 8765,
        timeout: float = 5.0,
        mock_mode: bool = False,
    )
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | `str` | `"localhost"` | gRPC 服务器地址 |
| `port` | `int` | `50052` | gRPC 端口 |
| `ws_port` | `int` | `8765` | WebSocket 端口 |
| `timeout` | `float` | `5.0` | 默认 RPC 超时（秒） |
| `mock_mode` | `bool` | `False` | 离线模拟模式 |

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `cognition` | `CognitionClient` | 认知引擎客户端 |
| `decision` | `DecisionClient` | 决策引擎客户端 |
| `perception` | `PerceptionClient` | 感知引擎客户端 |
| `control` | `ControlClient` | 控制客户端 |
| `safety` | `SafetyClient` | 安全监控客户端 |
| `knowledge` | `KnowledgeClient` | 知识库客户端 |

### 方法

| 方法 | 返回值 | 说明 |
|------|--------|------|
| `execute(instruction: str)` | `ExecuteResult` | 一句话执行完整流水线 |
| `subscribe(event: str, callback)` | `None` | 订阅 WebSocket 事件 |
| `unsubscribe(event: str)` | `None` | 取消订阅 |
| `listen()` | `None` | 启动事件循环（阻塞） |
| `close()` | `None` | 关闭连接 |

---

## CognitionClient

```python
class CognitionClient:
    def parse_intent(
        self,
        utterance: str,
        language: str = "zh-CN",
    ) -> Intent

    def decompose_task(
        self,
        intent: Intent,
        robot_id: str = "",
    ) -> DecomposeTaskResponse

    def generate_bt(
        self,
        plan_id: str,
        subtasks: list[SubTask],
        robot_id: str = "",
    ) -> BehaviorTree

    def clarify(
        self,
        request: ClarifyRequest,
    ) -> ClarifyResponse
```

---

## DecisionClient

```python
class DecisionClient:
    def generate_trajectories(
        self,
        robot_id: str,
        plan_id: str,
        target_pose: Pose,
        num_candidates: int = 5,
    ) -> list[Trajectory]

    def select_trajectory(
        self,
        robot_id: str,
        plan_id: str,
        trajectory_id: str,
    ) -> SelectTrajectoryResponse

    def cancel_plan(
        self,
        robot_id: str,
        plan_id: str,
        reason: str = "",
    ) -> CancelPlanResponse
```

---

## PerceptionClient

```python
class PerceptionClient:
    def get_scene_graph(self) -> GetSceneGraphResponse

    def get_localization(self) -> GetLocalizationResponse

    def query_objects(
        self,
        label: str = "",
        min_conf: float = 0.5,
    ) -> list[DetectedObject]
```

---

## ControlClient

```python
class ControlClient:
    def send_joint_command(
        self,
        joint_positions: dict[str, float],
    ) -> None

    def control_gripper(self, open: bool) -> None

    def open_gripper(self) -> None

    def close_gripper(self) -> None

    def execute_trajectory(
        self,
        trajectory: Trajectory,
    ) -> None

    def stop_execution(self) -> None

    def go_home(self) -> None
```

---

## SafetyClient

```python
class SafetyClient:
    def get_status(self) -> SafetyStatus

    def emergency_stop(self) -> None

    def release_emergency_stop(self) -> None

    def acknowledge_alert(self, alert_id: str) -> None

    def on_change(self, callback) -> None
```

---

## KnowledgeClient

```python
class KnowledgeClient:
    def search_episodes(
        self,
        robot_id: str,
        query_text: str,
        top_k: int = 10,
        min_score: float = 0.5,
        success_only: bool = False,
    ) -> SearchEpisodesResponse

    def search_knowledge(
        self,
        query: str,
        type: int = 0,
        top_k: int = 10,
    ) -> SearchKnowledgeResponse

    def store_episode(
        self,
        episode: Episode,
    ) -> StoreEpisodeResponse

    def list_skills(
        self,
        tag_filter: str = "",
    ) -> list[Skill]

    def register_skill(
        self,
        skill: Skill,
    ) -> RegisterSkillResponse
```

---

## 核心数据类型

### Intent

```python
class Intent:
    type: IntentType     # 意图类型枚举
    raw_text: str        # 原始指令文本
    confidence: float    # 置信度 0.0-1.0
    params: dict         # 参数 (google.protobuf.Struct)
    language: str        # 语言代码
```

### SubTask

```python
class SubTask:
    task_id: str         # 子任务 ID
    skill_name: str      # 技能名称
    parameters: dict     # 参数
    depends_on: list[str] # 依赖的任务 ID
    status: TaskStatus   # 执行状态
    priority: float      # 优先级
```

### Trajectory

```python
class Trajectory:
    trajectory_id: str       # 轨迹 ID
    robot_id: str            # 机器人 ID
    joint_path: list         # 关节空间路径
    cartesian_path: list     # 笛卡尔空间路径
    score: float             # 质量评分 0.0-1.0
    duration_sec: float      # 预计执行时间
    description: str         # 描述
    is_recommended: bool     # 是否推荐
```

### BehaviorTree

```python
class BehaviorTree:
    tree_id: str         # 树 ID
    xml_str: str         # BT XML 字符串
    description: str     # 描述
```

---

## 异常类型

| 异常 | 说明 |
|------|------|
| `BrainError` | 基础异常 |
| `ConnectionError` | gRPC 连接失败 |
| `TimeoutError` | RPC 调用超时 |
| `SafetyError` | 安全违规 |
| `PlanningError` | 运动规划失败 |
| `PerceptionError` | 感知不可用 |
