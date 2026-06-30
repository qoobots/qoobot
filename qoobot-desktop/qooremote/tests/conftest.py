"""pytest 配置 — qooremote 测试"""

import pytest
from unittest.mock import Mock, AsyncMock


@pytest.fixture
def mock_robot_state():
    """提供模拟的机器人状态数据"""
    from console.core.models.robot_state import (
        RobotState, RobotStatus, PowerInfo, ImuData, Quaternion, Vector3,
    )
    from console.core.models.joint_state import JointState
    from console.core.models.alert import Alert, AlertLevel, AlertType

    return RobotState(
        timestamp=1719700000000,
        sequence=1,
        robot_id="qoobot-test-01",
        status=RobotStatus(
            cpu_percent=45.2,
            memory_used_mb=2048.0,
            memory_total_mb=8192.0,
        ),
        power=PowerInfo(
            battery_percent=67.0,
            charging=False,
            voltage=48.2,
            current_amps=12.5,
            power_watts=602.5,
            estimated_runtime_minutes=45.0,
        ),
        joints=[
            JointState(name="left_shoulder_pitch", id=0, position_rad=0.523,
                       velocity_rad_s=0.12, torque_nm=1.5,
                       temperature_celsius=41.2, current_amps=3.2),
            JointState(name="left_elbow", id=1, position_rad=-0.314,
                       velocity_rad_s=-0.08, torque_nm=0.8,
                       temperature_celsius=38.5, current_amps=1.8),
        ],
        imu=ImuData(),
        forces=[],
        alerts=[Alert.create(AlertLevel.WARNING, AlertType.BATTERY_LOW, "电量低于 20%", "test")],
    )


@pytest.fixture
def alert_manager():
    """提供告警管理器"""
    from console.core.models.alert import AlertManager
    return AlertManager()


@pytest.fixture
def signaling_client():
    """提供信令客户端"""
    from console.core.signaling.client import SignalingClient
    return SignalingClient()
