# Protobuf 服务定义

Brain OS 使用 gRPC + Protobuf 作为服务间通信协议。以下为 6 个核心 gRPC 服务的完整接口定义。

---

## 服务总览

| 服务 | 文件 | RPC 数量 | 描述 |
|------|------|----------|------|
| **Cognition** | `cognition/service.proto` | 4 | 意图解析、任务分解、行为树生成 |
| **Decision** | `decision/service.proto` | 3 | 轨迹生成、选择、计划管理 |
| **Perception** | `perception/service.proto` | 3 | 场景图、定位、目标查询 |
| **Control** | `control/service.proto` | 3 | 关节控制、轨迹执行 |
| **Safety** | `safety/service.proto` | 3 | 安全状态、急停、警报管理 |
| **Knowledge** | `knowledge/service.proto` | 5 | 技能库、经验存储、知识检索 |

---

## 通用类型 (`common/types.proto`)

```protobuf
message Status {
    StatusCode code = 1;
    string message = 2;
}

enum StatusCode {
    OK = 0;
    ERROR = 1;
    PENDING = 2;
    RUNNING = 3;
}

message Header {
    uint32 seq = 1;
    google.protobuf.Timestamp stamp = 2;
    string frame_id = 3;
}

message Vector3 {
    double x = 1;
    double y = 2;
    double z = 3;
}

message Quaternion {
    double x = 1;
    double y = 2;
    double z = 3;
    double w = 4;
}

message Pose {
    Vector3 position = 1;
    Quaternion orientation = 2;
}
```

---

## Cognition Service

### 类型定义 (`cognition/types.proto`)

```protobuf
enum IntentType {
    INTENT_UNKNOWN = 0;
    INTENT_PICK = 1;
    INTENT_PLACE = 2;
    INTENT_NAVIGATE = 3;
    INTENT_INSPECT = 4;
    INTENT_QUERY = 5;
    INTENT_STOP = 6;
    INTENT_SEQUENCE = 7;
    INTENT_GREET = 8;
}

message Intent {
    IntentType type = 1;
    string raw_text = 2;
    float confidence = 3;
    google.protobuf.Struct params = 4;
    string language = 5;
}

enum TaskStatus {
    TASK_PENDING = 0;
    TASK_RUNNING = 1;
    TASK_SUCCEEDED = 2;
    TASK_FAILED = 3;
    TASK_CANCELLED = 4;
    TASK_WAITING_HUMAN = 5;
}

message SubTask {
    string task_id = 1;
    string skill_name = 2;
    google.protobuf.Struct parameters = 3;
    repeated string depends_on = 4;
    TaskStatus status = 5;
    float priority = 6;
}

message BehaviorTree {
    string tree_id = 1;
    string xml_str = 2;
    string description = 3;
}
```

### RPC 方法

```protobuf
service CognitionService {
    rpc ParseIntent(ParseIntentRequest) returns (ParseIntentResponse);
    rpc DecomposeTask(DecomposeTaskRequest) returns (DecomposeTaskResponse);
    rpc GenerateBehaviorTree(GenerateBTRequest) returns (GenerateBTResponse);
    rpc Clarify(ClarifyRequest) returns (ClarifyResponse);
}
```

**ParseIntent**：解析自然语言指令为结构化意图。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `robot_id` | string | 机器人 ID |
| `utterance` | string | 用户指令文本 |
| `language` | string | 语言代码（zh-CN / en） |
| `context` | ConversationTurn | 对话上下文 |

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| `status` | Status | 执行状态 |
| `intent` | Intent | 解析后的意图 |
| `candidates` | repeated Intent | 候选意图 |

**DecomposeTask**：将意图分解为子任务 DAG。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `robot_id` | string | 机器人 ID |
| `intent` | Intent | 已解析的意图 |
| `scene_graph` | repeated DetectedObject | 场景上下文 |

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| `status` | Status | 执行状态 |
| `plan_id` | string | 计划 ID |
| `subtasks` | repeated SubTask | 子任务列表 |
| `rationale` | string | 分解理由 |

**GenerateBehaviorTree**：生成行为树 XML。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `robot_id` | string | 机器人 ID |
| `plan_id` | string | 计划 ID |
| `subtasks` | repeated SubTask | 子任务列表 |

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| `status` | Status | 执行状态 |
| `tree` | BehaviorTree | 生成的行为树 |

---

## Decision Service

### RPC 方法

