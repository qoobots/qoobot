# 快速上手

5 分钟内启动 Brain OS 仿真演示，通过自然语言指令控制虚拟机器人。

---

## 启动演示

如果已经完成 [安装](installation.md)，可以直接运行：

```bash
# 选择一个场景运行端到端演示
python brain_sim/demo/e2e_demo.py --scenario pick_cup

# 或运行全部场景
python brain_sim/demo/e2e_demo.py --all
```

---

## 可用场景

| 场景 | 指令 | 描述 |
|------|------|------|
| `pick_cup` | 把桌上的红色杯子拿给我 | 标准抓取-交付流程 |
| `stack_boxes` | 把桌子上的两个盒子叠起来 | 多步操作序列 |
| `inspect_arm` | 检查机械臂是否在安全位置 | 安全状态检测 |
| `wild_goose` | 给我变个魔术 | 异常输入处理演示 |

---

## 场景演示流程

每个演示场景会依次执行以下步骤：

```
Step 0: 系统初始化 → 启动 gRPC 服务、ROS2 桥接、模型运行时
Step 1: 场景初始化 → 加载 Gazebo 世界、生成物体、设定位姿
Step 2: 环境感知   → YOLO 目标检测、ORB-SLAM3 定位、碰撞扫描
Step 3: 认知引擎   → 意图解析、任务分解、行为树生成
Step 4: 运动规划   → 多策略轨迹生成、HITL 自动选择
Step 5: 执行反馈   → 轨迹执行、抓手控制、安全监控
Step 6: 清理收尾   → 状态广播、资源释放
```

---

## 预期输出

```
═══════════════════════════════════════════════════════════
  Brain OS 端到端演示 — 拿杯子演示
═══════════════════════════════════════════════════════════
     场景     : 机械臂从桌面上拾取红色杯子递给操作员
     指令     : 把桌上的红色杯子拿给我

  ╭─ Step 0: 系统初始化
     ├─ CognitionService    :50052  [OK]
     ├─ DecisionService     :50052  [OK]
     ├─ KnowledgeService    :50052  [OK]
     └─ PerceptionService   :50052  [OK]
  ✅  系统就绪 (50 ms)

  ╭─ Step 3: 认知引擎
     [CognitionService] ParseIntent...
       Type: INTENT_PICK, Confidence: 88%
  ✅  意图解析完成

     [CognitionService] DecomposeTask...
       └─ 5 subtasks: navigate → detect → plan → pick → place
  ✅  任务分解完成

  ╭─ Step 4: 运动规划
     [DecisionService] GenerateTrajectories...
       ├─ traj_0  score=0.92  [STOMP (safe)] ★ 推荐
       ├─ traj_1  score=0.80  [STOMP (fast)]
       └─ traj_2  score=0.68  [STOMP (min-jerk)]
  ✅  轨迹生成完成

═══════════════════════════════════════════════════════════
  Demo Report
═══════════════════════════════════════════════════════════
  Status     : ✅ SUCCESS
  Total time : 327 ms
═══════════════════════════════════════════════════════════
```

---

## 使用 Python SDK 控制机器人

```python
from brain_sdk import RobotClient

# 连接到机器人
robot = RobotClient("localhost:50052")

# 解析用户指令
intent = robot.cognition.parse_intent("把桌上的红色杯子拿给我")
print(f"意图: {intent.type}, 置信度: {intent.confidence:.0%}")

# 分解任务
plan = robot.cognition.decompose_task(intent)
print(f"子任务: {len(plan.subtasks)} 个")

# 生成行为树
bt = robot.cognition.generate_bt(plan.plan_id, plan.subtasks)
print(f"行为树: {bt.tree.tree_id}")

# 规划轨迹
trajectories = robot.decision.generate_trajectories(
    plan.plan_id, goal_pose
)
print(f"候选轨迹: {len(trajectories)} 条")

# 选择最佳轨迹
best = robot.decision.select_trajectory(
    plan.plan_id, trajectories[0].trajectory_id
)

# 执行
robot.control.execute_trajectory(best)
```

---

## 启动 Web Dashboard

```bash
cd brain_viz
npm run dev
```

浏览器打开 `http://localhost:3000` 即可看到 3D 可视化界面。

---

## 下一步

- 了解 [Dashboard 操作指南](../user-guide/dashboard.md)
- 了解 [人在回路 (HITL)](../user-guide/hitl.md)
- 查看 [Python SDK 文档](../sdk/python-sdk.md)
- 深入 [架构设计](../development/architecture.md)
