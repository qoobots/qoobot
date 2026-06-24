"""运动规划与控制数据类型。

包括关节状态、轨迹、运动指令、夹爪控制等。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from brain_os.types.common import Pose


class MotionStatus(Enum):
    """运动执行状态。"""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    STOPPED = "stopped"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GripperCommand(Enum):
    """夹爪指令。"""

    OPEN = "open"
    CLOSE = "close"
    SET_POSITION = "set_position"
    SET_FORCE = "set_force"


@dataclass
class JointLimits:
    """关节限位。

    Attributes:
        lower: 下限 (弧度或米)
        upper: 上限 (弧度或米)
        max_velocity: 最大速度
        max_effort: 最大力矩 (Nm 或 N)
    """

    lower: float = 0.0
    upper: float = 0.0
    max_velocity: float = 0.0
    max_effort: float = 0.0


@dataclass
class JointState:
    """单关节状态。

    Attributes:
        name: 关节名称
        position: 当前位置 (弧度或米)
        velocity: 当前速度
        effort: 当前力矩
        limits: 关节限位
    """

    name: str = ""
    position: float = 0.0
    velocity: float = 0.0
    effort: float = 0.0
    limits: Optional[JointLimits] = None


@dataclass
class CartesianPath:
    """笛卡尔空间路径。

    Attributes:
        waypoints: 路径点列表 (每项为 (x, y, z, roll, pitch, yaw))
        frame_id: 参考坐标系
        max_velocity: 最大线速度 (m/s)
        max_acceleration: 最大线加速度 (m/s^2)
    """

    waypoints: List[Tuple[float, float, float, float, float, float]] = field(default_factory=list)
    frame_id: str = "base_link"
    max_velocity: float = 0.5
    max_acceleration: float = 1.0


@dataclass
class TrajectoryPoint:
    """轨迹点。

    Attributes:
        time_from_start_sec: 从起点开始的持续时间 (秒)
        joint_positions: 关节角度列表 (弧度)
        joint_velocities: 关节速度列表
        ee_pose: 末端执行器位姿 (可选)
    """

    time_from_start_sec: float = 0.0
    joint_positions: List[float] = field(default_factory=list)
    joint_velocities: Optional[List[float]] = None
    ee_pose: Optional[Pose] = None


@dataclass
class Trajectory:
    """完整轨迹。

    Attributes:
        id: 轨迹唯一标识
        points: 轨迹点序列
        total_duration_sec: 总执行时间 (秒)
        is_recommended: 是否为推荐轨迹 (HITL)
        metadata: 轨迹元数据 (cost, smoothness, etc.)
    """

    id: str = ""
    points: List[TrajectoryPoint] = field(default_factory=list)
    total_duration_sec: float = 0.0
    is_recommended: bool = False
    metadata: Dict[str, float] = field(default_factory=dict)


@dataclass
class MotionCommand:
    """运动指令。

    Attributes:
        type: 指令类型 ("joint", "cartesian", "gripper", "stop")
        joint_targets: 目标关节值
        cartesian_target: 笛卡尔空间目标位姿
        gripper_position: 夹爪位置 (0=关闭, 1=打开)
        velocity_scale: 速度倍率 (0.0-1.0)
        timeout_sec: 指令超时
    """

    type: str = ""
    joint_targets: Optional[List[float]] = None
    cartesian_target: Optional[Pose] = None
    gripper_position: float = 0.0
    velocity_scale: float = 1.0
    timeout_sec: float = 10.0
