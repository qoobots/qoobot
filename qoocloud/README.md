# qoocloud — 具身机器人云端服务

> 机器人的"iCloud"：云端推理、数据同步、远程协作、多机管理。

## 定位

qoocloud 是 QooBot 生态的云端基础设施，为运行 qoobrain 的机器人
提供云端推理、数据存储、远程管理、多机协作等能力。

## 模块

| 模块 | 说明 | 状态 |
|------|------|------|
| `inference/` | 云端模型推理服务（VLA 大模型、视觉模型） | 📋 规划中 |
| `sync/` | 数据同步（技能、知识库、模型参数） | 📋 规划中 |
| `fleet/` | 多机器人集群管理与调度 | 📋 规划中 |
| `teleop/` | 远程遥操作服务 | 📋 规划中 |
| `analytics/` | 运行数据采集与分析 | 📋 规划中 |
| `pipeline/` | 数据处理流水线（标注、清洗、训练） | 📋 规划中 |
| `identity/` | 设备认证与访问控制 | 📋 规划中 |
| `ota/` | OTA 固件/软件升级 | 📋 规划中 |
| `monitor/` | 远程监控与告警 | 📋 规划中 |
| `api/` | 开放 API 网关 | 📋 规划中 |

## 技术栈（建议）

| 组件 | 方案 |
|------|------|
| API 网关 | Kong / Envoy |
| 推理引擎 | Triton Inference Server / vLLM |
| 消息队列 | NATS / Kafka |
| 数据存储 | PostgreSQL + MinIO |
| 容器编排 | Kubernetes |
| 服务网格 | Istio |
| 可观测性 | Prometheus + Grafana + OpenTelemetry |
| 边缘-云端通信 | gRPC / MQTT |

## 与 qoobrain 的关系

```
qoocloud (云端) ←──gRPC/MQTT──→ qoobrain (大脑OS)
     │
     ├── 云端大模型推理
     ├── 知识库同步
     ├── 远程遥操作
     └── 多机协作调度
```

## 许可

Apache-2.0
