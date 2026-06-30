"""遥操作控制器 — 控制指令生成与发送

定义所有遥控类型的命令数据类，负责：
- 末端位姿控制 (TEL-02: 6 DOF 末端执行器精确位姿控制)
- 关节空间控制 (TEL-03: 单关节/多关节位置/速度/力矩控制)
- 模式切换 (TAK-01: 自主↔半自主↔全手动模式切换)
- 紧急制动 (TAK-02: 一键紧急接管+紧急制动)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class ControlMode(str, Enum):
    """控制模式"""
    END_EFFECTOR = "end_effector"   # 末端位姿控制
    JOINT_POSITION = "position"     # 关节位置控制
    JOINT_VELOCITY = "velocity"     # 关节速度控制
    JOINT_TORQUE = "torque"         # 关节力矩控制


class GripperCommand(str, Enum):
    """夹爪指令"""
    OPEN = "open"
    CLOSE = "close"
    STOP = "stop"
    GRASP = "grasp"                 # 力控抓取


@dataclass
class Pose:
    """6D 位姿"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

    @property
    def position(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z], dtype=np.float64)

    @property
    def orientation_euler(self) -> np.ndarray:
        return np.array([self.roll, self.pitch, self.yaw], dtype=np.float64)

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "orientation": {"roll": self.roll, "pitch": self.pitch, "yaw": self.yaw},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pose:
        pos = data.get("position", {})
        ori = data.get("orientation", {})
        return cls(
            x=float(pos.get("x", 0)), y=float(pos.get("y", 0)),
            z=float(pos.get("z", 0)),
            roll=float(ori.get("roll", 0)), pitch=float(ori.get("pitch", 0)),
            yaw=float(ori.get("yaw", 0)),
        )


@dataclass
class JointTarget:
    """单关节目标值"""
    id: int = 0
    position: float = 0.0           # 目标位置 (rad)
    velocity_limit: float = 2.0     # 速度限制 (rad/s)
    torque_limit: float = 50.0      # 力矩限制 (Nm)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "position": self.position,
            "velocity_limit": self.velocity_limit,
            "torque_limit": self.torque_limit,
        }


@dataclass
class TeleopCommand:
    """遥操作指令 (末端位姿控制)

    对应功能 TEL-02。
    """
    timestamp: int = 0
    sequence: int = 0
    mode: ControlMode = ControlMode.END_EFFECTOR
    target_frame: str = ""           # 目标坐标系, e.g. "left_hand"
    pose: Pose = field(default_factory=Pose)
    gripper: GripperCommand = GripperCommand.STOP
    gripper_force_limit: float = 20.0
    velocity_limit: float = 0.5
    acceleration_limit: float = 1.0
    emergency: bool = False

    def __post_init__(self) -> None:
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "teleop_command",
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "mode": self.mode.value,
            "target": {
                "frame": self.target_frame,
                "pose": self.pose.to_dict(),
                "velocity_limit": self.velocity_limit,
                "acceleration_limit": self.acceleration_limit,
            },
            "gripper": {
                "command": self.gripper.value,
                "force_limit_n": self.gripper_force_limit,
            },
            "emergency": self.emergency,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class JointCommand:
    """关节空间控制指令

    对应功能 TEL-03。
    """
    timestamp: int = 0
    sequence: int = 0
    mode: ControlMode = ControlMode.JOINT_POSITION
    joints: list[JointTarget] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "joint_command",
            "timestamp": self.timestamp,
            "sequence": self.sequence,
            "mode": self.mode.value,
            "joints": [j.to_dict() for j in self.joints],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class ModeSwitchCommand:
    """模式切换指令

    对应功能 TAK-01。
    """
    from_mode: str = "autonomous"
    to_mode: str = "manual"
    reason: str = "operator_takeover"
    operator_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "mode_switch",
            "from": self.from_mode,
            "to": self.to_mode,
            "reason": self.reason,
            "operator_id": self.operator_id,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class EmergencyStopCommand:
    """紧急制动指令

    对应功能 TAK-02。
    """
    timestamp: int = 0
    reason: str = "operator"
    stop_type: str = "hard"          # hard = 立即断电, soft = 减速停止

    def __post_init__(self) -> None:
        if self.timestamp == 0:
            self.timestamp = int(time.time() * 1000)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "emergency_stop",
            "timestamp": self.timestamp,
            "reason": self.reason,
            "stop_type": self.stop_type,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class TeleopController:
    """遥操作控制器

    管理遥操作命令的生成、平滑处理和发送。
    作为手柄/键盘输入到网络指令的桥梁。
    """

    def __init__(self) -> None:
        self._sequence = 0
        self._active = False
        self._send_callback: callable | None = None  # type: ignore

    @property
    def active(self) -> bool:
        return self._active

    def set_send_callback(self, callback: callable) -> None:  # type: ignore
        """设置指令发送回调"""
        self._send_callback = callback

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence

    async def send_teleop(self, command: TeleopCommand) -> None:
        """发送遥操作指令"""
        command.sequence = self._next_sequence()
        if self._send_callback:
            await self._send_callback(command.to_dict())

    async def send_joint_command(self, command: JointCommand) -> None:
        """发送关节指令"""
        command.sequence = self._next_sequence()
        if self._send_callback:
            await self._send_callback(command.to_dict())

    async def send_emergency_stop(self, reason: str = "operator") -> None:
        """发送紧急制动指令"""
        cmd = EmergencyStopCommand(reason=reason)
        if self._send_callback:
            await self._send_callback(cmd.to_dict())

    async def send_mode_switch(self, to_mode: str, reason: str = "operator") -> None:
        """发送模式切换指令"""
        cmd = ModeSwitchCommand(to_mode=to_mode, reason=reason)
        if self._send_callback:
            await self._send_callback(cmd.to_dict())
