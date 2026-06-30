"""遥操作 ViewModel

管理遥操作控制的状态：输入设备映射、操控模式、
指令缓冲和发送。
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, QTimer

from console.core.teleop.controller import (
    ControlMode,
    EmergencyStopCommand,
    ModeSwitchCommand,
    TeleopCommand,
    JointCommand,
    TeleopController,
)
from console.core.teleop.gamepad import GamepadDriver, GamepadMapping
from console.core.teleop.keyboard import KeyboardDriver, KeyboardMapping


class TeleopViewModel(QObject):
    """遥操作 ViewModel

    管理遥操作的输入设备、模式切换和指令发送。
    """

    command_sent = Signal(object)              # command dict
    emergency_triggered = Signal(str)          # reason
    mode_switch_triggered = Signal(str, str)   # from_mode, to_mode
    gamepad_status_changed = Signal(bool, str) # connected, name
    control_mode_changed = Signal(str)         # control_mode

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._controller = TeleopController()
        self._gamepad = GamepadDriver()
        self._keyboard = KeyboardDriver()

        self._controller.set_send_callback(self._on_send_command)
        self._gamepad.set_teleop_callback(self._on_teleop_command)
        self._gamepad.set_emergency_callback(self._on_emergency)
        self._keyboard.set_teleop_callback(self._on_teleop_command)
        self._keyboard.set_emergency_callback(self._on_emergency)

        self._active = False
        self._command_count = 0
        self._command_rate_hz = 0.0

        # 频率统计
        self._rate_timer = QTimer(self)
        self._rate_timer.setInterval(1000)
        self._rate_timer.timeout.connect(self._on_rate_tick)

    @property
    def active(self) -> bool:
        return self._active

    @property
    def command_rate_hz(self) -> float:
        return self._command_rate_hz

    def activate(self) -> None:
        self._active = True
        self._controller.activate()
        self._rate_timer.start()

    def deactivate(self) -> None:
        self._active = False
        self._controller.deactivate()
        self._rate_timer.stop()

    def press_key(self, key: int) -> None:
        self._keyboard.press_key(key)

    def release_key(self, key: int) -> None:
        self._keyboard.release_key(key)

    def trigger_emergency_stop(self, reason: str = "operator") -> None:
        """触发紧急制动"""
        self._on_emergency(reason)

    def switch_mode(self, to_mode: str) -> None:
        """切换操控模式"""
        self._on_mode_switch(to_mode)

    def set_gamepad_connected(self, connected: bool, name: str = "") -> None:
        """更新手柄连接状态"""
        self.gamepad_status_changed.emit(connected, name)

    def set_control_mode(self, mode: str) -> None:
        """设置控制模式"""
        self.control_mode_changed.emit(mode)

    def _on_send_command(self, cmd_dict: dict) -> None:
        self._command_count += 1
        self.command_sent.emit(cmd_dict)

    def _on_teleop_command(self, command: TeleopCommand) -> None:
        if self._active:
            self.command_sent.emit(command.to_dict())

    def _on_emergency(self, reason: str) -> None:
        self.emergency_triggered.emit(reason)

    def _on_mode_switch(self, to_mode: str) -> None:
        self.mode_switch_triggered.emit("current", to_mode)

    def _on_rate_tick(self) -> None:
        self._command_rate_hz = self._command_count
        self._command_count = 0
