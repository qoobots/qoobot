# qoocloud — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft | 子项目：qoocloud（云端服务）
> API 类型：REST · gRPC · MQTT · WebSocket

---

## 1. API 设计原则

1. **REST 用于管理面**：设备管理、OTA 配置、用户操作
2. **gRPC 用于数据面**：高频推理请求、流式数据传输
3. **MQTT 用于设备面**：设备遥测、命令下发、状态同步
4. **WebSocket 用于实时面**：Web 控制台实时监控

---

## 2. REST API

### 2.1 设备管理

| Method | Endpoint | 描述 |
|:-------|---------|------|
| POST | `/api/v1/devices/register` | 设备注册 |
| GET | `/api/v1/devices/{deviceId}` | 获取设备详情 |
| PUT | `/api/v1/devices/{deviceId}` | 更新设备配置 |
| DELETE | `/api/v1/devices/{deviceId}` | 注销设备 |
| GET | `/api/v1/devices` | 设备列表（分页/筛选） |
| POST | `/api/v1/devices/{deviceId}/shadow` | 更新期望状态 |
| GET | `/api/v1/devices/{deviceId}/shadow` | 获取设备影子 |
| POST | `/api/v1/devices/{deviceId}/commands` | 下发命令 |
| GET | `/api/v1/devices/{deviceId}/health` | 获取健康状态 |
| GET | `/api/v1/devices/{deviceId}/telemetry` | 查询遥测数据 |

### 2.2 OTA 管理

| Method | Endpoint | 描述 |
|:-------|---------|------|
| POST | `/api/v1/ota/packages` | 上传升级包 |
| GET | `/api/v1/ota/packages/{pkgId}` | 获取升级包详情 |
| POST | `/api/v1/ota/campaigns` | 创建升级任务 |
| GET | `/api/v1/ota/campaigns/{campaignId}` | 获取任务状态 |
| PUT | `/api/v1/ota/campaigns/{campaignId}` | 更新灰度策略 |
| POST | `/api/v1/ota/campaigns/{campaignId}/rollback` | 回滚 |
| GET | `/api/v1/ota/devices/{deviceId}/updates` | 设备升级历史 |

### 2.3 推理管理

| Method | Endpoint | 描述 |
|:-------|---------|------|
| POST | `/api/v1/inference/models` | 注册模型 |
| GET | `/api/v1/inference/models` | 模型列表 |
| PUT | `/api/v1/inference/models/{modelId}` | 更新模型版本 |
| DELETE | `/api/v1/inference/models/{modelId}` | 删除模型 |
| POST | `/api/v1/inference/models/{modelId}/switch` | 热切换版本 |

### 2.4 通用规范

```yaml
请求头:
  Authorization: Bearer <jwt_token>
  Content-Type: application/json
  X-Request-ID: <uuid>          # 请求追踪
  X-Device-ID: <device_id>      # 设备标识（设备端请求）

响应格式:
  {
    "code": 0,
    "message": "success",
    "data": { ... },
    "request_id": "uuid"
  }

分页:
  GET /devices?page=1&size=20&sort=created_at:desc
  Response: { "data": [...], "total": 150, "page": 1, "size": 20 }

错误响应:
  {
    "code": 10001,
    "message": "Device not found",
    "request_id": "uuid"
  }
```

---

## 3. gRPC API

### 3.1 Inference Service

```protobuf
service InferenceService {
  // 文本推理（支持流式）
  rpc Chat(ChatRequest) returns (stream ChatResponse);
  
  // 视觉推理
  rpc VisualInference(VisualRequest) returns (VisualResponse);
  
  // 嵌入向量
  rpc Embed(EmbedRequest) returns (EmbedResponse);
  
  // 批量推理
  rpc BatchInfer(BatchRequest) returns (BatchResponse);
  
  // 模型信息
  rpc GetModelInfo(ModelInfoRequest) returns (ModelInfo);
}

message ChatRequest {
  string model_id = 1;
  repeated Message messages = 2;
  float temperature = 3;
  int32 max_tokens = 4;
  bool stream = 5;
}

message ChatResponse {
  string content = 1;
  string finish_reason = 2; // stop / length / error
  Usage usage = 3;
}
```

### 3.2 Device Data Service

```protobuf
service DeviceDataService {
  // 遥测数据上传
  rpc IngestTelemetry(stream TelemetryBatch) returns (IngestResult);
  
  // 经验数据上传
  rpc IngestExperience(stream ExperienceRecord) returns (IngestResult);
  
  // 联邦学习参数同步
  rpc FederatedSync(stream ModelGradient) returns (stream AggregatedModel);
}
```

---

## 4. MQTT Topics

### 4.1 设备 → 云端

| Topic | QoS | 描述 |
|:------|:---:|------|
| `qoo/{deviceId}/telemetry` | 1 | 遥测数据 |
| `qoo/{deviceId}/event` | 1 | 设备事件（唤醒/故障/告警） |
| `qoo/{deviceId}/state/reported` | 1 | 上报状态 |
| `qoo/{deviceId}/shadow/update` | 1 | 设备影子更新 |
| `qoo/{deviceId}/heartbeat` | 0 | 心跳 |

### 4.2 云端 → 设备

| Topic | QoS | 描述 |
|:------|:---:|------|
| `qoo/{deviceId}/command` | 1 | 命令下发 |
| `qoo/{deviceId}/state/desired` | 1 | 期望状态 |
| `qoo/{deviceId}/config` | 1 | 配置下发 |
| `qoo/{deviceId}/ota/notify` | 1 | OTA 升级通知 |

---

## 5. 错误码

| 错误码 | HTTP | 描述 |
|:-------|:----:|------|
| `CLOUD_OK` (0) | 200 | 成功 |
| `CLOUD_ERR_BAD_REQUEST` (40001) | 400 | 请求参数错误 |
| `CLOUD_ERR_UNAUTHORIZED` (40101) | 401 | 未认证 |
| `CLOUD_ERR_FORBIDDEN` (40301) | 403 | 无权限 |
| `CLOUD_ERR_NOT_FOUND` (40401) | 404 | 资源不存在 |
| `CLOUD_ERR_RATE_LIMITED` (42901) | 429 | 请求限流 |
| `CLOUD_ERR_DEVICE_OFFLINE` (50001) | 503 | 设备离线 |
| `CLOUD_ERR_INFERENCE_OVERLOAD` (50002) | 503 | 推理过载 |
| `CLOUD_ERR_OTA_FAILED` (50003) | 500 | OTA 执行失败 |
| `CLOUD_ERR_GPU_UNAVAILABLE` (50004) | 503 | GPU 资源不可用 |
| `CLOUD_ERR_MODEL_NOT_FOUND` (50005) | 404 | 模型未找到 |
| `CLOUD_ERR_TENANT_LIMIT` (50006) | 429 | 租户配额超限 |

---

## 6. 版本策略

- REST API URL 版本化：`/api/v1/`, `/api/v2/`
- gRPC 使用 Protobuf 向后兼容（新增字段，不删除/修改已有字段）
- MQTT Topic 版本号内嵌：`qoo/v1/{deviceId}/...`
- 旧版本 API 至少保持 6 个月兼容期
