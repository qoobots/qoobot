# qoocode — 具身机器人开发者工具链

> 机器人的"Xcode"：IDE、仿真器、调试器、性能剖析、数据标注。

## 定位

qoocode 是 QooBot 生态的开发者工具平台，提供从代码编写、仿真调试、
性能分析到部署发布的一站式开发体验。

## 模块

| 模块 | 说明 | 状态 |
|------|------|------|
| `simulator/` | 机器人仿真调试环境（物理引擎集成） | 📋 规划中 |
| `ide_plugin/` | VSCode / JetBrains 插件 | 📋 规划中 |
| `debugger/` | 机器人行为调试器（断点、回放、状态检查） | 📋 规划中 |
| `profiler/` | 性能剖析（计算延迟、通信带宽、内存占用） | 📋 规划中 |
| `data_labeler/` | 训练数据标注工具（点云、图像、轨迹） | 📋 规划中 |
| `ci_cd/` | 自动化测试与部署流水线 | 📋 规划中 |
| `cli/` | 命令行开发工具（项目脚手架、构建、发布） | 📋 规划中 |
| `logger/` | 可视化日志分析器 | 📋 规划中 |
| `ros2_tools/` | ROS 2 开发辅助工具 | 📋 规划中 |

## 开发工作流

```
                    ┌──────────────────────────────────┐
                    │           qoocode                 │
                    │                                  │
  qoocode CLI ─────►│  创建项目脚手架                     │
  ide_plugin ──────►│  VSCode 中编码（语法高亮/补全/提示）  │
  simulator ──────►│  仿真环境中运行调试                  │
  debugger ───────►│  断点/回放/状态检查                  │
  profiler ───────►│  性能分析                           │
  ci_cd ──────────►│  自动化测试 → 部署到机器人            │
                    └──────────────────────────────────┘
```

## iPhone 类比

| iPhone 工具 | qoocode 对应 |
|-------------|-------------|
| Xcode | IDE 插件 + CLI |
| Simulator | simulator |
| Instruments | profiler |
| TestFlight | ci_cd（测试分发） |
| Swift Playgrounds | 在线沙盒学习环境 |

## 与 qoobrain 的关系

```
qoocode ──开发/调试──→ qoobrain (大脑OS)
         ──部署/测试──→ qoobody (硬件)
```

## 许可

Apache-2.0
