#!/usr/bin/env python3
"""
============================================================================
QooBody Teleop Launch — 启动键盘遥控 + 桥接
============================================================================

用法: ros2 launch qoobody_ros_bridge teleop.launch.py
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='qoobody_ros_bridge',
            executable='sensor_bridge.py',
            name='sensor_bridge',
            output='screen',
        ),
        Node(
            package='qoobody_ros_bridge',
            executable='cmd_bridge.py',
            name='cmd_bridge',
            output='screen',
        ),
        Node(
            package='qoobody_ros_bridge',
            executable='teleop_keyboard.py',
            name='teleop_keyboard',
            output='screen',
            prefix='xterm -e',  # 需要独立终端窗口
        ),
    ])
