# qoodev — 仿生人开发者工具链

> 机器人的"Xcode"：IDE、仿真器、调试器、性能剖析、数据标注、CI/CD。
>
> **对标**：Xcode + Instruments + TestFlight + App Store Connect 的完整开发工具生态。
>
> **当前版本**：v1.6.0

## 定位

qoodev 是 QooBot 生态的开发者工具平台，提供从项目脚手架、代码编写、仿真调试、
性能分析到打包发布的一站式开发体验。它是第三方开发者为 QooBot 开发应用的核心入口。

**依赖**：qoobrain（需集成其 API 和仿真环境）
**被依赖**：qoostore、qoocommunity

## 快速开始

```bash
pip install qoodev
qoo init my-first-skill
cd my-first-skill
qoo build
qoo run --sim mujoco --scene home
```

详见[快速入门](docs/05快速入门.md)。

## 文档索引

| 文档 | 说明 |
|------|------|
| [功能清单与进度](docs/01功能清单完成进度.md) | 56 项功能模块清单与状态跟踪 |
| [架构设计](docs/02架构设计.md) | 整体技术架构、分层设计、数据流 |
| [开发路线图](docs/03开发路线图.md) | 版本规划、里程碑、交付物 |
| [技术选型](docs/04技术选型.md) | 各模块技术栈选择与理由 |
| [快速入门](docs/05快速入门.md) | 5 分钟上手教程 |
| [项目结构](docs/06项目结构.md) | 目录结构与模块职责 |
| [交互设计](docs/07交互设计.md) | CLI/IDE/Dashboard 多入口交互设计 |
| [数据设计](docs/08数据设计.md) | .qooskills/.qoodata/.qooannot 等格式设计 |

## 工程基础设施

| 组件 | 状态 |
|------|------|
| `.gitignore` 版本控制 | ✅ |
| `.editorconfig` 编辑器规范 | ✅ |
| `pyproject.toml` v1.6.0 | ✅ |
| `tests/` 单元测试框架 | ✅ |
| `.github/workflows/` CI/CD | ✅ |
| `qoobot-sdk/` Python SDK | ✅ |
| `vscode-plugin/` VS Code 插件 | ✅ |
| `qoodev-lsp/` LSP 语言服务器 | ✅ |
| `web-dashboard/` Web 仿真面板 | ✅ |

## 模块概览

| 模块 | 说明 | 状态 |
|------|------|------|
| `cli/` | 命令行开发工具（init/build/run/test/package...） | ✅ 已完成 |
| `sim_bridge/` | 仿真桥接层（MuJoCo/Isaac Sim + 桩模式） | ✅ 已完成 |
| `packager/` | 技能打包（.qooskills + 签名 + 依赖管理） | ✅ 已完成 |
| `debugger/` | 远程调试器（Python/C++ 混合调试） | ✅ 已完成 |
| `profiler/` | 性能剖析（延迟/火焰图/通信/功耗） | ✅ 已完成 |
| `data_recorder/` | 示教录制与回放（.qoodata 格式） | ✅ 已完成 |
| `annotation/` | 数据标注工具（2D/3D/轨迹标注） | ✅ 已完成 |
| `compiler/` | 模型编译桥接（qoocore 集成） | ✅ 已完成 |
| `testing/` | 测试框架（Mock 传感器/模糊测试/兼容性测试） | ✅ 已完成 |
| `stability/` | 稳定性框架（错误处理/输入校验/崩溃收集） | ✅ 已完成 |
| `ide/` | IDE 集成（JetBrains/技能清单/代码生成） | ✅ 已完成 |
| `bt_debugger/` | 行为树调试器（断点/步进/回放） | ✅ 已完成 |
| `data_management/` | 数据管理（版本/清洗/质量/分割/导出） | ✅ 已完成 |
| `domain_randomization/` | 域随机化（Sim2Real 迁移） | ✅ 已完成 |
| `qoobot-sdk/` | Python/C++ SDK | ✅ 已完成 |
| `vscode-plugin/` | VS Code 插件（语法高亮/补全/行为树编辑器） | ✅ 已完成 |
| `qoodev-lsp/` | LSP 语言服务器 | ✅ 已完成 |
| `web-dashboard/` | Web 仿真监控面板（Vue 3 + Three.js） | ✅ 已完成 |

