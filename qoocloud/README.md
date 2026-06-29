# qoocloud — 仿生人云端服务

> 机器人的"iCloud"：云端推理、设备管理、OTA 升级、数据同步、多机器人编排。连接每一台 QooBot 与云端智能。

## 定位

qoocloud 是 QooBot 生态的云端基础设施，为运行 qoobrain 的机器人提供云端推理、设备管理、数据同步、远程遥控、多机协作等能力。

## 架构

```
qoocloud (Spring Cloud 微服务集群 :8080~:8208)
  ├── qoocloud-gateway     网关 (8080)     — 统一入口/鉴权/限流/路由
  ├── qoocloud-inference   推理服务 (8200)  — 大模型托管/推理调度/缓存/审计
  ├── qoocloud-device      设备管理 (8201)  — 注册/心跳/诊断/配置/分组/GIS
  ├── qoocloud-ota         OTA 升级 (8202)  — 固件/模型/技能/灰度/回滚
  ├── qoocloud-data        数据同步 (8203)  — 经验回放/知识库/联邦学习/隐私过滤
  ├── qoocloud-orchestra   多机编排 (8204)  — 集群管理/任务分配/协作调度
  ├── qoocloud-twin        数字孪生 (8205)  — 环境镜像/行为仿真/异常推演/回放
  ├── qoocloud-observability 可观测性 (8206) — 全链路追踪/日志/告警/用量
  ├── qoocloud-infra       云基础设施 (8207) — 多租户/弹性伸缩/灾备
  └── qoocloud-teleop      远程遥控 (8208)  — WebRTC 信令/控制转发/示教
```

## 模块

| 模块 | 端口 | 说明 | 状态 |
|------|------|------|------|
| `qoocloud-gateway` | 8080 | Spring Cloud Gateway 统一 API 入口 | ✅ 已完成 |
| `qoocloud-inference` | 8200 | 云端大模型推理托管 | ✅ 已完成 |
| `qoocloud-device` | 8201 | 设备注册/状态监控/远程诊断 | ✅ 已完成 |
| `qoocloud-ota` | 8202 | 固件/模型/技能 OTA 灰度升级 | ✅ 已完成 |
| `qoocloud-data` | 8203 | 经验回放/知识库/联邦学习 | ✅ 已完成 |
| `qoocloud-orchestra` | 8204 | 多机器人集群管理与协作调度 | ✅ 已完成 |
| `qoocloud-twin` | 8205 | 数字孪生/环境镜像/行为仿真 | ✅ 已完成 |
| `qoocloud-observability` | 8206 | 全链路追踪/日志聚合/智能告警 | ✅ 已完成 |
| `qoocloud-infra` | 8207 | 多租户隔离/弹性伸缩/灾备 | ✅ 已完成 |
| `qoocloud-teleop` | 8208 | WebRTC 远程遥控/控制转发/示教 | ✅ 已完成 |
| `qoocloud-common` | — | 公共 DTO/异常/配置/工具（库） | ✅ 已完成 |

## 技术栈

| 组件 | 方案 |
|------|------|
| 语言 | Java 21 |
| 框架 | Spring Boot 3.3 + Spring Cloud 2024.x |
| 注册/配置 | Nacos |
| 熔断限流 | Sentinel |
| 消息队列 | RocketMQ / Kafka |
| 数据库 | PostgreSQL + MyBatis-Plus + Spring Data JPA |
| 缓存 | Redis |
| 对象存储 | MinIO |
| 迁移工具 | Flyway |
| 服务调用 | OpenFeign + LoadBalancer |
| API 文档 | SpringDoc OpenAPI |
| 可观测性 | Micrometer + Prometheus + Actuator |
| 构建工具 | Maven (多模块) |
| 容器化 | Docker (多阶段构建) + K8s |
| Web 控制台 | Vue 3 + TypeScript + Element Plus |

## 与 qoobrain 的关系

```
qoocloud (云端) ←──gRPC/MQTT/WebRTC──→ qoobrain (大脑OS)
     │
     ├── 云端大模型推理
     ├── 设备管理 & OTA 升级
     ├── 数据同步 & 联邦学习
     ├── 远程遥控 & 示教
     └── 多机协作调度
```

## 工程基础设施

| 设施 | 状态 |
|------|------|
| `.gitignore` | ✅ |
| `.editorconfig` | ✅ |
| CI/CD (GitHub Actions 4-job) | ✅ |
| Docker 多阶段构建 | ✅ |
| Docker Compose (16 服务) | ✅ |
| Flyway 数据库迁移 (7 模块) | ✅ |
| 运维脚本 (init_db/deploy_all/backup/smoke_test) | ✅ |

## 快速开始

```bash
# 启动基础设施
docker compose up -d postgres redis nacos kafka minio

# 构建
bash scripts/build_all.sh compile

# 部署全部服务
bash scripts/deploy_all.sh

# 冒烟测试
bash scripts/smoke_test.sh
```

## 许可

Apache-2.0
