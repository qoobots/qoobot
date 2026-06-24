#!/usr/bin/env python3
# brain_core.launch.py — Launch all brain_core lifecycle nodes
#
# Usage: ros2 launch brain_core brain_core.launch.py

import os
from launch import LaunchDescription
from launch_ros.actions import LifecycleNode
from launch.actions import DeclareLaunchArgument, GroupAction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition


def generate_launch_description():
    # ── Launch arguments ────────────────────────────────────
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    robot_model  = LaunchConfiguration('robot_model', default='kinova_gen3')
    config_dir   = LaunchConfiguration('config_dir',
        default=os.path.join(
            os.path.dirname(__file__), '..', 'config'
        ))

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time', default_value='true',
        description='Use simulation (Gazebo) time')

    declare_robot_model = DeclareLaunchArgument(
        'robot_model', default_value='kinova_gen3',
        description='Robot model: kinova_gen3 | turtlebot4')

    declare_config_dir = DeclareLaunchArgument(
        'config_dir', default_value=config_dir,
        description='Path to brain_core config directory')

    # ── Node definitions (stubs for Phase 1) ────────────────
    # In real deployment, these are LifecycleNode instances
    # For Sprint 1, we define the launch structure

    control_node = LifecycleNode(
        package='brain_core',
        executable='brain_core_node',
        name='control',
        namespace='brain_core',
        parameters=[os.path.join(config_dir, 'brain_core.yaml')],
        output='screen',
    )

    safety_node = LifecycleNode(
        package='brain_core',
        executable='brain_core_node',
        name='safety',
        namespace='brain_core',
        parameters=[
            os.path.join(config_dir, 'brain_core.yaml'),
            os.path.join(config_dir, 'safety', 'collision_zones.yaml'),
            os.path.join(config_dir, 'safety', 'force_limits.yaml'),
        ],
        output='screen',
    )

    perception_node = LifecycleNode(
        package='brain_core',
        executable='brain_core_node',
        name='perception',
        namespace='brain_core',
        parameters=[os.path.join(config_dir, 'brain_core.yaml')],
        output='screen',
    )

    behavior_node = LifecycleNode(
        package='brain_core',
        executable='brain_core_node',
        name='behavior',
        namespace='brain_core',
        parameters=[os.path.join(config_dir, 'brain_core.yaml')],
        output='screen',
    )

    grpc_bridge_node = LifecycleNode(
        package='brain_core',
        executable='brain_core_node',
        name='grpc_bridge',
        namespace='brain_core',
        parameters=[os.path.join(config_dir, 'brain_core.yaml')],
        output='screen',
    )

    return LaunchDescription([
        declare_use_sim_time,
        declare_robot_model,
        declare_config_dir,

        # Start nodes with staggered delays for orderly lifecycle
        TimerAction(period=0.0, actions=[control_node]),
        TimerAction(period=1.0, actions=[safety_node]),
        TimerAction(period=2.0, actions=[perception_node]),
        TimerAction(period=3.0, actions=[behavior_node]),
        TimerAction(period=4.0, actions=[grpc_bridge_node]),
    ])
