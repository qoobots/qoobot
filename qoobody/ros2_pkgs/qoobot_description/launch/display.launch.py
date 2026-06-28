#!/usr/bin/env python3
# ============================================================================
# QooBot Display Launch — URDF 模型可视化 (RViz)
# 对标: unitree_ros-master robots/*_description/launch/display.launch
#
# 用法: ros2 launch qoobot_description display.launch.py
# ============================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('qoobot_description')
    urdf_file = os.path.join(pkg_dir, 'urdf', 'qoobot.urdf.xacro')
    rviz_config = os.path.join(pkg_dir, 'rviz', 'qoobot.rviz')

    # 可选: 使用 xacro 编译, 或直接使用预编译 URDF
    use_xacro = LaunchConfiguration('use_xacro', default='true')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_xacro',
            default_value='true',
            description='Whether to use xacro to process the URDF file'
        ),

        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': [
                    'xacro ', urdf_file
                ] if use_xacro else [urdf_file],
                'publish_frequency': 50.0,
                'use_sim_time': False,
            }]
        ),

        # Joint State Publisher GUI (for manual joint testing)
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
        ),
    ])
