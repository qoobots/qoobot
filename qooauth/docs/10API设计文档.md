# qooauth — API 设计文档

> 版本：v0.1 | 最后更新：2026-06-29 | 状态：Draft
>
> **子项目**：qooauth（账号与安全）| **对标**：OIDC / OAuth 2.0 标准 API

---

## 1. API 设计原则

| 原则 | 说明 |
|:-----|:-----|
| **标准优先** | 遵循 OAuth 2.0 (RFC 6749)、OIDC (OpenID Connect 1.0)、RFC 7519 (JWT) |
| **版本管理** | URL 路径版本 `/api/v1/`，兼容 2 个大版本 |
| **统一响应** | `{ "code": 0, "message": "ok", "data": {...} }` |
| **安全默认** | 所有 API 默认 HTTPS，敏感端点需认证 |
| **限流保护** | 所有端点 Token Bucket 限流，返回 `429 Too Many Requests` |
| **可观测性** | 请求 ID (`X-Request-Id`)、链路追踪 |

---

## 2. 协议分层

```
┌─────────────────────────────────────────────────────────────┐
│                    对外 API (REST/JSON)                      │
│  协议：HTTPS / TLS 1.3                                     │
│  格式：JSON (application/json)                              │
│  鉴权：Bearer Token (JWT) / OAuth 2.0 / API Key            │
│  文档：OpenAPI 3.0 (Swagger)                                │
├─────────────────────────────────────────────────────────────┤
│                    对内 API (gRPC/Protobuf)                  │
│  协议：HTTP/2 + TLS 1.3 (mTLS)                              │
│  格式：Protocol Buffers v3                                  │
│  鉴权：mTLS + JWT                                           │
│  文档：protobuf 注释                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. REST API 端点

### 3.1 认证相关 `/api/v1/auth`

| 方法 | 路径 | 描述 | 鉴权 |
|:-----|:-----|:-----|:-----|
| POST | `/auth/register` | 注册 QooBot ID | 无 |
| POST | `/auth/login` | 用户名密码登录 | 无 |
| POST | `/auth/logout` | 登出，吊销 Refresh Token | Bearer |
| POST | `/auth/refresh` | 刷新 Access Token | Refresh Token |
| POST | `/auth/2fa/enroll` | 注册 TOTP 双因素 | Bearer |
| POST | `/auth/2fa/verify` | 验证 TOTP 码 | Bearer + TOTP |
| POST | `/auth/recovery/init` | 初始化账户恢复 | Bearer |
| POST | `/auth/recovery/verify` | 验证恢复密钥 | 无 |
| POST | `/auth/webauthn/register` | 注册 FIDO2 硬件密钥 | Bearer |
| POST | `/auth/webauthn/authenticate` | FIDO2 认证 | 无 |

### 3.2 用户相关 `/api/v1/users`

| 方法 | 路径 | 描述 | 鉴权 |
|:-----|:-----|:-----|:-----|
| GET | `/users/me` | 获取当前用户信息 | Bearer |
| PUT | `/users/me` | 更新个人资料 | Bearer |
| PUT | `/users/me/password` | 修改密码 | Bearer |
| DELETE | `/users/me` | 账户注销 | Bearer |
| GET | `/users/me/sessions` | 查看活跃会话 | Bearer |
| DELETE | `/users/me/sessions/{id}` | 踢出指定会话 | Bearer |
| GET | `/users/me/devices` | 查看绑定设备列表 | Bearer |
| GET | `/users/me/consents` | 查看隐私同意记录 | Bearer |
| PUT | `/users/me/consents/{id}` | 撤回隐私同意 | Bearer |

### 3.3 OAuth 2.0 `/oauth2`

| 方法 | 路径 | 描述 | 鉴权 |
|:-----|:-----|:-----|:-----|
| GET | `/oauth2/.well-known/openid-configuration` | OIDC Discovery | 无 |
| GET | `/oauth2/authorize` | 授权请求 | Session Cookie |
| POST | `/oauth2/token` | Token 端点 | Client Auth |
| POST | `/oauth2/revoke` | Token 吊销 | Client Auth |
| GET | `/oauth2/userinfo` | 用户信息端点 | Bearer |
| GET | `/oauth2/jwks.json` | JWK Set 公钥端点 | 无 |
| POST | `/oauth2/introspect` | Token 内省 | Client Auth |

### 3.4 设备相关 `/api/v1/devices`

| 方法 | 路径 | 描述 | 鉴权 |
|:-----|:-----|:-----|:-----|
| POST | `/devices/activate` | 设备激活 | Device Pre-Auth |
| POST | `/devices/{id}/bind` | 绑定设备到用户 | Bearer |
| DELETE | `/devices/{id}/unbind` | 解绑设备 | Bearer |
| POST | `/devices/{id}/lock` | 远程锁定 (激活锁) | Bearer |
| POST | `/devices/{id}/wipe` | 远程擦除 | Bearer |
| GET | `/devices/{id}/location` | 查询设备位置 | Bearer |
| POST | `/devices/{id}/guest` | 开启访客模式 | Bearer |
| DELETE | `/devices/{id}/guest` | 关闭访客模式 | Bearer |

### 3.5 开发者相关 `/api/v1/developer`

| 方法 | 路径 | 描述 | 鉴权 |
|:-----|:-----|:-----|:-----|
| POST | `/developer/apps` | 注册 OAuth 应用 | Bearer |
| GET | `/developer/apps` | 列出我的应用 | Bearer |
| PUT | `/developer/apps/{id}` | 更新应用配置 | Bearer |
| POST | `/developer/keys` | 生成 API Key | Bearer |
| GET | `/developer/keys` | 列出 API Keys | Bearer |
| DELETE | `/developer/keys/{id}` | 吊销 API Key | Bearer |
| POST | `/developer/certs` | 申请开发者证书 | Bearer |
| POST | `/developer/sign` | 技能签名 | Bearer |

---

## 4. 统一响应格式

### 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    // 业务数据
  },
  "requestId": "req_uuid_xxx"
}
```

