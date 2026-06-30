# 10 — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-30 | 状态：Draft
> 子项目：qoobot-os（仿生人操作系统）

---

## 1. API 体系总览

qoobot-os 提供四层 API，面向不同粒度的开发需求：

| API 层 | 协议 | 使用者 | 粒度 |
|--------|------|--------|:----:|
| Scene API | Python (brain_sdk) | 应用开发者 | 场景级 |
| Cognitive API | Python (brain_ai) | 算法开发者 | 功能级 |
| gRPC Service API | Protobuf | 进程间通信 | 服务级 |
| C/C++ Direct API | 头文件 + 共享库 | 硬件驱动开发者 | 底层 |

---

## 2. Scene API (场景级)

### 2.1 家居场景

```python
from qoobot_brain.scene import SmartHome

home = SmartHome(robot)

# 清洁
await home.clean_room("living_room", mode="vacuum")

# 整理
await home.tidy_up(target_objects=["toys", "books"])

# 递物
await home.fetch_and_deliver("water_bottle", to="sofa")

# 陪伴
await home.companion_mode(duration_minutes=30)
```

### 2.2 工业场景

```python
from qoobot_brain.scene import Industrial

industrial = Industrial(robot)

# 巡检
report = await industrial.patrol(
    route="warehouse_route_3",
    checkpoints=["temperature", "leak", "intrusion"]
)

# 搬运
await industrial.transport(
    payload=15.0,           # kg
    from_location="dock_A",
    to_location="shelf_42"
)

# 装配
await industrial.assemble(
    task_file="assembly/gearbox_v2.yaml"
)
```

### 2.3 通用场景基类

```python
class BaseScene:
    """所有场景的基类"""

    async def execute(self) -> SceneResult:
        """执行场景，返回结果"""
        ...

    async def pause(self):
        """暂停场景"""
        ...

    async def resume(self):
        """恢复场景"""
        ...

    async def cancel(self):
        """取消场景"""
        ...

    @property
    def status(self) -> SceneStatus:
        """场景状态: IDLE / RUNNING / PAUSED / ERROR / COMPLETED"""
        ...
```

---

## 3. Cognitive API (认知级)

### 3.1 感知 API

```python
class Perception:
    async def detect(self,
        image: np.ndarray,
        classes: Optional[list[str]] = None,
        confidence: float = 0.5
    ) -> list[Detection]:
        """目标检测，返回检测框列表"""
        ...

    async def segment(self,
        image: np.ndarray,
        task: str = "semantic"  # semantic / instance / panoptic
    ) -> SegmentationMask:
        """图像分割"""
        ...

    async def estimate_pose(self,
        observation: dict,
        target: str
    ) -> Pose6D:
        """6D 位姿估计"""
        ...

    async def track(self,
        object_id: str,
        stream: AsyncIterator[Frame]
    ) -> AsyncIterator[TrackResult]:
        """对象追踪（流式）"""
        ...
```

### 3.2 认知 API

```python
class Cognition:
    async def understand_scene(self,
        perceptions: list[PerceptionResult]
    ) -> SceneGraph:
        """场景理解，返回场景图"""
        ...

    async def recognize_intent(self,
        text: str,
        context: Optional[DialogContext] = None
    ) -> Intent:
        """意图识别"""
        ...

    async def query_knowledge(self,
        query: str,
        domain: str = "general"
    ) -> KnowledgeResult:
        """知识图谱查询"""
        ...
```

### 3.3 LLM/VLA API

```python
class LLM:
    async def chat(self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7
    ) -> str:
        """通用对话"""
        ...

    async def vla_infer(self,
        image: np.ndarray,
        instruction: str
    ) -> VLAOutput:
        """视觉语言动作推理

        Returns:
            VLAOutput:
                - action_type: str      # "pick" / "place" / "move" / "grasp"
                - target: str           # 目标物体
                - position: tuple       # 目标位置 (x, y, z)
                - trajectory: list      # 动作轨迹
                - confidence: float
        """
        ...
```

### 3.4 规划 API

