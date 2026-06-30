"""手柄输入映射 — Xbox / PlayStation 游戏手柄到控制指令的转换

将手柄物理输入（摇杆、按钮、扳机）映射为机器人控制指令。
支持 Xbox 和 PlayStation 手柄布局。

对应功能 TEL-01（手柄/键盘遥控）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from console.core.teleop.controller import (
    GripperCommand,
    JointTarget,
    TeleopCommand,
    ControlMode,
    Pose,
)
from console.core.utils.interpolation import deadzone, Smoother


# ------------------------------------------------------------------
# 手柄按钮/轴枚举
# ------------------------------------------------------------------

class GamepadButton:
    """标准手柄按钮映射"""
    A = 0
    B = 1
    X = 2
    Y = 3
    LB = 4          # Left Bumper
    RB = 5          # Right Bumper
    SELECT = 6
    START = 7
    L3 = 8          # Left Stick Press
    R3 = 9          # Right Stick Press
    D_UP = 10
    D_DOWN = 11
    D_LEFT = 12
    D_RIGHT = 13
    GUIDE = 14      # Xbox/PS 按钮


class GamepadAxis:
    """标准手柄轴映射"""
    LEFT_X = 0
    LEFT_Y = 1
    RIGHT_X = 2
    RIGHT_Y = 3
    LEFT_TRIGGER = 4
    RIGHT_TRIGGER = 5


@dataclass
class GamepadState:
    """手柄状态快照"""
    buttons: dict[int, bool] = field(default_factory=dict)
    axes: dict[int, float] = field(default_factory=dict)
    connected: bool = False

    def is_pressed(self, button: int) -> bool:
        return self.buttons.get(button, False)

    def get_axis(self, axis: int) -> float:
        return self.axes.get(axis, 0.0)


@dataclass
class GamepadMapping:
    """手柄到控制指令的映射配置

    可自定义摇杆/按钮对应的控制功能。
    """
    # 轴映射: (轴ID, 缩放系数, 对应位姿分量)
    # 默认: 左摇杆 = XY平移, 右摇杆 = Z + Yaw, 扳机 = Roll/Pitch
    end_effector_x: tuple[int, float] = (GamepadAxis.LEFT_X, 1.0)
    end_effector_y: tuple[int, float] = (GamepadAxis.LEFT_Y, -1.0)
    end_effector_z: tuple[int, float] = (GamepadAxis.RIGHT_Y, 1.0)
    end_effector_yaw: tuple[int, float] = (GamepadAxis.RIGHT_X, 1.0)
    end_effector_roll: tuple[int, float] = (GamepadAxis.LEFT_TRIGGER, 1.0)
    end_effector_pitch: tuple[int, float] = (GamepadAxis.RIGHT_TRIGGER, 1.0)

    # 按钮映射
    button_gripper_close: int = GamepadButton.RB
    button_gripper_open: int = GamepadButton.LB
    button_emergency_stop: int = GamepadButton.SELECT
    button_mode_switch: int = GamepadButton.START

    # 摇杆死区
    deadzone: float = 0.08
    # 平移灵敏度 (m/s per axis unit)
    translate_sensitivity: float = 0.5
    # 旋转灵敏度 (rad/s per axis unit)
    rotate_sensitivity: float = 1.0
    # 平滑因子
    smoothing: float = 0.3


class GamepadDriver:
    """手柄驱动

    将手柄输入转换为遥操作指令。
    """

    def __init__(self, mapping: GamepadMapping | None = None) -> None:
        self._mapping = mapping or GamepadMapping()
        self._state = GamepadState()
        self._smoothers = {
            f"axis_{i}": Smoother(self._mapping.smoothing, self._mapping.deadzone)
            for i in range(6)
        }
        self._prev_buttons: dict[int, bool] = {}
        self._on_teleop: callable | None = None  # type: ignore
        self._on_emergency: callable | None = None  # type: ignore

    def set_teleop_callback(self, callback: callable) -> None:  # type: ignore
        """设置遥操作指令回调"""
        self._on_teleop = callback

    def set_emergency_callback(self, callback: callable) -> None:  # type: ignore
        """设置紧急制动回调"""
        self._on_emergency = callback

    def update_state(self, state: GamepadState) -> Optional[TeleopCommand]:
        """更新手柄状态并生成遥操作指令

        Args:
            state: 当前手柄状态快照

        Returns:
            如果有有效输入，返回 TeleopCommand；否则返回 None。
        """
        self._state = state

        # 检查按钮边缘触发
        self._check_buttons()

        # 读取并平滑轴值
        axes = {
            "x": self._smooth_axis(0, state.get_axis(self._mapping.end_effector_x[0])
                                   * self._mapping.end_effector_x[1]),
            "y": self._smooth_axis(1, state.get_axis(self._mapping.end_effector_y[0])
                                   * self._mapping.end_effector_y[1]),
            "z": self._smooth_axis(2, state.get_axis(self._mapping.end_effector_z[0])
                                   * self._mapping.end_effector_z[1]),
            "yaw": self._smooth_axis(3, state.get_axis(self._mapping.end_effector_yaw[0])
                                     * self._mapping.end_effector_yaw[1]),
            "roll": self._smooth_axis(4, state.get_axis(self._mapping.end_effector_roll[0])
                                     * self._mapping.end_effector_roll[1]),
            "pitch": self._smooth_axis(5, state.get_axis(self._mapping.end_effector_pitch[0])
                                       * self._mapping.end_effector_pitch[1]),
        }

        # 检查是否有有效输入（非零轴值）
        axis_magnitude = sum(abs(v) for v in axes.values())
        if axis_magnitude < 0.01:
            return None

        # 生成遥操作指令
        cmd = TeleopCommand(
            mode=ControlMode.END_EFFECTOR,
            target_frame="base_link",
            pose=Pose(
                x=axes["x"] * self._mapping.translate_sensitivity,
                y=axes["y"] * self._mapping.translate_sensitivity,
                z=axes["z"] * self._mapping.translate_sensitivity,
                roll=axes["roll"] * self._mapping.rotate_sensitivity,
                pitch=axes["pitch"] * self._mapping.rotate_sensitivity,
                yaw=axes["yaw"] * self._mapping.rotate_sensitivity,
            ),
        )
        return cmd

    def _smooth_axis(self, axis_id: int, raw_value: float) -> float:
        return self._smoothers[f"axis_{axis_id}"].update(raw_value)

    def _check_buttons(self) -> None:
        """检查按钮边缘触发事件"""
        for button_id in (self._mapping.button_emergency_stop,
                          self._mapping.button_mode_switch):
            was_pressed = self._prev_buttons.get(button_id, False)
            is_pressed = self._state.is_pressed(button_id)

            if is_pressed and not was_pressed:
                if button_id == self._mapping.button_emergency_stop:
                    if self._on_emergency:
                        self._on_emergency("gamepad")
                elif button_id == self._mapping.button_mode_switch:
                    pass  # 模式切换由上层处理

        self._prev_buttons = dict(self._state.buttons)

    def get_gripper_command(self) -> GripperCommand:
        """获取当前夹爪指令"""
        if self._state.is_pressed(self._mapping.button_gripper_close):
            return GripperCommand.CLOSE
        if self._state.is_pressed(self._mapping.button_gripper_open):
            return GripperCommand.OPEN
        return GripperCommand.STOP