```protobuf
service DecisionService {
    rpc GenerateTrajectories(GenerateTrajectoriesRequest)
        returns (GenerateTrajectoriesResponse);
    rpc SelectTrajectory(SelectTrajectoryRequest)
        returns (SelectTrajectoryResponse);
    rpc CancelPlan(CancelPlanRequest) returns (CancelPlanResponse);
}
```

**GenerateTrajectories**：生成多条候选轨迹。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `robot_id` | string | 机器人 ID |
| `plan_id` | string | 计划 ID |
| `target_pose` | Pose | 目标位姿 |
| `num_candidates` | int32 | 候选轨迹数量 |

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| `status` | Status | 执行状态 |
| `trajectories` | repeated Trajectory | 候选轨迹 |

**SelectTrajectory**：选择并确认轨迹。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `robot_id` | string | 机器人 ID |
| `plan_id` | string | 计划 ID |
| `trajectory_id` | string | 选择的轨迹 ID |

**CancelPlan**：取消执行计划。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `robot_id` | string | 机器人 ID |
| `plan_id` | string | 计划 ID |
| `reason` | string | 取消原因 |

---

## Perception Service

```protobuf
service PerceptionService {
    rpc GetSceneGraph(GetSceneGraphRequest) returns (GetSceneGraphResponse);
    rpc GetLocalization(GetLocalizationRequest) returns (GetLocalizationResponse);
    rpc StreamSceneGraph(StreamSceneGraphRequest)
        returns (stream StreamSceneGraphResponse);
}
```

---

## Control Service

```protobuf
service ControlService {
    rpc SendJointCommand(SendJointCommandRequest)
        returns (SendJointCommandResponse);
    rpc ControlGripper(ControlGripperRequest)
        returns (ControlGripperResponse);
    rpc ExecuteTrajectory(ExecuteTrajectoryRequest)
        returns (stream ExecuteTrajectoryResponse);
}
```

---

## Safety Service

```protobuf
service SafetyService {
    rpc GetSafetyStatus(GetSafetyStatusRequest)
        returns (GetSafetyStatusResponse);
    rpc EmergencyStop(EmergencyStopRequest)
        returns (EmergencyStopResponse);
    rpc AcknowledgeAlert(AcknowledgeAlertRequest)
        returns (AcknowledgeAlertResponse);
}
```

---

## Knowledge Service

```protobuf
service KnowledgeService {
    rpc ListSkills(ListSkillsRequest) returns (ListSkillsResponse);
    rpc RegisterSkill(RegisterSkillRequest) returns (RegisterSkillResponse);
    rpc SearchEpisodes(SearchEpisodesRequest) returns (SearchEpisodesResponse);
    rpc StoreEpisode(StoreEpisodeRequest) returns (StoreEpisodeResponse);
    rpc SearchKnowledge(SearchKnowledgeRequest) returns (SearchKnowledgeResponse);
}
```

**ListSkills**：查询已注册的技能。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `tag_filter` | string | 标签过滤 |

| 响应字段 | 类型 | 说明 |
|----------|------|------|
| `status` | Status | 执行状态 |
| `skills` | repeated Skill | 技能列表 |

**SearchEpisodes**：搜索历史经验。

| 请求字段 | 类型 | 说明 |
|----------|------|------|
| `robot_id` | string | 机器人 ID |
| `query_text` | string | 查询文本 |
| `query_embed` | repeated float | 查询向量 |
| `top_k` | int32 | 返回数 |
| `min_score` | float | 最低相似度 |
| `success_only` | bool | 仅成功案例 |

---

## 通信协议详情

### gRPC 配置

```python
channel = grpc.insecure_channel("localhost:50052")
# 生产环境推荐使用 TLS
# channel = grpc.secure_channel("robot-1:50052", credentials)
```

| 参数 | 值 |
|------|-----|
| 默认端口 | 50052 |
| 最大消息 | 16 MB |
| Keepalive | 30 秒 |
| Keepalive 超时 | 10 秒 |
| 服务发现 | 直连（支持 DNS/Consul 扩展） |

### WebSocket 协议

用于实时推送（状态更新、安全警报、场景变化）：

```json
{
    "action": "subscribe",
    "events": ["plan_status", "safety_alert", "scene_update"]
}
```

| 端口 | 用途 |
|------|------|
| 8765 | WebSocket 事件推送 |
| 3000 | brain_viz Dashboard HTTP |
