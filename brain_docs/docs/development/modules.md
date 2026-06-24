# 模块说明

Brain OS 由 9 个子项目组成，每个子项目负责独立的领域。

---

## 项目结构

```
brain_os/
├── brain_proto/        # Protobuf 服务定义
├── brain_core/         # C++17 实时引擎
├── brain_ai/           # Python 3.11 认知引擎
├── brain_viz/          # TypeScript Web Dashboard
├── brain_sdk/          # Python SDK
├── brain_sim/          # 仿真环境
├── brain_models/       # AI 模型文件
├── brain_deploy/       # 部署配置
└── brain_docs/         # 文档站点
```

---

## brain_core — C++17 实时引擎

| 子模块 | 源文件 | 功能描述 |
|--------|--------|---------|
| **ros2_bridge** | node_manager, topic_adapter | ROS 2 节点管理、Topic 发布订阅 |
| **behavior_engine** | bt_loader, tree_executor, 10 action_nodes | BehaviorTree.CPP v4 加载与执行 |
| **motion_planner** | ik_solver, trajectory_generator, path_smoother | TRAC-IK 逆运动学 + 轨迹参数化 |
| **safety_monitor** | collision_checker, emergency_stop, workspace_monitor | FCL 碰撞检测 + 4 级安全状态机 |
| **hal_interface** | joint_driver, gripper_driver, sensor_reader | 硬件抽象（Kinova Gen3 + TurtleBot 4） |
| **grpc_client** | brain_ai_client | 与 brain_ai 的 gRPC 通信 |
| **utils** | pose_utils, coordinate_transform, time_utils, logger, thread_pool | 通用工具 |

**编译**：

```bash
cd brain_core && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
ctest --output-on-failure
```

**测试**: 36 个 gtest 单元测试（8 个模块 × 4-5 项）

---

## brain_ai — Python 3.11 认知引擎

| 子模块 | 源文件 | 功能描述 |
|--------|--------|---------|
| **domain** | entities, value_objects, exceptions, services, repositories | 领域模型定义 |
| **model_runtime** | llm_runtime, vision_runtime, model_loader, device_manager | 模型加载与推理（Qwen2.5/YOLOv11） |
| **llm_agent** | agent_core, tool_adapter, prompt_manager, context_window | LLM 提示词管理与工具调用 |
| **planner** | intent_parser, task_decomposer, bt_generator, hitl_manager, trajectory_selector, strategies/* | 流水线编排 |
| **perception** | object_detector, scene_graph, localization, tracker, slam_wrapper, depth_estimator, instance_segmenter, sensor_fusion, 3dgs_renderer | 目标检测、SLAM、场景理解 |
| **ros2_bridge** | ros_client, topic_subscriber, service_client, action_client | ROS 2 接口封装 |
| **knowledge** | memory_store, experience_retriever, skill_registry, embedding_service | 知识库、经验存储 |
| **voice_io** | speech_recognizer, text_to_speech, audio_capture | 语音输入输出 |
| **grpc_server** | server, cognition_service, decision_service, knowledge_service, perception_service | gRPC 服务端 |
| **utils** | config_loader, metrics_collector, event_dispatcher, serializer | 基础设施 |

**测试**: 118 个 pytest 单元测试

---

## brain_viz — TypeScript Web Dashboard

| 模块 | 文件数 | 技术栈 |
|------|--------|--------|
| **types** | 2 | TypeScript 接口（事件、proto 类型） |
| **stores** | 2 | Zustand 状态管理（chat, trajectory） |
| **hooks** | 8 | 自定义 Hooks（WebSocket, gRPC Stream, 键盘） |
| **utils** | 4 | 颜色映射、时间格式化、物理计算、坐标转换 |
| **services** | 8 | gRPC 客户端 + WebSocket + 6 个服务客户端 |
| **components/common** | 8 | 通用 UI 组件（Button, Modal, Toast 等） |
| **components/chat-panel** | 4 | 文本聊天、语音、意图视图、子任务时间线 |
| **components/scene-view** | 5 | Three.js 3D 场景、摄像头、幽灵轨迹 |
| **components/hitl-panel** | 4 | 轨迹选择、评分图、策略标签 |
| **components/status-monitor** | 6 | 健康卡、警报、日志、指标、关节状态 |
| **components/dev-panel** | 6 | API 测试、技能表、行为树查看 |
| **styles** | 1 | 设计 Token 系统（颜色、间距、字体） |

**测试**: React Testing Library + Playwright E2E

---

## brain_sdk — Python SDK

| 模块 | 功能 |
|------|------|
| **client.py** | RobotClient 统一入口 |
| **cognition/** | 认知 API 封装 |
| **decision/** | 决策 API 封装 |
| **perception/** | 感知 API 封装 |
| **control/** | 控制 API 封装 |
| **safety/** | 安全 API 封装 |
| **knowledge/** | 知识库 API 封装 |

---

## brain_sim — 仿真环境

| 组件 | 描述 |
|------|------|
| **Gazebo Worlds** | tabletop, warehouse, living_room |
| **Gazebo Robots** | kinova_gen3.sdf, turtlebot4.sdf |
| **Isaac Sim** | pick_and_place 环境、训练脚本 |
| **demo** | 端到端演示脚本 |
| **config** | sim_config.yaml |

---

## brain_proto — Protobuf 定义

| 服务 | .proto | RPC 方法 |
|------|--------|----------|
| **Cognition** | cognition/types, cognition/service | ParseIntent, DecomposeTask, GenerateBehaviorTree, Clarify |
| **Decision** | decision/types, decision/service | GenerateTrajectories, SelectTrajectory, CancelPlan |
| **Perception** | perception/types, perception/service | GetSceneGraph, GetLocalization, StreamSceneGraph |
| **Control** | control/types, control/service | SendJointCommand, ExecuteTrajectory |
| **Safety** | safety/types, safety/service | GetStatus, EmergencyStop, AcknowledgeAlert |
| **Knowledge** | knowledge/types, knowledge/service | ListSkills, RegisterSkill, SearchEpisodes |

---

## Jetson Orin 部署

Brain OS 支持 NVIDIA Jetson Orin 平台部署：

| 组件 | 部署位置 |
|------|---------|
| brain_core (C++) | Jetson Orin（ARM64 编译） |
| brain_ai (Python) | 云端 / Jetson Orin |
| brain_viz | 云端 / 局域网 |
| YOLOv11 ONNX | Jetson Orin GPU 推理 |
| ORB-SLAM3 | Jetson Orin CPU 推理 |

```bash
# Jetson Orin 编译
cd brain_core
mkdir build_jetson && cd build_jetson
cmake .. \
    -DCMAKE_TOOLCHAIN_FILE=../cmake/jetson_orin.cmake \
    -DCMAKE_BUILD_TYPE=Release
make -j8
```
