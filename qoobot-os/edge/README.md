# QooEdge — 边缘计算层

[![C++](https://img.shields.io/badge/C%2B%2B-17-blue.svg)](https://isocpp.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](../../LICENSE)
[![Status](https://img.shields.io/badge/status-v0.1-brightgreen.svg)]()

> QooBot 边缘计算中间件 — 端-云推理卸载 / 数据同步 / 多机器人 Mesh 网络

---

## 概述

QooEdge 运行在机器人端侧计算平台 (onboard_core)，介于端侧 AI 推理引擎 (QooCore) 和云端服务 (QooCloud) 之间。对标 **AWS Greengrass + Azure IoT Edge + ROS 2 DDS**。

### 核心能力

| 模块 | 功能数 | 说明 |
|------|:------:|------|
| ⚡ **edge_runtime** | 5 | 优先级调度、模型 LRU 缓存、任务取消、统计输出、优雅关闭 |
| 🧠 **edge_offload** | 7 | 多因素决策、实时强制本地、离线模式、批量决策、网络/能耗预算 |
| ☁️ **edge_sync** | 6 | 双向同步、4种策略 (FULL/INCREMENTAL/DELTA/LAZY)、版本管理、强制同步 |
| 📡 **edge_mesh** | 7 | mDNS 节点发现、话题发布/订阅、消息路由、心跳机制、拓扑查询 |

### 入口

- **`qooedge-daemon`** — 边缘守护进程
- **`qooedge-cli`** — 命令行管理工具

---

## 快速开始

### 构建

```bash
cd qoobot-os/edge
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
```

### 运行测试

```bash
./test/test_qooedge
```

预期输出：

```
qooedge Test Suite v0.1.0
...
Total: 33 Passed: 33 Failed: 0
```

---

## 目录结构

```
edge/
├── CMakeLists.txt              # 顶层 CMake 构建
├── README.md                   # 本文件
├── QOOEDGE_PLANNING.md         # 规划文档
├── docs/
│   └── 01功能清单完成进度.md    # 功能清单与进度
├── include/qooedge/            # 公共头文件
│   ├── edge_types.h            #   类型系统
│   ├── edge_runtime.h          #   推理运行时接口
│   ├── edge_offload.h          #   卸载决策引擎接口
│   ├── edge_sync.h             #   数据同步引擎接口
│   └── edge_mesh.h             #   Mesh 网络接口
├── src/
│   ├── main.cpp                #   守护进程入口
│   ├── cli/qooedge_cli.cpp     #   CLI 工具
│   ├── edge_runtime/           #   推理运行时实现
│   ├── edge_offload/           #   卸载决策引擎实现
│   ├── edge_sync/              #   数据同步引擎实现
│   └── edge_mesh/              #   Mesh 网络实现
└── test/
    ├── test_main.cpp           #   测试框架
    ├── test_edge_runtime.cpp   #   运行时测试 (6用例)
    ├── test_edge_offload.cpp   #   卸载引擎测试 (9用例)
    ├── test_edge_sync.cpp      #   同步引擎测试 (11用例)
    └── test_edge_mesh.cpp      #   Mesh 网络测试 (7用例)
```

---

## 相关模块

| 组件 | 关系 |
|------|------|
| QooCore (ai-engine/) | edge_runtime 通过 QooCore C API 调用端侧推理 |
| QooCloud (qoobot-service/cloud/) | edge_sync 通过 gRPC streaming 与云端同步 |
| QooStore (store/) | 技能运行时高计算任务可卸载到 edge_runtime |

---

## 许可证

Apache 2.0 — 详见 [LICENSE](../../LICENSE)
