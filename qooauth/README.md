# qooauth — 人形机器人账号与安全框架

> 机器人的"Apple ID + Face ID + Secure Enclave"：
> 统一身份认证、设备安全、权限管理、隐私保护。

## 定位

qooauth 是 QooBot 生态的安全基础设施，管理机器人身份、用户认证、
操作权限和隐私合规，确保机器人系统的端到端安全。

## 模块

| 模块 | 说明 | 状态 |
|------|------|------|
| `identity/` | 统一身份系统（机器人/用户/开发者） | 📋 规划中 |
| `device_auth/` | 设备认证与绑定（证书、密钥管理） | 📋 规划中 |
| `permissions/` | 操作权限分级（管理员/操作员/观察者） | 📋 规划中 |
| `privacy/` | 隐私框架（摄像头/麦克风/位置数据管控） | 📋 规划中 |
| `secure_enclave/` | 安全存储（密钥、模型参数、敏感配置） | 📋 规划中 |
| `audit/` | 操作审计日志（谁在何时做了什么事） | 📋 规划中 |
| `compliance/` | 合规检查（GDPR、机器人安全法规） | 📋 规划中 |
| `tls/` | 通信加密（gRPC TLS、MQTT TLS） | 📋 规划中 |
| `attestation/` | 设备远程证明（防篡改） | 📋 规划中 |

## 权限分级

| 角色 | 权限范围 | 示例 |
|------|----------|------|
| 管理员 (Admin) | 完全控制 | 工厂管理员、机器人所有者 |
| 操作员 (Operator) | 运行操作 | 产线工人、手术医生 |
| 开发者 (Developer) | 调试/部署 | 算法工程师、集成工程师 |
| 观察者 (Observer) | 只读监控 | 安全巡检员、审计员 |
| 访客 (Guest) | 受限交互 | 展览观众、客户演示 |

## 安全威胁模型

| 威胁 | 防护措施 |
|------|----------|
| 未授权控制 | 设备证书 + 双向 TLS + 操作权限校验 |
| 数据泄露 | 端到端加密 + 隐私框架 + 数据最小化 |
| 固件篡改 | 安全启动 + 远程证明 + 签名验证 |
| 模型窃取 | 安全存储 + 模型加密 + 访问控制 |
| 中间人攻击 | 双向 TLS + 证书固定 |

## iPhone 类比

| Apple 技术 | qooauth 对应 |
|------------|-------------|
| Apple ID | identity（统一账号） |
| Face ID / Touch ID | device_auth（生物识别绑定） |
| Secure Enclave | secure_enclave |
| 隐私标签 | privacy |
| App Tracking Transparency | compliance |

## 与 qoobrain 的关系

```
qooauth ──认证/授权──→ qoobrain (大脑OS)
        ──加密通信──→ qoocloud (云端)
        ──权限管控──→ qoobody (硬件)
```

## 许可

Apache-2.0
