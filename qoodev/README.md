# qoodev — 人形机器人开发者工具链

> 机器人的"Xcode"：IDE、仿真器、调试器、性能剖析、数据标注、CI/CD。
>
> **对标**：Xcode + Instruments + TestFlight + App Store Connect 的完整开发工具生态。

## 定位

qoodev 是 QooBot 生态的开发者工具平台，提供从项目脚手架、代码编写、仿真调试、
性能分析到打包发布的一站式开发体验。它是第三方开发者为 QooBot 开发应用的核心入口。

**依赖**：qoobrain（需集成其 API 和仿真环境）
**被依赖**：qooeco、qoocommunity

## 文档索引

| 文档 | 说明 |
|------|------|
| [功能清单与进度](docs/01功能清单完成进度.md) | 56 项功能模块清单与状态跟踪 |
| [架构设计](docs/02架构设计.md) | 整体技术架构、分层设计、数据流 |
| [开发路线图](docs/03开发路线图.md) | 版本规划、里程碑、交付物 |
| [技术选型](docs/04技术选型.md) | 各模块技术栈选择与理由 |

## 模块概览

| 模块 | 说明 | 状态 |
|------|------|------|
| `cli/` | 命令行开发工具（项目脚手架、构建、发布） | 📋 规划中 |
| `ide_plugin/` | VSCode / JetBrains 插件 | 📋 规划中 |
| `simulator/` | 机器人仿真调试环境（Isaac Sim / MuJoCo / Gazebo） | 📋 规划中 |
| `debugger/` | 机器人行为调试器（断点、回放、状态检查、可视化） | 📋 规划中 |
| `profiler/` | 性能剖析（全链路延迟、资源火焰图、通信带宽） | 📋 规划中 |
| `data_labeler/` | 训练数据标注工具（点云、图像、轨迹） | 📋 规划中 |
| `ci_cd/` | 自动化测试与部署流水线 | 📋 规划中 |
| `sdk/` | Python/C++ SDK（`qoobot-sdk`） | 📋 规划中 |
| `docs/` | 文档站点（API 参考、教程、示例） | 🚧 文档先行 |

## 子系统划分

| 子系统 | 功能数 | 说明 |
|--------|--------|------|
| 🖥️ IDE 集成 | 6 | VS Code/JetBrains 插件、行为树编辑器、项目脚手架 |
| 🤖 仿真环境 | 8 | Isaac Sim/MuJoCo 集成、传感器仿真、场景库、域随机化 |
| 🐛 调试与诊断 | 7 | 实时日志、传感器可视化、3D 位姿显示、回放调试 |
| 📊 性能剖析 | 5 | 全链路延迟分析、资源火焰图、通信剖析 |
| 🎬 示教与数据 | 6 | 遥操作录制、数据标注、数据版本管理 |
| 📦 构建与打包 | 6 | 技能打包(.qooskills)、依赖管理、代码签名 |
| 🧪 测试与 CI/CD | 6 | 单元测试框架、仿真回归测试、CI/CD 流水线 |
| 📚 文档与 SDK | 7 | Python/C++ SDK、API 文档、教程与示例 |
| 🚀 发布与分发 | 5 | 技能提交、版本管理、崩溃收集、使用统计 |
| **合计** | **56** | |

## 开发工作流

```
                    ┌──────────────────────────────────┐
                    │           qoodev                 │
                    │                                  │
  qoo init ────────►│  创建项目脚手架                     │
  ide_plugin ──────►│  VSCode 中编码（语法高亮/补全/提示）  │
  qoo sim ─────────►│  仿真环境中运行调试                  │
  debugger ────────►│  断点/回放/状态检查/3D 可视化        │
  profiler ────────►│  性能分析（延迟/资源/通信）          │
  qoo test ────────►│  自动化测试                          │
  qoo package ─────►│  打包签名 → .qooskills             │
  qoo publish ─────►│  发布到 qooeco 市场                 │
                    └──────────────────────────────────┘
```

## 版本规划

| 版本 | 代号 | 目标 |
|------|------|------|
| v0.1 | Scaffold | CLI 脚手架 + Python SDK |
| v0.3 | IDE Base | VS Code 插件基础体验 |
| v0.5 | Simulate | 仿真环境 + 可视化调试 |
| v0.7 | Full Loop | 打包签名 + CI/CD |
| v1.0 | GA | 正式发布，完整开发闭环 |

详见[开发路线图](docs/03开发路线图.md)。

## iPhone 类比

| iPhone 工具 | qoodev 对应 |
|-------------|-------------|
| Xcode | IDE 插件 + CLI |
| Simulator | simulator |
| Instruments | profiler |
| TestFlight | CI/CD（测试分发） |
| App Store Connect | 技能发布与分发 |
| Swift Playgrounds | 在线沙盒学习环境 |

## 与 qoobrain 的关系

```
qoodev ──开发/调试──→ qoobrain (大脑OS)
         ──部署/测试──→ qoobody (硬件)
         ──发布───────→ qooeco (技能市场)
```

## 许可

Apache-2.0
