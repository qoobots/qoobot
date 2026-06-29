#!/usr/bin/env python3
"""
============================================================================
QooBody ROS Bridge Launch — 启动全部桥接节点
============================================================================

用法: ros2 launch qoobody_ros_bridge bridge.launch.py
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
            executable='foot_contact_publisher.py',
            name='foot_contact_publisher',
            output='screen',
        ),
    ])
