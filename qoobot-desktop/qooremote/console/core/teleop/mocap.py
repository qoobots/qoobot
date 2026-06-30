"""动作捕捉遥操作接口 — 动捕设备到机器人运动映射

对应功能 TEL-04（动作捕捉遥操作）。

支持的动捕系统：
- OptiTrack (Motive)
- Xsens (MVN)
- 通用 OSC 协议
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

import numpy as np

from console.core.teleop.controller import TeleopCommand, ControlMode, Pose, JointTarget

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 动捕数据模型
# ------------------------------------------------------------------

class MocapSystem(Enum):
    """动捕系统类型"""
    OPTITRACK = "optitrack"
    XSENS = "xsens"
    OSC_GENERIC = "osc_generic"


@dataclass
class SkeletonBone:
    """骨骼节点"""
    name: str
    position: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # [x, y, z]
    rotation: list[float] = field(default_factory=lambda: [1.0, 0.0, 0.0, 0.0])  # [qw, qx, qy, qz]
    parent: Optional[str] = None

    def get_pos_array(self) -> np.ndarray:
        return np.array(self.position, dtype=np.float32)

    def get_rot_quat(self) -> np.ndarray:
        return np.array(self.rotation, dtype=np.float32)


@dataclass
class MocapFrame:
    """动捕帧 — 一帧完整的动捕数据"""
    timestamp: float = 0.0
    frame_index: int = 0
    bones: dict[str, SkeletonBone] = field(default_factory=dict)
    markers: list[list[float]] = field(default_factory=list)  # [[x, y, z], ...]

    def get_bone(self, name: str) -> Optional[SkeletonBone]:
        return self.bones.get(name)


# ------------------------------------------------------------------
# 骨骼映射
# ------------------------------------------------------------------

@dataclass
class BoneMapping:
    """动捕骨骼 → 机器人关节映射规则"""
    mocap_bone: str         # 动捕骨骼名
    robot_joint: str        # 机器人关节名
    scale: float = 1.0      # 缩放因子
    offset: float = 0.0     # 偏移量 (rad)
    use_rotation: bool = False  # True=使用旋转, False=使用位置
    axis: int = 0           # 使用哪个轴 (0=X, 1=Y, 2=Z)


# 预定义的人形机器人映射
HUMANOID_DEFAULT_MAPPING: list[BoneMapping] = [
    # 上半身
    BoneMapping("RightUpperArm", "shoulder_pitch_r", scale=1.0, use_rotation=True, axis=0),
    BoneMapping("RightUpperArm", "shoulder_roll_r", scale=1.0, use_rotation=True, axis=2),
    BoneMapping("RightForeArm", "elbow_r", scale=1.0, use_rotation=True, axis=0),
    BoneMapping("RightHand", "wrist_pitch_r", scale=0.5, use_rotation=True, axis=0),
    BoneMapping("RightHand", "wrist_roll_r", scale=0.5, use_rotation=True, axis=2),
    # 左半身
    BoneMapping("LeftUpperArm", "shoulder_pitch_l", scale=1.0, use_rotation=True, axis=0),
    BoneMapping("LeftUpperArm", "shoulder_roll_l", scale=-1.0, use_rotation=True, axis=2),
    BoneMapping("LeftForeArm", "elbow_l", scale=1.0, use_rotation=True, axis=0),
    BoneMapping("LeftHand", "wrist_pitch_l", scale=0.5, use_rotation=True, axis=0),
    BoneMapping("LeftHand", "wrist_roll_l", scale=-0.5, use_rotation=True, axis=2),
    # 头部
    BoneMapping("Head", "neck_pitch", scale=0.5, use_rotation=True, axis=0),
    BoneMapping("Head", "neck_yaw", scale=0.5, use_rotation=True, axis=2),
]


# ------------------------------------------------------------------
# 动捕接口
# ------------------------------------------------------------------

class MocapInterface:
    """动捕系统抽象接口

    统一不同动捕系统的数据接入，输出标准化的 MocapFrame。
    """

    def __init__(self, system: MocapSystem = MocapSystem.OSC_GENERIC) -> None:
        self._system = system
        self._connected = False
        self._latest_frame: Optional[MocapFrame] = None
        self._frame_count = 0

        # 回调
        self.on_frame: Optional[Callable[[MocapFrame], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None

    @property
    def system(self) -> MocapSystem:
        return self._system

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def latest_frame(self) -> Optional[MocapFrame]:
        return self._latest_frame

    def connect(self, **kwargs) -> bool:
        """连接动捕系统"""
        # 各系统子类实现具体连接逻辑
        self._connected = True
        logger.info("Mocap connected: %s", self._system.value)
        if self.on_connected:
            self.on_connected()
        return True

    def disconnect(self) -> None:
        """断开动捕系统"""
        self._connected = False
        logger.info("Mocap disconnected: %s", self._system.value)
        if self.on_disconnected:
            self.on_disconnected()

    def push_frame(self, frame: MocapFrame) -> None:
        """推送一帧动捕数据（由设备驱动调用）"""
        self._latest_frame = frame
        self._frame_count += 1
        if self.on_frame:
            self.on_frame(frame)


# ------------------------------------------------------------------
# 动捕→机器人映射引擎
# ------------------------------------------------------------------

class MocapToRobotMapper:
    """动捕数据到机器人控制指令的映射引擎

    根据骨骼映射规则，将 MocapFrame 转换为 TeleopCommand 或 JointCommand。
    """

    def __init__(self, mappings: Optional[list[BoneMapping]] = None) -> None:
        self._mappings = mappings or HUMANOID_DEFAULT_MAPPING

    def map_to_joint_targets(self, mocap_frame: MocapFrame) -> dict[str, JointTarget]:
        """将动捕帧映射为关节目标

        Args:
            mocap_frame: 动捕数据帧

        Returns:
            {joint_name: JointTarget} 字典
        """
        targets: dict[str, JointTarget] = {}

        for mapping in self._mappings:
            bone = mocap_frame.get_bone(mapping.mocap_bone)
            if bone is None:
                continue

            if mapping.use_rotation:
                quat = bone.get_rot_quat()
                value = self._quat_to_euler_axis(quat, mapping.axis)
            else:
                pos = bone.get_pos_array()
                value = pos[mapping.axis]

            angle = value * mapping.scale + mapping.offset
            targets[mapping.robot_joint] = JointTarget(
                position=angle,
            )

        return targets

    @staticmethod
    def _quat_to_euler_axis(q: np.ndarray, axis: int) -> float:
        """从四元数提取指定轴的欧拉角分量"""
        w, x, y, z = q[0], q[1], q[2], q[3]
        if axis == 0:  # Pitch
            return float(np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
        elif axis == 1:  # Yaw
            return float(np.arcsin(np.clip(2 * (w * y - z * x), -1, 1)))
        else:  # Roll
            return float(np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))

    def set_mappings(self, mappings: list[BoneMapping]) -> None:
        """更新映射规则"""
        self._mappings = mappings