```python
class Planning:
    async def create_task_plan(self,
        goal: str,
        context: SceneContext
    ) -> TaskPlan:
        """高层任务规划 (HTN/LLM-based)"""
        ...

    async def plan_motion(self,
        start: JointState,
        goal: Pose,
        constraints: Optional[MotionConstraints] = None
    ) -> MotionTrajectory:
        """运动规划 (IK + 轨迹生成 + 碰撞检测)"""
        ...

    async def plan_path(self,
        start_pose: Pose,
        goal_pose: Pose,
        costmap: Costmap2D
    ) -> Path:
        """路径规划 (A*/Dijkstra/TEB)"""
        ...
```

### 3.5 语音 API

```python
class Speech:
    async def speak(self,
        text: str,
        voice: str = "default",
        emotion: str = "neutral"
    ):
        """TTS 语音合成"""
        ...

    async def listen(self,
        duration: float = 5.0,
        language: str = "auto"
    ) -> str:
        """ASR 语音识别"""
        ...

    async def wake_word_detect(self) -> bool:
        """唤醒词检测 (阻塞直到唤醒)"""
        ...

    async def dialog(self,
        prompt: str,
        max_turns: int = 10
    ) -> AsyncIterator[str]:
        """多轮对话 (流式)"""
        ...
```

---

## 4. gRPC Service API (服务级)

### 4.1 ControlService

```protobuf
service ControlService {
    // 下发运动指令
    rpc SendMotionCommand(MotionCommand) returns (CommandAck);

    // 订阅关节状态
    rpc SubscribeJointStates(google.protobuf.Empty)
        returns (stream JointStateArray);

    // 紧急制动
    rpc EmergencyStop(EmergencyStopRequest) returns (EmergencyStopResponse);

    // 设置安全模式
    rpc SetSafetyMode(SafetyModeRequest) returns (SafetyModeResponse);
}

message MotionCommand {
    MotionType type = 1;  // JOINT_SPACE / CARTESIAN / VELOCITY
    repeated double target = 2;
    double duration_sec = 3;
    Priority priority = 4;  // HIGH / NORMAL / LOW
}

message JointStateArray {
    repeated JointState joints = 1;
    uint64 timestamp_ns = 2;
}
```

### 4.2 PerceptionService

```protobuf
service PerceptionService {
    // 执行推理
    rpc Infer(InferRequest) returns (InferResponse);

    // 流式推理 (视频流)
    rpc StreamInfer(stream Frame) returns (stream InferResult);

    // 获取模型信息
    rpc GetModelInfo(ModelInfoRequest) returns (ModelInfo);
}

message InferRequest {
    string model_name = 1;
    bytes input_data = 2;
    DataType dtype = 3;
    repeated int32 shape = 4;
    InferOptions options = 5;
}

message InferOptions {
    string backend = 1;      // "auto" / "npu" / "gpu" / "cpu"
    string precision = 2;    // "int8" / "fp16" / "fp32"
    int32 timeout_ms = 3;
}
```

### 4.3 NavigationService

```protobuf
service NavigationService {
    rpc NavigateToPose(NavGoal) returns (stream NavFeedback);
    rpc CancelNavigation(CancelRequest) returns (CancelResponse);
    rpc GetCurrentMap(MapRequest) returns (MapData);
    rpc SetZone(ZoneConfig) returns (ZoneResponse);
}

message NavGoal {
    Pose target_pose = 1;
    NavConstraints constraints = 2;
}

message NavFeedback {
    NavStatus status = 1;  // PLANNING / MOVING / NEAR_TARGET / ARRIVED / FAILED
    float distance_remaining = 2;
    float estimated_time_remaining = 3;
}
```

---

## 5. C/C++ Direct API (底层)

### 5.1 推理引擎 (ai-engine/)

```c
// 引擎
qoocore_engine_t* qoocore_engine_create(const qoocore_config_t* config);
void qoocore_engine_load_model(qoocore_engine_t* engine, const char* model_path);
qoocore_tensor_t* qoocore_engine_infer(qoocore_engine_t* engine, const qoocore_tensor_t* input);
void qoocore_engine_destroy(qoocore_engine_t* engine);

// 编译器
qoocore_compiler_t* qoocore_compiler_create(void);
int qoocore_compiler_compile(qoocore_compiler_t* c, const char* onnx_path,
                              const char* qoomodel_path, const qoocore_compile_options_t* opts);

// 性能剖析
qoocore_profile_t* qoocore_engine_profile(qoocore_engine_t* engine, const qoocore_tensor_t* input);
void qoocore_profile_to_json(const qoocore_profile_t* p, char* buf, size_t* len);
```

