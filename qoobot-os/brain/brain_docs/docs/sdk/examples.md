# SDK 示例代码

以下示例演示 Brain OS Python SDK 的常见使用场景。

---

## 示例 1: Hello World

最简单的一次性指令：

```python
from brain_sdk import RobotClient

robot = RobotClient("localhost:50052", mock_mode=True)

# 一句话执行
result = robot.execute("把桌上的红色杯子拿给我")
print(f"结果: {'成功' if result.success else '失败'}")
print(f"耗时: {result.total_ms:.0f}ms")
print(f"子任务: {len(result.subtasks)}")
print(f"轨迹: {len(result.trajectories)}")
```

---

## 示例 2: 分步控制

手动控制流水线每一步：

```python
from brain_sdk import RobotClient

robot = RobotClient(mock_mode=True)

# 1. 意图解析
intent = robot.cognition.parse_intent("将蓝色瓶子移动到桌子右侧")
print(f"意图: {intent.type_name}, 置信度: {intent.confidence:.0%}")

# 2. 任务分解
response = robot.cognition.decompose_task(intent, robot_id="kinova_gen3")
plan_id = response.plan_id
print(f"计划 ID: {plan_id}")

# 3. 行为树
bt = robot.cognition.generate_bt(plan_id, response.subtasks)
print(f"行为树: {bt.tree_id}")

# 4. 运动规划
from brain_os.common.types_pb2 import Pose, Vector3, Quaternion

target = Pose(
    position=Vector3(x=0.5, y=0.0, z=0.3),
    orientation=Quaternion(x=0, y=0, z=0, w=1),
)

trajectories = robot.decision.generate_trajectories(
    "kinova_gen3", plan_id, target, num_candidates=5
)
print(f"生成轨迹: {len(trajectories)} 条")

# 5. 选择轨迹
best = max(trajectories, key=lambda t: t.score)
selected = robot.decision.select_trajectory(
    "kinova_gen3", plan_id, best.trajectory_id
)
print(f"已选择: {best.trajectory_id}")

# 6. 执行
robot.control.execute_trajectory(best)
print("执行完成!")
```

---

## 示例 3: 安全监控

实时安全状态监听：

```python
from brain_sdk import RobotClient
import time

robot = RobotClient(mock_mode=True)

alerts = []

def on_safety_alert(event):
    alerts.append(event)
    print(f"[ALERT] 级别={event.level} 消息={event.message}")
    if event.level == "CRITICAL":
        robot.safety.emergency_stop()
        print("[STOP] 紧急停止!")

def on_status_change(status):
    print(f"[STATUS] {status.level}: {status.message}")

robot.subscribe("safety_alert", on_safety_alert)
robot.safety.on_change(on_status_change)

# 执行任务时持续监控
robot.execute("清理工作台上的所有物品")

time.sleep(1)
print(f"收到的警报: {len(alerts)} 条")
```

---

## 示例 4: 场景感知

查询环境中的物体：

```python
robot = RobotClient(mock_mode=True)

# 获取完整场景
scene = robot.perception.get_scene_graph()
print(f"场景中的物体: {len(scene.objects)}")
for obj in scene.objects:
    print(f"  - {obj.label} 置信度={obj.confidence:.0%}")

# 查询特定物体
cups = robot.perception.query_objects(label="cup", min_conf=0.7)
print(f"检测到的杯子: {len(cups)} 个")

# 获取机器人当前位置
pose = robot.perception.get_localization()
print(f"当前位置: ({pose.position.x:.2f}, "
      f"{pose.position.y:.2f}, {pose.position.z:.2f})")
```

---

## 示例 5: 知识库查询

利用历史经验指导当前任务：

```python
robot = RobotClient(mock_mode=True)

# 查询相似任务的历史经验
episodes = robot.knowledge.search_episodes(
    robot_id="kinova_gen3",
    query_text="抓取红色物体",
    top_k=5,
    min_score=0.6,
    success_only=True,
)
print(f"找到 {len(episodes.episodes)} 条成功经验")

# 列出可用的技能
skills = robot.knowledge.list_skills("manipulation")
for skill in skills:
    print(f"  技能: {skill.skill_name}")
```

---

## 示例 6: 并发执行

同时控制多台机器人：

```python
from concurrent.futures import ThreadPoolExecutor

robots = {
    "arm_1": RobotClient("192.168.1.10:50052"),
    "arm_2": RobotClient("192.168.1.11:50052"),
}

instructions = {
    "arm_1": "把杯子拿给我",
    "arm_2": "把盒子叠起来",
}

def execute(robot_id, instruction):
    robot = robots[robot_id]
    result = robot.execute(instruction)
    return robot_id, result

with ThreadPoolExecutor(max_workers=2) as pool:
    futures = [
        pool.submit(execute, rid, inst)
        for rid, inst in instructions.items()
    ]
    for future in futures:
        rid, result = future.result()
        print(f"{rid}: {'成功' if result.success else '失败'} "
              f"({result.total_ms:.0f}ms)")
```

---

## 示例 7: 自定义技能

注册新的机器人技能：

```python
from brain_os.knowledge.types_pb2 import Skill

new_skill = Skill()
new_skill.skill_name = "sort_objects_by_color"
new_skill.description = "按颜色分类桌面物体"
new_skill.parameters = {
    "target_workspace": "table_1",
    "color_priority": ["red", "blue", "green"],
    "sort_position": "shelf_2",
}

response = robot.knowledge.register_skill(new_skill)
print(f"技能注册成功: {response.skill_id}")
```
