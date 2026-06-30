"""键盘输入映射 — WASD 键盘到控制指令的转换

将键盘按键映射为机器人控制指令。
支持增量式移动（按键持续时间越长，位移越大）。

使用原始键码（与 Qt.Key 兼容），不依赖任何 GUI 框架。

对应功能 TEL-01（手柄/键盘遥控）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from console.core.teleop.controller import (
    GripperCommand,
    JointCommand,
    JointTarget,
    TeleopCommand,
    ControlMode,
    Pose,
)


# ------------------------------------------------------------------
# 键盘键码常量（与 Qt.Key 兼容，无需 PySide6 依赖）
# ------------------------------------------------------------------

class KeyCode:
    """平台无关的键盘键码常量"""
    # 字母键
    W = 87
    A = 65
    S = 83
    D = 68
    Q = 81
    E = 69
    R = 82
    F = 70
    Z = 90
    C = 67
    # 数字键
    K_1 = 49
    K_2 = 50
    # 功能键
    Space = 32
    Tab = 9
    # 方向键
    Up = 16777235
    Down = 16777237
    Left = 16777234
    Right = 16777236


# ------------------------------------------------------------------
# 键盘映射配置
# ------------------------------------------------------------------

@dataclass
class KeyboardMapping:
    """键盘到控制指令的映射配置

    默认 WASD + QE 布局：
    - WASD: 平移 X/Y
    - Q/E: 旋转 Yaw
    - R/F: 升降 Z
    - Z/C: 旋转 Roll
    - 1/2: 夹爪开/关
    - Space: 紧急制动
    - Tab: 模式切换
    - 方向键: 关节微调
    """
    # 平移
    key_forward: int = KeyCode.W       # +X
    key_backward: int = KeyCode.S      # -X
    key_left: int = KeyCode.A          # +Y
    key_right: int = KeyCode.D         # -Y
    key_up: int = KeyCode.R            # +Z
    key_down: int = KeyCode.F          # -Z

    # 旋转
    key_yaw_left: int = KeyCode.Q      # +Yaw
    key_yaw_right: int = KeyCode.E     # -Yaw
    key_roll_left: int = KeyCode.Z     # +Roll
    key_roll_right: int = KeyCode.C    # -Roll

    # 夹爪
    key_gripper_open: int = KeyCode.K_1
    key_gripper_close: int = KeyCode.K_2

    # 紧急操作
    key_emergency_stop: int = KeyCode.Space
    key_mode_switch: int = KeyCode.Tab

    # 微调控制（方向键对应关节目标微调）
    key_joint_plus: int = KeyCode.Up
    key_joint_minus: int = KeyCode.Down
    key_joint_next: int = KeyCode.Right
    key_joint_prev: int = KeyCode.Left

    # 灵敏度
    translate_step: float = 0.01          # 每帧平移步长 (m)
    rotate_step: float = 0.02             # 每帧旋转步长 (rad)
    joint_step: float = 0.01              # 关节微调步长 (rad)

    # 重复率
    max_command_rate_hz: float = 50.0     # 最大指令发送频率


class KeyboardDriver:
    """键盘驱动

    将键盘按键状态转换为遥操作指令。
    通过 QTimer 以固定频率轮询当前按键状态，生成增量式控制指令。
    """

    def __init__(self, mapping: KeyboardMapping | None = None) -> None:
        self._mapping = mapping or KeyboardMapping()
        self._active = False
        self._pressed_keys: set[int] = set()
        self._on_teleop: callable | None = None  # type: ignore
        self._on_emergency: callable | None = None  # type: ignore

        # 关节微调状态
        self._selected_joint: int = 0
        self._num_joints: int = 28          # 默认 28 DOF

    def set_teleop_callback(self, callback: callable) -> None:  # type: ignore
        self._on_teleop = callback

    def set_emergency_callback(self, callback: callable) -> None:  # type: ignore
        self._on_emergency = callback

    def set_joint_count(self, count: int) -> None:
        self._num_joints = count

    def press_key(self, key: int) -> None:
        """按下按键"""
        if key not in self._pressed_keys:
            self._pressed_keys.add(key)
            self._handle_edge_trigger(key)

    def release_key(self, key: int) -> None:
        """释放按键"""
        self._pressed_keys.discard(key)

    def is_pressed(self, key: int) -> bool:
        return key in self._pressed_keys

    def get_pose_delta(self) -> Pose:
        """根据当前按住的键计算位姿增量"""
        m = self._mapping
        delta = Pose()

        # 平移
        if self.is_pressed(m.key_forward):
            delta.x += m.translate_step
        if self.is_pressed(m.key_backward):
            delta.x -= m.translate_step
        if self.is_pressed(m.key_left):
            delta.y += m.translate_step
        if self.is_pressed(m.key_right):
            delta.y -= m.translate_step
        if self.is_pressed(m.key_up):
            delta.z += m.translate_step
        if self.is_pressed(m.key_down):
            delta.z -= m.translate_step

        # 旋转
        if self.is_pressed(m.key_yaw_left):
            delta.yaw += m.rotate_step
        if self.is_pressed(m.key_yaw_right):
            delta.yaw -= m.rotate_step
        if self.is_pressed(m.key_roll_left):
            delta.roll += m.rotate_step
        if self.is_pressed(m.key_roll_right):
            delta.roll -= m.rotate_step

        return delta

    def get_joint_target(self, joint_id: int) -> Optional[JointTarget]:
        """获取指定关节的目标值"""
        m = self._mapping
        if joint_id != self._selected_joint:
            return None

        delta = 0.0
        if self.is_pressed(m.key_joint_plus):
            delta += m.joint_step
        if self.is_pressed(m.key_joint_minus):
            delta -= m.joint_step

        if abs(delta) < 0.0001:
            return None

        return JointTarget(id=joint_id, position=delta)

    def get_gripper_command(self) -> GripperCommand:
        """获取夹爪指令"""
        if self.is_pressed(self._mapping.key_gripper_open):
            return GripperCommand.OPEN
        if self.is_pressed(self._mapping.key_gripper_close):
            return GripperCommand.CLOSE
        return GripperCommand.STOP

    def _handle_edge_trigger(self, key: int) -> None:
        """处理边缘触发的按键（如紧急制动）"""
        if key == self._mapping.key_emergency_stop:
            if self._on_emergency:
                self._on_emergency("keyboard")
        elif key == self._mapping.key_joint_next:
            self._selected_joint = min(self._selected_joint + 1, self._num_joints - 1)
        elif key == self._mapping.key_joint_prev:
            self._selected_joint = max(self._selected_joint - 1, 0)

    @property
    def selected_joint(self) -> int:
        """当前选中的关节 ID"""
        return self._selected_joint

    @property
    def active(self) -> bool:
        return len(self._pressed_keys) > 0