## 子系统划分

| 子系统 | 功能数 | 说明 |
|--------|--------|------|
| 🖥️ IDE 集成 | 6 | VS Code/JetBrains 插件、行为树编辑器、项目脚手架、技能清单编辑器、代码生成器 |
| 🤖 仿真环境 | 8 | Isaac Sim/MuJoCo 集成、传感器仿真、场景库、域随机化、数字孪生、多机器人仿真、硬件在环、加速仿真 |
| 🐛 调试与诊断 | 7 | 实时日志、行为树调试、传感器可视化、3D 位姿显示、回放调试 |
| 📊 性能剖析 | 5 | 全链路延迟分析、资源火焰图、通信剖析、功耗追踪、模型推理剖析 |
| 🎬 示教与数据 | 6 | 遥操作录制、数据标注(2D/3D)、数据管理(版本/清洗/质量/分割/导出)、数据增强、人类偏好标注 |
| 📦 构建与打包 | 6 | 技能打包(.qooskills)、依赖管理、代码签名、模型编译集成、多架构编译、资源打包(.qoor) |
| 🧪 测试与 CI/CD | 6 | 单元测试框架、仿真回归测试、CI/CD 流水线、模型评估、模糊测试、兼容性测试 |
| 📚 文档与 SDK | 7 | Python SDK+C++ SDK、API 文档、教程与示例、REST/gRPC API、迁移指南、视频课程 |
| 🚀 发布与分发 | 5 | 技能提交、版本管理、崩溃收集、测试分发、使用统计 |
| **合计** | **56** | |

## 开发工作流

```
                    ┌──────────────────────────────────┐
                    │           qoodev                 │
                    │                                  │
  qoo init ────────►│  创建项目脚手架                     │
  ide_plugin ──────►│  VSCode 中编码（语法高亮/补全/提示）  │
  qoo build ───────►│  编译构建（Python/C++/Model）       │
  qoo sim ─────────►│  仿真环境中运行调试                  │
  debugger ────────►│  断点/回放/状态检查/3D 可视化        │
  profiler ────────►│  性能分析（延迟/资源/通信）          │
  qoo test ────────►│  自动化测试                          │
  qoo package ─────►│  打包签名 → .qooskills             │
  qoo eco submit ──►│  发布到 qoostore 市场                │
                    └──────────────────────────────────┘
```

## 版本规划

| 版本 | 代号 | 目标 |
|------|------|------|
| v0.1 | Scaffold | CLI 脚手架 + Python SDK ✅ |
| v0.3 | IDE Base | VS Code 插件基础体验 ✅ |
| v0.5 | Simulate | 仿真环境 + 可视化调试 ✅ |
| v0.7 | Full Loop | 打包签名 + CI/CD ✅ |
| v1.0 | GA | 正式发布，完整开发闭环 ✅ |
| v1.5 | Ecosystem | JetBrains 插件、高级分析、数字孪生 ✅ |
| v1.6 | Polish | 工程基础设施完善、build/run 命令实现、测试框架 ✅ |

详见[开发路线图](docs/03开发路线图.md)。

## iPhone 类比

| iPhone 工具 | qoodev 对应 |
|-------------|-------------|
| Xcode | IDE 插件 + CLI |
| Simulator | sim_bridge |
| Instruments | profiler |
| TestFlight | CI/CD（测试分发） |
| App Store Connect | 技能发布与分发（qoostore 集成） |
| Swift Playgrounds | 在线沙盒学习环境 |

## 与 qoobrain 的关系

```
qoodev ──开发/调试──→ qoobrain (大脑OS)
         ──部署/测试──→ qoobody (硬件)
         ──发布───────→ qoostore (技能市场)
```

## 许可

Apache-2.0
