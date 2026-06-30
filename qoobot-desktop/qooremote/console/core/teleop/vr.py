"""VR 遥控接口 — VR 头显第一人称遥操作

提供统一的 VR 控制器抽象接口，支持：
- 头显位姿追踪 (6DOF)
- 手部控制器位姿追踪 (左右手)
- 按键/扳机/摇杆输入
- 手部关节追踪 (可选)

设备插件通过继承 VrInterface 实现具体硬件接入。

对应功能 TEL-05（VR 沉浸式遥控）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VrButton(str, Enum):
    """VR 控制器按键"""
    TRIGGER = "trigger"          # 扳机
    GRIP = "grip"                # 握持
    A = "a"
    B = "b"
    X = "x"
    Y = "y"
    THUMBSTICK = "thumbstick"    # 摇杆按下
    MENU = "menu"
    SYSTEM = "system"


class VrHand(str, Enum):
    LEFT = "left"
    RIGHT = "right"


@dataclass
class VrPose:
    """VR 设备 6DOF 位姿"""
    position: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)  # 四元数 (w,x,y,z)
    linear_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: tuple[float, float, float] = (0.0, 0.0, 0.0)
    timestamp: float = 0.0
    valid: bool = True


@dataclass
class VrControllerState:
    """VR 控制器完整状态"""
    hand: VrHand = VrHand.RIGHT
    pose: VrPose = field(default_factory=VrPose)
    trigger_value: float = 0.0       # 扳机轴 [0, 1]
    grip_value: float = 0.0          # 握持轴 [0, 1]
    thumbstick: tuple[float, float] = (0.0, 0.0)  # 摇杆 (x, y)
    trackpad: tuple[float, float] = (0.0, 0.0)    # 触控板
    buttons: dict[VrButton, bool] = field(default_factory=dict)
    # 手指追踪（可选，Meta Quest 支持）
    finger_curl: dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0

    def is_button_pressed(self, button: VrButton) -> bool:
        return self.buttons.get(button, False)


@dataclass
class VrHmdState:
    """头显完整状态"""
    pose: VrPose = field(default_factory=VrPose)
    left_eye_pose: VrPose = field(default_factory=VrPose)
    right_eye_pose: VrPose = field(default_factory=VrPose)
    ipd_mm: float = 63.0            # 瞳距 (mm)
    fov: tuple[float, float] = (90.0, 90.0)  # (水平, 垂直) 视野角
    is_mounted: bool = False        # 是否佩戴中
    timestamp: float = 0.0


@dataclass
class VrFrame:
    """VR 完整帧数据"""
    timestamp: float = field(default_factory=time.time)
    hmd: VrHmdState = field(default_factory=VrHmdState)
    left_controller: VrControllerState = field(default_factory=lambda: VrControllerState(hand=VrHand.LEFT))
    right_controller: VrControllerState = field(default_factory=lambda: VrControllerState(hand=VrHand.RIGHT))
    tracking_quality: float = 1.0    # 追踪质量 [0, 1]


class VrInterface:
    """VR 设备统一接口

    所有 VR 设备插件必须实现此接口。
    提供轮询式状态获取，适合桌面/非实时渲染场景。

    对应功能 TEL-05（VR 沉浸式遥控）。
    """

    # 设备标识
    device_name: str = "generic_vr"
    device_vendor: str = "unknown"
    supports_finger_tracking: bool = False
    supports_eye_tracking: bool = False

    def __init__(self) -> None:
        self._connected: bool = False
        self._latest_frame = VrFrame()
        self._on_connected_callbacks: list[callable] = []    # type: ignore
        self._on_disconnected_callbacks: list[callable] = []  # type: ignore

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def latest_frame(self) -> VrFrame:
        return self._latest_frame

    # --- 生命周期 ---

    def connect(self) -> bool:
        """连接 VR 设备"""
        raise NotImplementedError

    def disconnect(self) -> None:
        """断开 VR 设备"""
        raise NotImplementedError

    def poll(self) -> Optional[VrFrame]:
        """轮询最新帧数据

        Returns:
            VrFrame 或 None（无新数据时）
        """
        raise NotImplementedError

    # --- 回调 ---

    def on_connected(self, callback: callable) -> None:  # type: ignore
        self._on_connected_callbacks.append(callback)

    def on_disconnected(self, callback: callable) -> None:  # type: ignore
        self._on_disconnected_callbacks.append(callback)

    def _notify_connected(self) -> None:
        self._connected = True
        for cb in self._on_connected_callbacks:
            cb()

    def _notify_disconnected(self) -> None:
        self._connected = False
        for cb in self._on_disconnected_callbacks:
            cb()

    # --- 触觉反馈 ---

    def haptic_pulse(self, hand: VrHand, duration_ms: float = 100,
                     amplitude: float = 0.5) -> None:
        """发送触觉脉冲"""
        pass

    # --- 属性访问 ---

    def get_hmd_position(self) -> Optional[tuple[float, float, float]]:
        """获取头显世界位置"""
        if self._latest_frame.hmd.pose.valid:
            return self._latest_frame.hmd.pose.position
        return None

    def get_controller_position(self, hand: VrHand) -> Optional[tuple[float, float, float]]:
        """获取控制器世界位置"""
        ctrl = (self._latest_frame.left_controller if hand == VrHand.LEFT
                else self._latest_frame.right_controller)
        if ctrl.pose.valid:
            return ctrl.pose.position
        return None


class VrTeleopBridge:
    """VR→机器人遥操作桥接

    将 VR 控制器位姿/按键转换为机器人控制指令。
    支持两种模式：
    - 末端控制：VR 手部位置直接映射到机器人末端执行器
    - 关节映射：VR 手部关节对应机器人关节角度

    对应功能 TEL-05（VR 沉浸式遥控）。
    """

    class ControlMode(str, Enum):
        END_EFFECTOR = "end_effector"   # 末端位姿跟随
        JOINT_MIRROR = "joint_mirror"   # 关节镜像映射
        BOTH = "both"                   # 双模式（左手=关节，右手=末端）

    def __init__(self) -> None:
        self._mode: VrTeleopBridge.ControlMode = VrTeleopBridge.ControlMode.END_EFFECTOR
        self._workspace_scale: float = 1.0              # 工作空间缩放
        self._position_deadzone: float = 0.01           # 位置死区 (m)
        self._rotation_deadzone: float = 1.0            # 旋转死区 (度)

        # 左右手分工
        self._left_ctrl_target = VrHand.LEFT
        self._right_ctrl_target = VrHand.RIGHT

    @property
    def mode(self) -> ControlMode:
        return self._mode

    @mode.setter
    def mode(self, m: ControlMode) -> None:
        self._mode = m

    def compute_end_effector_target(
        self, frame: VrFrame, hand: VrHand
    ) -> dict:
        """从 VR 控制器计算末端执行器目标

        Returns:
            {"position": (x,y,z), "rotation": (w,x,y,z),
             "gripper": 0~1, "timestamp": float}
        """
        ctrl = frame.left_controller if hand == VrHand.LEFT else frame.right_controller
        if not ctrl.pose.valid:
            return {}

        pos = ctrl.pose.position
        # 位置缩放
        scaled_pos = (
            pos[0] * self._workspace_scale,
            pos[1] * self._workspace_scale,
            pos[2] * self._workspace_scale,
        )
        # 死区
        if all(abs(p) < self._position_deadzone for p in scaled_pos):
            return {}

        return {
            "position": scaled_pos,
            "rotation": ctrl.pose.rotation,
            "gripper": ctrl.trigger_value,    # 扳机=夹爪开合
            "timestamp": ctrl.timestamp,
        }

    def compute_joint_targets(
        self, frame: VrFrame, hand: VrHand
    ) -> dict[str, float]:
        """从 VR 控制器计算关节目标角度

        Returns:
            {joint_name: angle_rad, ...}
        """
        ctrl = frame.left_controller if hand == VrHand.LEFT else frame.right_controller

        targets: dict[str, float] = {}

        # 手腕旋转 → 末端 roll/pitch/yaw
        if ctrl.pose.valid:
            rot = self._quaternion_to_euler(ctrl.pose.rotation)
            targets["wrist_roll"] = rot[0]
            targets["wrist_pitch"] = rot[1]
            targets["wrist_yaw"] = rot[2]

        # 手指弯曲（如果支持）
        for finger, curl in ctrl.finger_curl.items():
            targets[f"finger_{finger}"] = curl

        # 摇杆 → 腕部平移
        sx, sy = ctrl.thumbstick
        if abs(sx) > 0.1 or abs(sy) > 0.1:
            targets["wrist_x"] = sx * 0.05
            targets["wrist_y"] = sy * 0.05

        return targets

    @staticmethod
    def _quaternion_to_euler(q: tuple[float, float, float, float]) -> tuple[float, float, float]:
        """四元数 → 欧拉角 (roll, pitch, yaw) 弧度"""
        import math
        w, x, y, z = q
        # roll (x-axis rotation)
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        # pitch (y-axis rotation)
        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)
        # yaw (z-axis rotation)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        return (roll, pitch, yaw)
