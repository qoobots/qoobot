# QooBot 总体 API 设计文档

> 最后更新：2026-06-29
>
> 本文档定义 QooBot 项目的总体 API 设计规范，涵盖 API 设计原则、协议选择、版本策略、鉴权模式、错误处理与接口规范。

---

## 🎯 API 设计原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **接口标准化** | 跨项目通信统一使用 gRPC + Protobuf |
| 2 | **版本化管理** | 所有 API 带语义化版本，向后兼容 |
| 3 | **安全内建** | JWT/API Key/设备证书，零信任假设 |
| 4 | **文档自动生成** | Protobuf → 文档，OpenAPI → Swagger |
| 5 | **幂等性** | 写操作支持幂等键，防止重复提交 |
| 6 | **分页与过滤** | 列表接口统一分页/排序/过滤参数 |
| 7 | **错误标准化** | 统一错误码体系，多语言错误信息 |
| 8 | **可观测性** | 所有 API 内置 tracing/metrics/logging |

---

## 📡 协议分层

### 协议矩阵

| 场景 | 协议 | 序列化 | 说明 |
|------|------|--------|------|
| **云端微服务间** | gRPC | Protobuf 3 | 高性能、强类型、流式支持 |
| **端→云通信** | gRPC + MQTT | Protobuf 3 | 请求-响应 + 发布-订阅 |
| **Web 前端→云端** | gRPC-Web + REST | Protobuf 3 / JSON | 浏览器兼容 |
| **机器人内部** | ROS 2 DDS | CDR | 实时控制总线 |
| **实时数据推送** | WebSocket | JSON / Protobuf | 状态面板、遥控视频信令 |
| **第三方集成** | REST + OAuth 2.0 | JSON (OpenAPI 3.0) | 外部系统对接 |
| **移动端** | REST + WebSocket | JSON | Mobile App / Mini Program |

### API 网关路由规则

```
所有 API 请求
    │
    ▼
┌─────────────────────────────────────────────┐
│          Spring Cloud Gateway (:8080)         │
│                                               │
│  路由规则:                                     │
│  /api/v1/auth/**        → auth-service:8101   │
│  /api/v1/users/**       → user-service:8102   │
│  /api/v1/devices/**     → device-service:8103  │
│  /api/v1/oauth/**       → oauth-service:8104   │
│  /api/v1/apikeys/**     → apikey-service:8105  │
│  /api/v1/inference/**   → inference-service    │
│  /api/v1/ota/**         → ota-service          │
│  /api/v1/store/**       → store-service        │
│  /api/v1/compliance/**  → compliance-service    │
│  /api/v1/chain/**       → chain-service         │
│  /api/v1/gear/**        → gear-service          │
│  /api/v1/community/**   → community-service     │
│  /grpc/**               → gRPC 服务 (双向流)    │
│  /ws/**                 → WebSocket 升级        │
│                                               │
└─────────────────────────────────────────────┘
```

---

## 🔐 API 鉴权模式

### 鉴权类型

| 鉴权方式 | 适用场景 | 示例 |
|----------|----------|------|
| **JWT (Ed25519)** | 用户 Web/Mobile 登录 | `Authorization: Bearer <jwt_token>` |
| **OAuth 2.0 (Authorization Code + PKCE)** | 第三方应用接入 | OIDC 标准流程 |
| **API Key** | 开发者 API 调用 | `X-API-Key: qk_xxxxxxxx` |
| **mTLS (X.509)** | 机器人→云端通信 | 双向 TLS 证书认证 |
| **设备 Token** | 机器人端轻量认证 | `X-Device-Token: <token>` |

### JWT Token 结构

```json
{
  "header": {
    "alg": "EdDSA",
    "typ": "JWT"
  },
  "payload": {
    "iss": "qooauth.qoobot.dev",
    "sub": "user_abc123",
    "aud": "qoocloud",
    "exp": 1719000000,
    "iat": 1718913600,
    "jti": "unique_token_id",
    "scope": "read:devices write:skills",
    "qid": "qoo_id_xyz789"
  }
}
```

