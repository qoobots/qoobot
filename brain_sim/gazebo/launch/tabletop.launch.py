"""
tabletop.launch.py — 启动桌面抓取仿真场景
用法:
  ros2 launch brain_sim tabletop.launch.py
  ros2 launch brain_sim tabletop.launch.py robot:=kinova_gen3 world:=warehouse
  ros2 launch brain_sim tabletop.launch.py robot:=turtlebot4 headless:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, SetEnvironmentVariable
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import os


def generate_launch_description():
    pkg_brain_sim = FindPackageShare("brain_sim")

    # =========================================================================
    # 参数声明
    # =========================================================================
    robot_arg = DeclareLaunchArgument(
        "robot",
        default_value="kinova_gen3",
        description="机器人型号: kinova_gen3 | turtlebot4 | mobile_manipulator",
    )

    gui_arg = DeclareLaunchArgument(
        "gui",
        default_value="true",
        description="是否启动 Gazebo GUI",
    )

    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="false",
        description="无头模式 (无GUI)",
    )

    world_arg = DeclareLaunchArgument(
        "world",
        default_value="tabletop",
        description="仿真世界: tabletop | warehouse | living_room",
    )

    paused_arg = DeclareLaunchArgument(
        "paused",
        default_value="false",
        description="启动时暂停物理引擎",
    )

    # =========================================================================
    # 环境变量
    # =========================================================================
    # 设置 GAZEBO_MODEL_PATH 使 Gazebo 找到自定义模型
    model_path_env = SetEnvironmentVariable(
        "GAZEBO_MODEL_PATH",
        PathJoinSubstitution([pkg_brain_sim, "gazebo", "models"])
    )

    # =========================================================================
    # Gazebo 世界文件
    # =========================================================================
    world_file = PathJoinSubstitution([
        pkg_brain_sim, "gazebo", "worlds",
        [LaunchConfiguration("world"), ".world"]
    ])

    # 启动信息
    world_info = LogInfo(
        msg=["Loading world: ", world_file]
    )

    # =========================================================================
    # Gazebo Server + GUI
    # =========================================================================
    # Gazebo server (always starts)
    gazebo_server = IncludeLaunchDescription(
        PathJoinSubstitution([
            FindPackageShare("gazebo_ros"), "launch", "gzserver.launch.py"
        ]),
        launch_arguments={
            "world": world_file,
            "verbose": "false",
            "pause": LaunchConfiguration("paused"),
        }.items(),
    )

    # Gazebo GUI (only if not headless)
    gazebo_gui = IncludeLaunchDescription(
        PathJoinSubstitution([
            FindPackageShare("gazebo_ros"), "launch", "gzclient.launch.py"
        ]),
        condition=UnlessCondition(LaunchConfiguration("headless")),
    )

    # =========================================================================
    # 机器人 URDF/SDF 加载
    # =========================================================================
    # Robot state publisher (TF transforms)
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "robot_description": "",  # 由 SDF→URDF 转换填充
            "publish_frequency": 50.0,
            "use_sim_time": True,
        }],
    )

    # =========================================================================
    # 传感器节点
    # =========================================================================
    # RGB Camera → ROS2 topic
    rgb_camera_node = Node(
        package="image_transport",
        executable="republish",
        name="rgb_republish",
        output="screen",
        arguments=["raw", "in:=/camera/color/image_raw", "out:=/brain_os/camera/rgb"],
        parameters=[{"use_sim_time": True}],
    )

    # Depth Camera → ROS2 topic
    depth_camera_node = Node(
        package="image_transport",
        executable="republish",
        name="depth_republish",
        output="screen",
        arguments=["raw", "in:=/camera/depth/image_rect_raw", "out:=/brain_os/camera/depth"],
        parameters=[{"use_sim_time": True}],
    )

    # =========================================================================
    # Brain OS 桥接节点
    # =========================================================================
    # ROS2 Bridge — connects Gazebo to Brain OS gRPC services
    brain_ros2_bridge = Node(
        package="brain_core",
        executable="ros2_bridge_node",
        name="brain_ros2_bridge",
        output="screen",
        parameters=[{
            "robot_id": "sim_robot_01",
            "grpc_address": "localhost:50051",
            "sim_mode": True,
            "use_sim_time": True,
            
            # Sensor topics
            "rgb_topic": "/camera/color/image_raw",
            "depth_topic": "/camera/depth/image_rect_raw",
            "points_topic": "/camera/depth/points",
            "lidar_topic": "/scan",
            "imu_topic": "/imu/data",
            "joint_states_topic": "/joint_states",
            "ft_sensor_topic": "/wrist_ft",
            
            # Control topics
            "cmd_vel_topic": "/cmd_vel",
            "arm_controller_topic": "/kinova_gen3/arm_controller/command",
            "gripper_controller_topic": "/kinova_gen3/gripper_controller/command",
            
            # Safety
            "collision_check_hz": 100,
            "emergency_stop_enabled": True,
        }],
    )

    # =========================================================================
    # 可选: RViz2 可视化
    # =========================================================================
    # rviz2_node = Node(
    #     package="rviz2",
    #     executable="rviz2",
    #     name="rviz2",
    #     arguments=["-d", PathJoinSubstitution([
    #         pkg_brain_sim, "config", "simulation.rviz"
    #     ])],
    #     condition=IfCondition(LaunchConfiguration("gui")),
    #     parameters=[{"use_sim_time": True}],
    # )

    # =========================================================================
    # 返回 Launch Description
    # =========================================================================
    return LaunchDescription([
        # Args
        robot_arg,
        gui_arg,
        headless_arg,
        world_arg,
        paused_arg,
        
        # Env
        model_path_env,
        
        # Info
        world_info,
        
        # Gazebo
        gazebo_server,
        gazebo_gui,
        
        # Robot
        robot_state_publisher,
        
        # Sensors
        rgb_camera_node,
        depth_camera_node,
        
        # Brain OS
        brain_ros2_bridge,
        
        # # RViz (commented out by default)
        # rviz2_node,
    ])
