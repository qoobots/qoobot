"""Tests for simulation bridge layer."""

from __future__ import annotations

import numpy as np

from qoodev.sim_bridge.interface import (
    SimConfig,
    SimScene,
    SimRobot,
    SimState,
    SensorType,
    ControlMode,
    SimControlCommand,
    SimStats,
)


def test_sim_config_defaults():
    """SimConfig has sensible defaults."""
    config = SimConfig()
    assert config.backend == "mujoco"
    assert config.headless is False
    assert config.real_time is True
    assert config.time_step == 0.001
    assert config.gravity == (0.0, 0.0, -9.81)


def test_sim_config_custom():
    """SimConfig accepts custom values."""
    config = SimConfig(
        backend="isaac_sim",
        headless=True,
        real_time=False,
        time_step=0.005,
        render_width=640,
        render_height=480,
    )
    assert config.backend == "isaac_sim"
    assert config.headless is True
    assert config.real_time is False
    assert config.render_width == 640


def test_sim_scene_creation():
    """SimScene can be created with robots."""
    robot = SimRobot(
        name="test_robot",
        model_path="robots/test.xml",
        base_position=(1.0, 2.0, 0.0),
    )
    scene = SimScene(
        name="test_scene",
        description="A test scene",
        robots=[robot],
    )
    assert scene.name == "test_scene"
    assert len(scene.robots) == 1
    assert scene.robots[0].name == "test_robot"


def test_sim_state_enum():
    """SimState enum values are distinct."""
    states = list(SimState)
    assert len(states) >= 6
    assert SimState.UNINITIALIZED != SimState.RUNNING


def test_sensor_type_enum():
    """SensorType enum has expected members."""
    assert SensorType.RGB_CAMERA.value == "rgb_camera"
    assert SensorType.LIDAR.value == "lidar"
    assert SensorType.IMU.value == "imu"


def test_control_mode_enum():
    """ControlMode enum has expected members."""
    assert ControlMode.POSITION.value == "position"
    assert ControlMode.VELOCITY.value == "velocity"
    assert ControlMode.TORQUE.value == "torque"


def test_control_command():
    """SimControlCommand creation."""
    targets = np.array([0.5, -0.3, 0.1])
    cmd = SimControlCommand(
        robot_name="test_robot",
        control_mode=ControlMode.POSITION,
        targets=targets,
        joint_names=["joint_1", "joint_2", "joint_3"],
    )
    assert cmd.robot_name == "test_robot"
    assert cmd.control_mode == ControlMode.POSITION
    assert len(cmd.targets) == 3


def test_sim_stats_defaults():
    """SimStats starts with zero values."""
    stats = SimStats()
    assert stats.real_time_factor == 1.0
    assert stats.total_steps == 0
    assert stats.total_time == 0.0