### API Key 格式

```
qk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
│   │    └── 32 字节随机字符串 (Base62)
│   └── 环境: live / test
└── 前缀: qk (QooBot API Key)
```

---

## 🔄 版本策略

### URL 路径版本

```
/api/v1/users                          ← 主版本
/api/v2/users                          ← 大版本升级
/api/v1/users?version=2026-01          ← 日期版本 (可选)
```

### Protobuf 版本管理

```protobuf
// 向后兼容规则:
// 1. 不修改已有字段编号
// 2. 新增字段使用新的字段编号
// 3. 废弃字段标记 [deprecated = true]
// 4. 使用 reserved 保留不再使用的字段编号

message User {
  string user_id = 1;
  string email = 2;
  string display_name = 3;
  // string old_field = 4 [deprecated = true];
  reserved 4;
  reserved "old_field";
  string avatar_url = 5;        // v1.1 新增
  UserPreferences preferences = 6;  // v1.2 新增
}
```

### 兼容性承诺

| 版本变化 | 兼容性保证 |
|----------|-----------|
| **新增字段** | 完全向后兼容 |
| **新增 API** | 完全向后兼容 |
| **废弃 API** | 至少 6 个月过渡期，响应头 `Deprecation: true` |
| **删除 API** | 仅在大版本升级时，提前公告 |
| **字段语义变更** | 视为不兼容变更，需要新版本 |

---

## ⚠️ 错误处理

### 统一错误响应格式

#### REST API (JSON)

```json
{
  "error": {
    "code": "AUTH_INVALID_TOKEN",
    "message": "The provided authentication token is invalid or expired.",
    "message_zh": "认证令牌无效或已过期。",
    "request_id": "req_abc123def456",
    "details": [
      {
        "field": "token",
        "reason": "expired",
        "expired_at": "2026-06-28T12:00:00Z"
      }
    ]
  }
}
```

#### gRPC API (Status)

```protobuf
// 使用标准 gRPC Status + 自定义 details
message ErrorDetail {
  string code = 1;          // 业务错误码
  string message = 2;       // 英文错误信息
  string message_zh = 3;    // 中文错误信息
  string request_id = 4;    // 请求追踪 ID
  repeated FieldError field_errors = 5;
}

message FieldError {
  string field = 1;
  string reason = 2;
}
```

### 错误码体系

| HTTP 状态码 | gRPC 状态码 | 场景 |
|:--:|------|------|
| 400 | `INVALID_ARGUMENT` | 请求参数错误 |
| 401 | `UNAUTHENTICATED` | 未认证或 Token 过期 |
| 403 | `PERMISSION_DENIED` | 权限不足 |
| 404 | `NOT_FOUND` | 资源不存在 |
| 409 | `ALREADY_EXISTS` | 资源冲突 |
| 422 | `FAILED_PRECONDITION` | 业务逻辑错误 |
| 429 | `RESOURCE_EXHAUSTED` | 速率限制 |
| 500 | `INTERNAL` | 服务内部错误 |
| 503 | `UNAVAILABLE` | 服务不可用 |

### 业务错误码段

| 错误码段 | 服务 | 示例 |
|:--:|------|------|
| `AUTH_*` | qooauth 认证服务 | `AUTH_INVALID_TOKEN` |
| `USER_*` | qooauth 用户服务 | `USER_EMAIL_EXISTS` |
| `DEVICE_*` | qoocloud 设备管理 | `DEVICE_OFFLINE` |
| `OTA_*` | qoocloud OTA 服务 | `OTA_UPDATE_FAILED` |
| `INFER_*` | qoocloud 推理服务 | `INFER_MODEL_NOT_FOUND` |
| `STORE_*` | qoostore 技能市场 | `STORE_SKILL_NOT_FOUND` |
| `SKILL_*` | 技能运行时 | `SKILL_CRASHED` |
| `COMPLY_*` | qoocompliance | `COMPLY_CERT_EXPIRED` |
| `CHAIN_*` | qoochain | `CHAIN_BOM_INVALID` |
| `GEAR_*` | qoogear | `GEAR_NOT_CERTIFIED` |

