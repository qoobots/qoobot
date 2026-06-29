# 07 API 设计文档

Brain OS API 设计——Python SDK、gRPC服务、ROS2接口规范。

---

## Python Skill SDK

```python
"""qoobrain Skill SDK"""

class Skill(ABC):
    """技能基类 - 所有第三方技能继承此类"""
    
    def __init__(self, manifest: SkillManifest):
        self.manifest = manifest
        self._context: SkillContext = None
    
    @abstractmethod
    async def on_start(self) -> None: ...
    
    @abstractmethod
    async def on_stop(self) -> None: ...
    
    @abstractmethod
    async def on_tick(self, dt: float) -> None: ...
    
    # 感知API
    async def detect_objects(self, class_filter: List[str] = None) -> List[Detection]: ...
    async def get_scene_graph(self) -> SceneGraph: ...
    async def get_robot_pose(self) -> Pose3D: ...
    async def get_room_map(self) -> OccupancyGrid: ...
    
    # 导航API
    async def navigate_to(self, target: Pose3D, speed: float = 0.5) -> bool: ...
    async def navigate_to_object(self, object_name: str) -> bool: ...
    async def follow_person(self, person_id: str, distance: float = 1.0) -> None: ...
    
    # 操作API
    async def grasp_object(self, object_name: str, grasp_type: str = "pinch") -> bool: ...
    async def place_object(self, target: Pose3D) -> bool: ...
    async def move_arm_to(self, pose: Pose3D, speed: float = 0.3) -> bool: ...
    
    # 语音API
    async def speak(self, text: str, emotion: str = "neutral") -> None: ...
    async def listen(self, timeout: float = 5.0) -> str: ...
    
    # 状态API
    async def get_battery_level(self) -> float: ...
    async def get_joint_states(self) -> Dict[str, JointState]: ...
    
    # 日志
    def log(self, level: str, message: str, **kwargs) -> None: ...


# 上下文管理
class SkillContext:
    skill_id: str
    session_id: str
    permissions: Set[str]
    resource_quota: ResourceQuota
    blackboard: Dict[str, Any]
```

---

## gRPC 服务定义

```protobuf
// qoobrain.proto

service PerceptionService {
    rpc Detect(DetectRequest) returns (DetectResponse);
    rpc GetSceneGraph(GetSceneGraphRequest) returns (SceneGraph);
    rpc GetRobotPose(google.protobuf.Empty) returns (Pose3D);
    rpc StreamSensors(SensorStreamRequest) returns (stream SensorFrame);
}

service CognitionService {
    rpc UnderstandCommand(UnderstandRequest) returns (TaskPlan);
    rpc DecomposeTask(DecomposeRequest) returns (TaskPlan);
    rpc QueryKnowledge(QueryRequest) returns (KnowledgeResponse);
}

service DecisionService {
    rpc GeneratePlan(TaskPlan) returns (BehaviorTree);
    rpc GenerateTrajectories(TrajectoryRequest) returns (TrajectorySet);
    rpc EvaluateTrajectory(Trajectory) returns (Evaluation);
    rpc HITLIntervention(HITLRequest) returns (HITLResponse);
}

service ControlService {
    rpc ExecuteTrajectory(Trajectory) returns (stream ExecutionStatus);
    rpc EmergencyStop(google.protobuf.Empty) returns (google.protobuf.Empty);
    rpc MoveJoint(MoveJointRequest) returns (MoveJointResponse);
    rpc SetControlMode(ControlModeRequest) returns (google.protobuf.Empty);
}

service HITLService {
    rpc RequestIntervention(HITLTrigger) returns (HITLOption);
    rpc SubmitSelection(Selection) returns (google.protobuf.Empty);
    rpc TakeManualControl(ManualControlRequest) returns (stream RobotState);
}
```

---

## ROS2 接口

### Topics (发布/订阅)

| Topic | 类型 | 发布者 | 频率 |
|:------|:-----|:-------|:-----|
| `/sensor/camera/{name}/image` | sensor_msgs/Image | 相机驱动 | 30Hz |
| `/sensor/lidar/points` | sensor_msgs/PointCloud2 | LiDAR驱动 | 20Hz |
| `/sensor/imu` | sensor_msgs/Imu | IMU驱动 | 200Hz |
| `/perception/scene_graph` | qoobot_msgs/SceneGraph | Perception | 10Hz |
| `/cognition/task_plan` | qoobot_msgs/TaskPlan | Cognition | 按需 |
| `/decision/trajectory` | qoobot_msgs/Trajectory | Decision | 50Hz |
| `/control/joint_command` | sensor_msgs/JointState | Control | 1000Hz |
| `/diagnostics` | diagnostic_msgs/DiagnosticArray | 各节点 | 1Hz |

### Services (请求/响应)

| Service | 类型 | 提供者 |
|:--------|:-----|:-------|
| `/navigation/plan_path` | nav_msgs/GetPlan | Navigation |
| `/manipulation/grasp` | qoobot_msgs/Grasp | Manipulation |
| `/speech/synthesize` | qoobot_msgs/Synthesize | Speech |
| `/emergency_stop` | std_srvs/Trigger | Safety |

### Actions (长时间任务)

| Action | 类型 | 提供者 |
|:-------|:-----|:-------|
| `/navigation/navigate_to_pose` | nav2_msgs/NavigateToPose | Navigation |
| `/manipulation/pick_and_place` | qoobot_msgs/PickAndPlace | Manipulation |
