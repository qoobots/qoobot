# qoobody ROS 2 Packages

> QooBot 机器人 ROS 2 生态集成，对标 unitree_ros-master。

## 包列表

| 包名 | 说明 | 状态 |
|------|------|------|
| `qoobot_description` | QooBot 机器人 URDF/Xacro 模型描述 + Launch + RViz + Gazebo | ✅ v0.1 |
| `qoobody_ros_bridge` | ROS 2 传感器/指令桥接节点 | ✅ v0.1 |

## 快速开始

```bash
# 构建
cd ~/ros2_ws
colcon build --packages-select qoobot_description qoobody_ros_bridge
source install/setup.bash

# URDF 可视化
ros2 launch qoobot_description display.launch.py

# MuJoCo 仿真 (带 ROS 桥接)
ros2 launch qoobot_description sim_mujoco.launch.py
ros2 launch qoobody_ros_bridge bridge.launch.py

# Gazebo 仿真
ros2 launch qoobot_description gazebo.launch.py world:=earth

# 键盘遥控
ros2 launch qoobody_ros_bridge teleop.launch.py

# 模型一致性校验
python3 qoobot_description/scripts/mujoco_urdf_validator.py \
  --mujoco qoobody/mechanical/mujoco/qoobot_float.xml \
  --urdf qoobot_description/urdf/qoobot.urdf.xacro \
  --joint-config qoobody/mechanical/mujoco/joint_ctrl_config.json
```

## 支持模型

| 模型 | 文件 | DOF |
|------|------|-----|
| 双足仿生人 | `urdf/qoobot.urdf.xacro` | 30 |
| 轮式底盘 | `urdf/wheeled/qoobot_wheeled.urdf.xacro` | 6 |
| 四足机器人 | `urdf/quadruped/qoobot_quadruped.urdf.xacro` | 12 |
| 6轴机械臂 | `urdf/manipulator/qoobot_arm6.urdf.xacro` | 6 |

## DOF 配置模式

```bash
# 通过参数选择 DOF 模式 (对标 G1 mode_machine)
ros2 launch qoobot_description display.launch.py dof_mode:=standard_30dof
ros2 launch qoobot_description display.launch.py dof_mode:=lite_23dof
ros2 launch qoobot_description display.launch.py dof_mode:=dual_arm_17dof
ros2 launch qoobot_description display.launch.py dof_mode:=mobile_manipulator_23dof
ros2 launch qoobot_description display.launch.py dof_mode:=full_dexterous_44dof
```

## 依赖

- ROS 2 Humble / Iron / Jazzy
- `robot_state_publisher`
- `joint_state_publisher_gui`
- `rviz2`
- `gazebo_ros` (可选, Gazebo 仿真)
- Python 3.8+