### 错误响应

```json
{
  "code": 10001,
  "message": "用户名或密码错误",
  "details": {
    "field": "password",
    "reason": "invalid_credentials",
    "remaining_attempts": 3
  },
  "requestId": "req_uuid_xxx"
}
```

---

## 5. 错误码体系

| 错误码范围 | 类别 | 示例 |
|:-----------|:-----|:-----|
| 10000-10099 | 认证错误 | 10001 密码错误, 10002 账户锁定 |
| 10100-10199 | Token 错误 | 10100 Token 过期, 10101 Token 无效 |
| 10200-10299 | OAuth 错误 | 10200 无效 client_id, 10201 无效 redirect_uri |
| 10300-10399 | 用户错误 | 10300 用户不存在, 10301 邮箱已注册 |
| 10400-10499 | 设备错误 | 10400 设备未注册, 10401 证书过期 |
| 10500-10599 | 权限错误 | 10500 无权限, 10501 Scope 不足 |
| 10600-10699 | 限流错误 | 10600 全局限流, 10601 用户限流 |
| 10700-10799 | 开发者错误 | 10700 应用审核中, 10701 API Key 吊销 |
| 90000-90099 | 系统错误 | 90000 内部错误, 90001 服务不可用 |

---

## 6. gRPC 服务定义

```protobuf
// qooauth.proto
service AuthService {
  rpc ValidateToken(ValidateTokenRequest) returns (ValidateTokenResponse);
  rpc IntrospectToken(IntrospectRequest) returns (IntrospectResponse);
  rpc GetUserPublicInfo(GetUserRequest) returns (UserPublicInfo);
  rpc VerifyDeviceCertificate(VerifyCertRequest) returns (VerifyCertResponse);
}

service UserService {
  rpc GetUserById(GetUserRequest) returns (UserResponse);
  rpc BatchGetUsers(BatchGetUsersRequest) returns (BatchGetUsersResponse);
  rpc CheckPermission(CheckPermRequest) returns (CheckPermResponse);
}

service DeviceService {
  rpc RegisterDevice(RegisterDeviceRequest) returns (DeviceResponse);
  rpc IssueCertificate(IssueCertRequest) returns (CertificateResponse);
  rpc RevokeDevice(RevokeDeviceRequest) returns (google.protobuf.Empty);
  rpc GetDeviceStatus(GetDeviceStatusRequest) returns (DeviceStatusResponse);
}
```

---

## 7. 版本策略

| 策略 | 说明 |
|:-----|:-----|
| **URL 版本** | `/api/v1/`, `/api/v2/` |
| **兼容周期** | 旧版本至少维护 6 个月 |
| **弃用公告** | `Sunset` HTTP 头提前 90 天通知 |
| **变更日志** | CHANGELOG.md + OpenAPI diff |

---

## 8. 速率限制

| 端点类别 | 限制 (per user) | 限制 (per IP) |
|:---------|:----------------|:--------------|
| 登录 | 5/min | 30/min |
| 注册 | 3/min | 10/min |
| Token 刷新 | 30/min | 60/min |
| 通用 API | 1000/min | 2000/min |
| 设备激活 | 10/min | 50/min |

限流响应头：
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1719667800
Retry-After: 60
```