---

## 📋 REST API 通用规范

### 请求规范

```
GET    /api/v1/resources              # 列表查询
GET    /api/v1/resources/{id}         # 单条查询
POST   /api/v1/resources              # 创建
PUT    /api/v1/resources/{id}         # 全量更新
PATCH  /api/v1/resources/{id}         # 部分更新
DELETE /api/v1/resources/{id}         # 删除

# 子资源
GET    /api/v1/resources/{id}/sub-resources
POST   /api/v1/resources/{id}/actions/{action}  # 操作
```

### 分页规范

```
GET /api/v1/users?page=1&page_size=20&sort=-created_at&filter=status:active
```

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_count": 156,
    "total_pages": 8,
    "has_next": true,
    "has_previous": false
  }
}
```

### 通用请求头

| 头 | 值 | 说明 |
|----|-----|------|
| `Authorization` | `Bearer <token>` | JWT 认证 |
| `X-API-Key` | `qk_live_...` | API Key 认证 |
| `X-Request-ID` | UUID v4 | 请求追踪 |
| `X-Idempotency-Key` | UUID v4 | 幂等键 |
| `Accept` | `application/json` | 响应格式 |
| `Accept-Language` | `zh-CN` / `en-US` | 多语言 |
| `User-Agent` | `QooBot-SDK/1.0` | 客户端标识 |

### 通用响应头

| 头 | 值 | 说明 |
|----|-----|------|
| `X-Request-ID` | UUID v4 | 请求追踪回显 |
| `X-RateLimit-Limit` | `100` | 速率限制上限 |
| `X-RateLimit-Remaining` | `87` | 剩余请求数 |
| `X-RateLimit-Reset` | `1719000000` | 重置时间戳 |
| `Deprecation` | `true` | API 已废弃 |
| `Sunset` | `Tue, 31 Dec 2026 23:59:59 GMT` | 废弃 API 下线时间 |

---

## 📡 gRPC 服务定义规范

### 项目级 Proto 组织

```
api/
├── proto/
│   ├── common/
│   │   ├── types.proto           # 通用类型 (UUID, Timestamp, Pagination)
│   │   ├── error.proto           # 错误定义
│   │   └── health.proto          # 健康检查
│   ├── auth/
│   │   ├── auth_service.proto    # 认证服务
│   │   ├── user_service.proto    # 用户服务
│   │   ├── device_service.proto  # 设备服务
│   │   └── oauth_service.proto   # OAuth 服务
│   ├── cloud/
│   │   ├── inference.proto       # 推理服务
│   │   ├── ota.proto             # OTA 服务
│   │   └── orchestra.proto       # 编排服务
│   ├── skill/
│   │   └── skill_service.proto   # 技能服务
│   ├── robot/
│   │   ├── perception.proto      # 感知 API
│   │   ├── navigation.proto      # 导航 API
│   │   └── control.proto         # 控制 API
│   └── teleop/
│       └── remote_control.proto  # 远程遥控
└── openapi/
    └── public_api.yaml           # 公开 REST API 规范
```

### Protobuf 编码规范

```protobuf
syntax = "proto3";
package qoobot.auth.v1;

option java_package = "com.qoobot.proto.auth.v1";
option java_multiple_files = true;
option go_package = "github.com/qoobots/qoobot/api/proto/auth/v1";

import "common/types.proto";
import "google/api/annotations.proto";

// 服务定义: 动词 + 名词
service AuthService {
  // 方法: PascalCase
  rpc Register(RegisterRequest) returns (RegisterResponse);
  rpc Login(LoginRequest) returns (LoginResponse);
  rpc RefreshToken(RefreshTokenRequest) returns (RefreshTokenResponse);
  rpc Logout(LogoutRequest) returns (LogoutResponse);
}

