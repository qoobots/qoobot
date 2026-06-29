# qoobot-proto

> QooBot 跨平台通信协议定义（Protobuf / gRPC）

## 定位

本目录作为协议索引中心，实际 `.proto` 文件分布在各自平台的目录中。
所有平台间 gRPC 通信均以本索引定义的协议为准。

## 协议清单

### 🔐 Auth（账号认证）
| 协议文件 | 位置 | 说明 |
|---------|------|------|
| `token_service.proto` | `qoobot-service/auth/proto/` | Token 管理服务 |
| `user_service.proto` | `qoobot-service/auth/proto/` | 用户管理服务 |
| `device_service.proto` | `qoobot-service/auth/proto/` | 设备管理服务 |
| `audit_service.proto` | `qoobot-service/auth/proto/` | 审计日志服务 |

### 🧠 Brain（大脑操作系统）
| 协议文件 | 位置 | 说明 |
|---------|------|------|
| `perception/service.proto` | `qoobot-os/brain/brain_proto/brain_os/perception/` | 感知服务 |
| `cognition/service.proto` | `qoobot-os/brain/brain_proto/brain_os/cognition/` | 认知服务 |
| `decision/service.proto` | `qoobot-os/brain/brain_proto/brain_os/decision/` | 决策服务 |
| `control/service.proto` | `qoobot-os/brain/brain_proto/brain_os/control/` | 控制服务 |
| `knowledge/service.proto` | `qoobot-os/brain/brain_proto/brain_os/knowledge/` | 知识服务 |
| `safety/service.proto` | `qoobot-os/brain/brain_proto/brain_os/safety/` | 安全服务 |
| `common/types.proto` | `qoobot-os/brain/brain_proto/brain_os/common/` | 通用类型定义 |

### ☁️ Cloud（云端服务）
| 协议文件 | 位置 | 说明 |
|---------|------|------|
| （待定义） | `qoobot-service/cloud/proto/` | 云端推理/OTA/设备管理协议 |

### 🔧 Services（机器人系统服务）
| 协议文件 | 位置 | 说明 |
|---------|------|------|
| `voice/asr_result.proto` | `qoobot-os/services/proto/voice/` | 语音识别结果 |
| `voice/tts_request.proto` | `qoobot-os/services/proto/voice/` | TTS 请求 |
| `navigation/goal.proto` | `qoobot-os/services/proto/navigation/` | 导航目标 |
| `navigation/path.proto` | `qoobot-os/services/proto/navigation/` | 导航路径 |
| `diagnostics/health_report.proto` | `qoobot-os/services/proto/diagnostics/` | 健康报告 |
| `multi_robot/discovery.proto` | `qoobot-os/services/proto/multi_robot/` | 多机器人发现 |

### 🔌 Gear（配件认证）
| 协议文件 | 位置 | 说明 |
|---------|------|------|
| `peripheral.proto` | `qoobot-service/gear/proto/` | 外设规范 |
| `certification.proto` | `qoobot-service/gear/proto/` | 认证流程 |
| `standard.proto` | `qoobot-service/gear/proto/` | 标准定义 |

### 🎮 Remote（远程操控）
| 协议文件 | 位置 | 说明 |
|---------|------|------|
| `teleop_command.proto` | `qoobot-web/remote/proto/` | 远程操控指令 |
| `teleop_media.proto` | `qoobot-web/remote/proto/` | 媒体传输 |
| `teleop_session.proto` | `qoobot-web/remote/proto/` | 会话管理 |
| `teleop_state.proto` | `qoobot-web/remote/proto/` | 状态同步 |
| `teleop_teaching.proto` | `qoobot-web/remote/proto/` | 示教记录 |

### 🏪 Store（技能商店）
| 协议文件 | 位置 | 说明 |
|---------|------|------|
| `store_skill.proto` | `qoobot-service/store/proto/` | 技能定义 |
| `store_order.proto` | `qoobot-service/store/proto/` | 订单管理 |
| `store_edge.proto` | `qoobot-service/store/proto/` | 端侧通信 |
| `store_analytics.proto` | `qoobot-service/store/proto/` | 数据分析 |

## 使用方式

各平台通过 gRPC 编译 proto 文件生成对应语言的客户端/服务端代码：

```bash
# C++ (qoobot-os)
protoc --cpp_out=. --grpc_out=. --plugin=protoc-gen-grpc=`which grpc_cpp_plugin` *.proto

# Java (qoobot-service)
protoc --java_out=. --grpc-java_out=. *.proto

# TypeScript (qoobot-web / qoobot-desktop)
protoc --ts_out=. *.proto

# Python (qoobot-os / qoobot-desktop)
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. *.proto
```

## 版本策略

- 协议版本与各平台独立版本解耦
- 协议变更遵循向后兼容原则（新增字段、不删除已有字段）
- 破坏性变更需要跨平台协调发布
