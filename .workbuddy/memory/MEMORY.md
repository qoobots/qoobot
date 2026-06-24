# Brain OS (qoobot) 项目长期记忆

## 项目定位
具身智能机器人操作系统，目标：自然语言指令 → 机器人执行完整技术栈。

## 工程结构
Monorepo，9 个子项目：
- brain_core (C++17)：实时引擎，ament_cmake，0 空文件，完成度 ~100%（含编译验证脚本 + 8 gtest）
- brain_ai (Python 3.11)：AI 引擎，0 空文件，完成度 ~98%
- brain_viz (TypeScript/Next.js)：前端，Three.js/Tailwind，0 空文件，完成度 ~100%
- brain_sdk：Python SDK 完成度 ~90%（client.py 7 命名空间 + 12 API 类集成 gRPC stub + 4 类型文件 + speech_api + direct_control + pip install 可安装 + 66 测试通过）
- brain_proto：6 服务 .proto 已完成（cognition/decision/perception/control/safety/knowledge）
- brain_sim：Gazebo+Isaac Sim 物理仿真完成度 ~85%（SDF 机器人模型+4 模型库+3 世界+sim_bridge+sensor_config+Isaac Sim 集成+测试套件 51/51 通过）
- brain_models：Git LFS 配置 + model_registry.json（11模型）+ download/convert/validate 脚本 + model_path_resolver + 基准测试框架，完成度 ~85%
- brain_deploy：4 Dockerfile + envoy.yaml + docker-compose.yml + shell 脚本已完成
- brain_docs：MkDocs Material 站点全部完成（17/17 文件含实质内容），安装/快速上手/用户指南/SDK/开发/API参考/CI部署就绪

## 文档体系
00_docs/ 下 11 份文档（01头脑风暴→11 CI/CD），均已完成初稿。
关键文档：02_系统功能设计(DDD) / 03_系统架构设计(C4+分层) / 06_开发进度

## 关键技术
- 通信：ROS 2 + gRPC + WebSocket
- LLM：Qwen2.5-7B (TRT-LLM) + DeepSeek-V3 云端
- 行为树：BehaviorTree.CPP 4.x
- 运动规划：MoveIt 2 + STOMP + TRAC-IK + FCL
- 感知：ORB-SLAM3 + YOLOv11 + SAM 2 + 3DGS
- 目标硬件：Jetson Orin + Kinova Gen3 机械臂 + TurtleBot 4

## 开发进度
当前：Phase 2 Sprint 9 ✅ 完成 → 整体代码完成度 ~94%
里程碑：M1(骨架)✅ / M2(认知)✅ / M3(感知)✅ / M4(行为树)✅ / M5(可视化)✅ / M6(集成)✅ / M7(仿真)✅ / M8(模型)✅ / M9(SDK)✅

### 已完成 Sprint
- Sprint 1 (15/15): monorepo + gRPC + WebSocket + CI + Docker
- Sprint 2 (15/17): domain/knowledge/llm_agent/planner，16+29 测试通过
- Sprint 3 (7/9): perception 9 模块 + ros2_bridge + PerceptionService，60 测试通过
- Sprint 4 (7/7): brain_core C++ 端全部实现（84 文件），0 空文件
- Sprint 5 (7/7): brain_viz 全部实现（67 文件填充），0 空文件
- Sprint 6 (6/6): E2E 集成测试(12/12)+仿真 Demo(4场景)+性能基准(8指标)+文档(12页)+Phase 1 回顾+发布打包
- Sprint 7 (6/6): brain_sim 物理仿真（Gazebo 机器人SDF+4模型+3世界+sim_bridge+sensor_config+Isaac Sim集成+测试51/51通过）
- Sprint 8 (6/6): brain_models 模型部署（model_registry+download/convert/validate 脚本+model_path_resolver+适配器路径对齐+基准测试+测试41/41通过）
- Sprint 9 (7/7): brain_sdk SDK 完善（11 个 __init__.py + 12 API gRPC 集成 + 4 类型文件 + speech_api + direct_control + README + 示例 + 测试 66/66 + pip install）

### 模块完成度
- brain_proto 100% / brain_core ~100% / brain_ai ~98% / brain_viz ~100% / brain_docs 100% / brain_sim ~85% / brain_models ~85% / brain_sdk ~90%
- brain_deploy 47%
- 累计测试 301 项（293 Python + 8 gtest C++），全部通过

### 下一步
Phase 2 P1 剩余：brain_deploy（47%→目标 70%+）/ brain_core 真机适配

## 用户偏好
- 先分析再动手
- 文档正式风格
