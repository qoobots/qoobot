#!/usr/bin/env python3
# ============================================================================
# QooBot MuJoCo Simulation Launch
# 对标: unitree_ros-master unitree_gazebo/launch/normal.launch
#
# 用法: ros2 launch qoobot_description sim_mujoco.launch.py
# ============================================================================
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('qoobot_description')
    urdf_file = os.path.join(pkg_dir, 'urdf', 'qoobot.urdf.xacro')
    rviz_config = os.path.join(pkg_dir, 'rviz', 'qoobot.rviz')
    joint_ctrl_yaml = os.path.join(pkg_dir, 'config', 'joint_control.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Gazebo) clock if true'
        ),

        # Robot State Publisher
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': ['xacro ', urdf_file],
                'publish_frequency': 200.0,
                'use_sim_time': use_sim_time,
            }]
        ),

        # Joint State Publisher
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            name='joint_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'source_list': ['/joint_states'],
            }]
        ),

        # RViz
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': use_sim_time}],
        ),
    ])
