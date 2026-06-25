# Changelog

All notable changes to Brain OS will be documented in this file.

---

## [1.0.0-alpha] — 2026-06-24

### Phase 1 原型验证完整发布

#### Added

##### brain_core (C++17 实时引擎)
- ROS2 Bridge: NodeManager, TopicAdapter（发布/订阅/服务调用）
- Behavior Engine: BT Loader, Tree Executor, 10 Action Nodes
- Motion Planner: TRAC-IK 逆运动学求解器 + 轨迹生成器
- Safety Monitor: FCL 碰撞检测 + 4 级安全状态机 + Emergency Stop
- HAL Interface: JointDriver, GripperDriver, SensorReader
- gRPC Client: 与 brain_ai 通信
- Utils: pose_utils, coordinate_transform, time_utils, logger, thread_pool
- 8 个 gtest 单元测试
- 编译验证脚本 (scripts/verify_brain_core_build.py)

##### brain_ai (Python 3.11 认知引擎)
- Domain Layer: 领域模型、值对象、服务接口
- LLM Agent: Qwen2.5-7B 集成、提示词管理、工具调用
- Intent Parser: 中文指令 → 结构化意图
- Task Decomposer: 意图 → 子任务 DAG
- BT Generator: 子任务 → BehaviorTree XML
- Planner: 多策略轨迹选择 + HITL 管理 + 事件分发
- Perception: YOLOv11, ORB-SLAM3, SceneGraph, 3DGS, 传感器融合
- Knowledge: 经验存储、语义检索、技能注册
- Voice I/O: ASR (Web Speech / Whisper) + TTS
- gRPC Server: 6 服务实现 (Cognition/Decision/Perception/Control/Safety/Knowledge)
- WebSocket Server: 实时事件推送
- 118 个 pytest 单元测试

##### brain_viz (TypeScript Web Dashboard)
- Scene View: Three.js 3D 场景渲染、5 种摄像头预设、幽灵轨迹
- ChatPanel: 文本聊天、语音输入、意图展示、子任务时间线
- HITL Panel: 轨迹选择、评分图表、策略标签、参数微调
- Status Monitor: 健康卡、警报列表、日志查看器、指标面板
- Dev Panel: API Tester, Skill Registry, BT Viewer, Proto Viewer
- Common Components: Button, Modal, Slider, Toast, Badge, ProgressBar, Tooltip, LoadingSpinner
- Providers: Auth → Theme → Toast → Layout Manager
- Hooks: useWebSocket, useGrpcStream, useRobotState, useSceneData 等 8 个
- Services: gRPC Client, ROS2 Bridge, 6 个领域客户端
- Utils: colorMap, formatTime, physics, ros2three, three2ros
- Zustand Stores: chatStore, monitorStore
- 5 个测试 (组件 + Store + E2E)

##### brain_proto
- 6 gRPC 服务定义（Cognition/Decision/Perception/Control/Safety/Knowledge）
- 完整类型系统（Intent, SubTask, Trajectory, BehaviorTree 等）
- C++ 和 Python 代码生成脚本

##### brain_sdk
- RobotClient 统一入口
- 6 个模块客户端（Cognition/Decision/Perception/Control/Safety/Knowledge）

##### brain_sim
- Gazebo 仿真: tabletop/warehouse/living_room 世界 + Kinova Gen3 + TurtleBot 4
- Isaac Sim: pick_and_place 环境
- 端到端演示脚本 (4 场景)

##### brain_docs
- MkDocs Material 文档站点
- 13 页完整中文文档（安装/快速上手/Dashboard/HITL/语音/SDK/架构/模块/贡献/API）

##### brain_deploy
- 4 个 Dockerfile + docker-compose.yml
- Envoy 代理配置
- Shell 部署脚本

##### Tests & Tools
- 端到端集成测试 (12 用例, 测试完整指令→执行流水线)
- 性能基准测试框架 (8 指标, SLA 对比, 历史趋势)
- C++ 编译验证脚本
- 项目完整性扫描脚本

---

## 下一步

Phase 2 路线图详见 [00_docs/12_Phase1回顾与Phase2路线.md](00_docs/12_Phase1回顾与Phase2路线.md)

- M6: 仿真验证（第 28 周）
- M7: 真机联调（第 32 周）
- M8: SDK 发布（第 36 周）
- M9: Phase 2 发布（第 40 周）
