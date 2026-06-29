"""遥控控制指令数据结构"""

from dataclasses import dataclass, field
from typing import List, Optional
from .enums import ControlMode, GripperType, StopType


@dataclass
class BaseCommand:
    """基座运动指令"""
    vx: float = 0.0       # 前进速度 (m/s)
    vy: float = 0.0       # 横向速度 (m/s)
    omega: float = 0.0    # 旋转速度 (rad/s)


@dataclass
class JointSetpoint:
    """关节目标点"""
    joint_name: str = ""
    position: float = 0.0       # 目标位置 (rad)
    velocity: float = 0.0       # 目标速度 (rad/s)
    torque_ff: float = 0.0      # 前馈力矩 (Nm)
    control_mode: ControlMode = ControlMode.POSITION


@dataclass
class GripperCommand:
    """末端执行器指令"""
    type: GripperType = GripperType.PARALLEL
    position: float = 0.0       # 开口宽度 (m)
    grasp_force: float = 0.0    # 抓取力 (N)
    suction_on: bool = False    # 吸盘开关


@dataclass
class HeadCommand:
    """头部/云台指令"""
    pitch: float = 0.0   # 俯仰角 (rad)
    yaw: float = 0.0     # 偏航角 (rad)
    roll: float = 0.0    # 滚转角 (rad)


@dataclass
class EmergencyStopCommand:
    """紧急停止指令"""
    stop_type: StopType = StopType.EMERGENCY
    reason: str = ""


@dataclass
class TeleopCommand:
    """全身运动遥控指令"""
    timestamp_ns: int = 0
    sequence: int = 0
    session_id: str = ""

    base: BaseCommand = field(default_factory=BaseCommand)
    joints: List[JointSetpoint] = field(default_factory=list)
    left_gripper: GripperCommand = field(default_factory=GripperCommand)
    right_gripper: GripperCommand = field(default_factory=GripperCommand)
    head: HeadCommand = field(default_factory=HeadCommand)

    control_mode: ControlMode = ControlMode.POSITION
    speed_override: float = 1.0   # 速度倍率 [0.0, 1.0]

    def to_dict(self) -> dict:
        """序列化为 JSON 字典 (用于 WebSocket 传输)"""
        return {
            "timestamp_ns": self.timestamp_ns,
            "sequence": self.sequence,
            "session_id": self.session_id,
            "base": {"vx": self.base.vx, "vy": self.base.vy, "omega": self.base.omega},
            "joints": [
                {
                    "joint_name": j.joint_name,
                    "position": j.position,
                    "velocity": j.velocity,
                    "torque_ff": j.torque_ff,
                    "control_mode": j.control_mode.value
                }
                for j in self.joints
            ],
            "left_gripper": {
                "type": self.left_gripper.type.value,
                "position": self.left_gripper.position,
                "grasp_force": self.left_gripper.grasp_force,
                "suction_on": self.left_gripper.suction_on
            },
            "right_gripper": {
                "type": self.right_gripper.type.value,
                "position": self.right_gripper.position,
                "grasp_force": self.right_gripper.grasp_force,
                "suction_on": self.right_gripper.suction_on
            },
            "head": {
                "pitch": self.head.pitch,
                "yaw": self.head.yaw,
                "roll": self.head.roll
            },
            "control_mode": self.control_mode.value,
            "speed_override": self.speed_override
        }
