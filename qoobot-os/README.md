# QooBot-OS — 仿生人操作系统

[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](../LICENSE)
[![C++](https://img.shields.io/badge/C%2B%2B-17-blue.svg)](https://isocpp.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow.svg)](https://www.python.org/)
[![ROS 2](https://img.shields.io/badge/ROS2-Humble-orange.svg)](https://docs.ros.org/en/humble/)

> QooBot Humanoid Robot Operating System — 端侧 AI 推理 + 具身智能大脑 + 硬件抽象层 + 系统服务

---

## 概述

qoobot-os 是 QooBot 仿生人项目的**核心操作系统层**，运行在机器人端侧计算平台上。它提供了从芯片级 AI 推理到高层行为决策的完整软件栈。

## 架构分层

```
┌─────────────────────────────────────────────────────┐
│                    应用层                            │
│   qoobot-desktop / qoobot-web / qoobot-mobile        │
├─────────────────────────────────────────────────────┤
│                   QooBrain (大脑)                     │
│  ┌─────────┬──────────┬──────────┬───────────────┐  │
│  │brain_core│brain_ai  │brain_sdk │brain_data/sim │  │
│  │ C++/ROS2 │ Python   │ Python   │   Python      │  │
│  └─────────┴──────────┴──────────┴───────────────┘  │
├──────────────────────┬──────────────────────────────┤
│   QooCore (推理引擎)  │    QooSvc / QooEdge (服务)    │
│      C++17           │      C++ / Python            │
├──────────────────────┴──────────────────────────────┤
│                 QooBody HAL (硬件抽象层)              │
│   mechanical │ sensor │ actuator │ comm │ power      │
├─────────────────────────────────────────────────────┤
│            硬件层 (SoC / MCU / 传感器 / 执行器)       │
└─────────────────────────────────────────────────────┘
```

## 子项目

| 模块 | 目录 | 语言 | 状态 | 说明 |
|------|------|:----:|:----:|------|
| **QooCore** | [ai-engine/](ai-engine/) | C++17 | ✅ v0.5 | 端侧 AI 推理引擎，多后端(NPU/GPU/DSP/CPU) |
| **QooBrain** | [brain/](brain/) | C++/Python/TS | ✅ v0.1 | 大脑操作系统，行为树/事件总线/运动规划/安全监控 |
| **QooBody HAL** | [hal/](hal/) | C++ | ✅ | 硬件抽象层，机械/传感器/执行器/通信/电源/安全 |
| **QooSvc** | [services/](services/) | C++/Python | 🚧 | 机器人端系统服务，设备/OTA/日志/监控/网络/配置 |
| **QooStore** | [store/](store/) | C++ | 🚧 | 技能商店边缘运行时 |
| **QooEdge** | [edge/](edge/) | — | 📋 P1 规划 | 边缘计算层，端-云卸载/协同/网络 |

## 快速开始

### 环境要求

- **OS**: Ubuntu 22.04+ / Debian 12+ / Windows 11 (WSL2)
- **C++**: GCC 11+ / Clang 16+, CMake 3.25+
- **Python**: 3.11+
- **ROS 2**: Humble Hawksbill (brain_core 必需)
- **CUDA**: 12.0+ (GPU 后端可选)

### 构建全部模块

```bash
# 方式一：CMake Superbuild (推荐)
cd qoobot-os
mkdir build && cd build
cmake .. -DQOOBOT_BUILD_ALL=ON
cmake --build . --parallel $(nproc)

# 方式二：分模块构建
# QooCore
cd ai-engine && mkdir build && cd build
cmake .. && cmake --build .

# QooBrain (ROS 2)
cd brain
colcon build --symlink-install

# QooBrain (Python)
cd brain && pip install -e ".[ai,dev]"

# QooBody HAL
cd hal/mechanical && mkdir build && cd build
cmake .. && cmake --build .
```

### 运行测试

```bash
# Python 测试
cd qoobot-os/brain
python -m pytest brain_ai/tests/ brain_sdk/tests/ -v

# C++ 测试
cd ai-engine/build && ctest --output-on-failure
cd brain/build && ctest --output-on-failure
```

## 设计文档

各子项目均包含完整设计文档（`docs/` 目录）：

- `02架构设计.md` — 系统架构与模块设计
- `03交互设计.md` — 接口协议与数据流
- `04数据设计.md` — 数据模型与存储
- `05项目目录结构.md` — 代码组织规范

## 测试状态

| 子项目 | 框架 | 通过/总数 | 状态 |
|--------|------|:---------:|:----:|
| brain_ai | pytest | 143/143 | ✅ |
| brain 集成 | pytest | 235/240 | ✅ |
| brain_sdk | pytest | 66/66 | ✅ |
| HAL mechanical | Python | 4/4 模块 | ✅ |

详见项目根目录 [总体功能清单](../docs/04_开发跟踪/01总体功能清单完成进度.md)。

## 开发规范

- **C++**: C++17, Google Style (`.clang-format`), 头文件 `.h` + 源文件 `.cpp`
- **Python**: 3.11+, ruff + mypy, 类型注解必须
- **ROS 2**: ament_cmake, package.xml 声明依赖
- **Git**: 遵循 [Conventional Commits](https://www.conventionalcommits.org/)
- **CI**: GitHub Actions (`.github/workflows/`)

## 许可证

Apache 2.0 — 详见 [LICENSE](../LICENSE)