### 5.2 HAL 接口

```cpp
namespace qoobot::hal {

// 执行器
class ActuatorInterface {
public:
    virtual Status set_joint_position(const std::string& name, double rad, double time_sec) = 0;
    virtual Status set_joint_velocity(const std::string& name, double rad_per_sec) = 0;
    virtual Status set_joint_torque(const std::string& name, double nm) = 0;
    virtual JointState get_joint_state(const std::string& name) = 0;
    virtual std::vector<JointState> get_all_joint_states() = 0;
    virtual Status enable_emergency_stop() = 0;
};

// 传感器
class SensorInterface {
public:
    virtual Image capture_rgb(const std::string& camera) = 0;
    virtual Image capture_depth(const std::string& camera) = 0;
    virtual PointCloud capture_pointcloud(const std::string& lidar) = 0;
    virtual ImuData read_imu(const std::string& imu) = 0;
};

} // namespace qoobot::hal
```

---

## 6. API 版本管理

| 策略 | 说明 |
|------|------|
| 语义化版本 | `MAJOR.MINOR.PATCH` (gRPC service 版本号) |
| 向后兼容 | MAJOR 版本不兼容，MINOR 向后兼容，PATCH 仅修复 |
| 弃用策略 | 标记 `DEPRECATED` → 保留 2 个 MINOR 版本 → 移除 |
| API 文档 | Proto 注释自动生成文档，Python docstring + Sphinx |

### 6.1 gRPC 服务版本控制

```protobuf
// v1/control.proto
service ControlService {
    rpc SendMotionCommand(MotionCommand) returns (CommandAck);
}

// v2/control.proto (新增字段)
service ControlService {
    rpc SendMotionCommand(MotionCommand) returns (CommandAck);
    rpc SendMotionCommandV2(MotionCommandV2) returns (CommandAck);  // 新增
}
```

---

## 7. 错误码设计

### 7.1 统一错误码体系

| 范围 | 分类 | 说明 |
|------|------|------|
| 0 | SUCCESS | 成功 |
| 1~99 | SYSTEM | 系统级错误 (OOM/超时/内部) |
| 100~199 | CORE | ai-engine/ 推理引擎错误 |
| 200~299 | BRAIN | brain/ 认知决策错误 |
| 300~399 | HAL | hal/ 硬件错误 |
| 400~499 | SERVICE | services/ 服务错误 |
| 500~599 | SAFETY | 安全相关错误 |
| 600~699 | NETWORK | 网络通信错误 |

### 7.2 常用错误码

```cpp
enum class ErrorCode : int32_t {
    SUCCESS = 0,

    // System (1~99)
    SYSTEM_INTERNAL       = 1,
    SYSTEM_OOM            = 2,
    SYSTEM_TIMEOUT        = 3,
    SYSTEM_NOT_FOUND      = 4,
    SYSTEM_NOT_IMPLEMENTED= 5,

    // Core (100~199)
    CORE_MODEL_LOAD_FAILED    = 100,
    CORE_INFERENCE_FAILED     = 101,
    CORE_BACKEND_UNAVAILABLE  = 102,
    CORE_COMPILE_FAILED       = 103,
    CORE_QUANTIZE_FAILED      = 104,

    // HAL (300~399)
    HAL_JOINT_LIMIT_EXCEEDED   = 300,
    HAL_MOTOR_OVERTEMP         = 301,
    HAL_SENSOR_FAILURE         = 302,
    HAL_COMMUNICATION_ERROR    = 303,
    HAL_POWER_LOW              = 304,

    // Safety (500~599)
    SAFETY_COLLISION_DETECTED  = 500,
    SAFETY_EMERGENCY_STOP      = 501,
    SAFETY_WATCHDOG_TIMEOUT    = 502,
    SAFETY_JOINT_TORQUE_LIMIT  = 503,
};
```