// 消息: PascalCase
message RegisterRequest {
  string email = 1;
  string password = 2;
  string display_name = 3;
  // 可选字段使用 optional 或 wrapper types
  optional string invite_code = 4;
}

message RegisterResponse {
  string user_id = 1;
  string qoo_id = 2;
  AuthToken token = 3;
}
```

---

## 🚦 速率限制与流量控制

### 速率限制策略

| 层级 | 限制维度 | 默认值 | 说明 |
|------|----------|:--:|------|
| **全局限流** | 网关整体 QPS | 10,000/s | 保护后端服务 |
| **用户限流** | 用户 ID | 100/min | 防止单用户滥用 |
| **设备限流** | 设备 ID | 10/s | 端侧上报频率 |
| **API Key 限流** | Key ID | 1,000/min | 开发者配额 |
| **IP 限流** | IP 地址 | 60/min | 防 DDoS |
| **接口限流** | API + 用户 | 差异化 | 推理 10/min, 查询 100/min |

### 速率限制响应

```
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719000060
Retry-After: 30

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please retry after 30 seconds.",
    "retry_after_ms": 30000
  }
}
```

---

## 🔌 WebSocket API

### 连接规范

```javascript
// 建立连接
const ws = new WebSocket("wss://api.qoobot.dev/ws/v1/device?token=<jwt>");

// 消息格式
{
  "type": "telemetry",          // 消息类型
  "id": "msg_abc123",           // 消息 ID (用于追踪)
  "timestamp": "2026-06-29T08:30:00Z",
  "payload": {
    "robot_id": "robot_xyz789",
    "metrics": {
      "cpu_percent": 45.2,
      "memory_mb": 8192,
      "battery_percent": 85
    }
  }
}
```

### 消息类型

| Type | 方向 | 说明 |
|------|:--:|------|
| `telemetry` | 端 → 云 | 遥测数据上报 |
| `state_change` | 端 → 云 | 状态变更通知 |
| `command` | 云 → 端 | 控制指令下发 |
| `notification` | 云 → 端 | 推送通知 |
| `ping` / `pong` | 双向 | 心跳保活 |
| `error` | 双向 | 错误通知 |

---

## 📊 API 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **API 响应时间 (P50)** | < 50ms | 简单查询 |
| **API 响应时间 (P95)** | < 200ms | 含数据库操作 |
| **API 响应时间 (P99)** | < 500ms | 复杂查询/聚合 |
| **gRPC 响应时间 (P99)** | < 100ms | 微服务间调用 |
| **WebSocket 消息延迟** | < 50ms | 端到端 |
| **API 可用性** | > 99.99% | 年度 |
| **API 错误率** | < 0.1% | 5xx + 4xx (不含 429) |

---

## 🧪 API 测试矩阵

| 测试类型 | 覆盖目标 | 工具 |
|----------|----------|------|
| **单元测试** | 每个 API 端点 | JUnit 5 (Java) / pytest (Python) |
| **契约测试** | Protobuf/OpenAPI 兼容性 | Pact / Spring Cloud Contract |
| **集成测试** | 端到端 API 调用链 | Testcontainers + Docker Compose |
| **负载测试** | 并发/吞吐量 | k6 / JMeter |
| **安全测试** | 注入/OAuth 漏洞/权限绕过 | ZAP / 手动渗透 |
| **模糊测试** | 异常输入处理 | RESTler / custom fuzzer |

---

## 📚 参考文档

| 文档 | 路径 |
|------|------|
| 技术架构设计 | `02总体技术架构设计.md` |
| 应用架构设计 | `03总体应用架构设计.md` |
| 数据架构设计 | `05总体数据架构设计.md` |
| 安全架构设计 | `07总体安全架构设计.md` |

---

> 所有子项目的 API 设计必须遵循本文档定义的规范。各子项目在本文档基础上制定各自的 API 详细设计文档。
