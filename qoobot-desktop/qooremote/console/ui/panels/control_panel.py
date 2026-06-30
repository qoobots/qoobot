"""操控面板 — 遥操作控制界面

集成模式切换、控制模式选择、手柄/键盘状态、
指令监控等功能。

对应功能 TAK-01（模式切换）、TEL-01（手柄/键盘遥控）。
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSlider,
)


class ControlPanel(QWidget):
    """操控面板

    提供遥操作控制界面，包括：
    - 操控模式选择（末端位姿/关节位置/速度/力矩）
    - 机器人模式切换（自主/半自主/全手动）
    - 灵敏度调节
    - 指令发送指示器
    """

    mode_switch_requested = Signal(str)  # to_mode
    control_mode_changed = Signal(str)   # control_mode
    sensitivity_changed = Signal(float)  # 0.1-1.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 机器人模式切换 — TAK-01
        mode_group = QGroupBox("机器人模式")
        mode_layout = QVBoxLayout(mode_group)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            "🔵 全自主 (Autonomous)",
            "🟡 半自主 (Semi-Autonomous)",
            "🟢 全手动 (Manual)",
        ])
        mode_layout.addWidget(self._mode_combo)

        self._switch_btn = QPushButton("切换模式")
        self._switch_btn.clicked.connect(self._on_mode_switch)
        mode_layout.addWidget(self._switch_btn)

        self._mode_status = QLabel("当前: 全自主")
        self._mode_status.setStyleSheet("color: #90a4ae; font-size: 11px;")
        mode_layout.addWidget(self._mode_status)
        layout.addWidget(mode_group)

        # 控制模式 — TEL-01
        ctrl_group = QGroupBox("控制模式")
        ctrl_layout = QVBoxLayout(ctrl_group)

        self._control_combo = QComboBox()
        self._control_combo.addItems([
            "末端位姿控制",
            "关节位置控制",
            "关节速度控制",
            "关节力矩控制",
        ])
        self._control_combo.currentIndexChanged.connect(self._on_control_mode_changed)
        ctrl_layout.addWidget(self._control_combo)

        layout.addWidget(ctrl_group)

        # 灵敏度 — TEL-01
        sens_group = QGroupBox("操控灵敏度")
        sens_layout = QVBoxLayout(sens_group)

        sens_row = QHBoxLayout()
        sens_row.addWidget(QLabel("低"))
        self._sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self._sensitivity_slider.setRange(10, 100)
        self._sensitivity_slider.setValue(70)
        self._sensitivity_slider.valueChanged.connect(self._on_sensitivity_changed)
        sens_row.addWidget(self._sensitivity_slider)
        sens_row.addWidget(QLabel("高"))
        sens_layout.addLayout(sens_row)

        self._sensitivity_label = QLabel("0.7")
        self._sensitivity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sensitivity_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        sens_layout.addWidget(self._sensitivity_label)

        layout.addWidget(sens_group)

        # 输入设备状态
        input_group = QGroupBox("输入设备")
        input_layout = QVBoxLayout(input_group)

        self._gamepad_status = QLabel("🎮 手柄: 未检测到")
        input_layout.addWidget(self._gamepad_status)

        self._keyboard_status = QLabel("⌨ 键盘: 已启用")
        input_layout.addWidget(self._keyboard_status)

        layout.addWidget(input_group)

        # 指令监控
        cmd_group = QGroupBox("指令监控")
        cmd_layout = QVBoxLayout(cmd_group)

        self._cmd_rate_label = QLabel("发送频率: -- Hz")
        cmd_layout.addWidget(self._cmd_rate_label)

        self._last_cmd_label = QLabel("最后指令: --")
        cmd_layout.addWidget(self._last_cmd_label)

        layout.addWidget(cmd_group)

        layout.addStretch()

        self._mode_map = {
            0: "autonomous",
            1: "semi_autonomous",
            2: "manual",
        }

    def _on_mode_switch(self) -> None:
        """模式切换按钮"""
        to_mode = self._mode_map.get(self._mode_combo.currentIndex(), "autonomous")
        self.mode_switch_requested.emit(to_mode)
        mode_names = {
            "autonomous": "全自主",
            "semi_autonomous": "半自主",
            "manual": "全手动",
        }
        self._mode_status.setText(f"切换中 → {mode_names.get(to_mode, to_mode)}")

    def _on_control_mode_changed(self, index: int) -> None:
        """控制模式变更"""
        control_modes = ["end_effector", "position", "velocity", "torque"]
        mode = control_modes[index] if index < len(control_modes) else "end_effector"
        self.control_mode_changed.emit(mode)

    def _on_sensitivity_changed(self, value: int) -> None:
        """灵敏度变更"""
        sensitivity = value / 100.0
        self._sensitivity_label.setText(f"{sensitivity:.1f}")
        self.sensitivity_changed.emit(sensitivity)

    def set_gamepad_connected(self, connected: bool, name: str = "") -> None:
        """更新手柄状态"""
        if connected:
            self._gamepad_status.setText(f"🎮 手柄: {name or '已连接'}")
            self._gamepad_status.setStyleSheet("color: #2ecc71;")
        else:
            self._gamepad_status.setText("🎮 手柄: 未检测到")
            self._gamepad_status.setStyleSheet("color: #90a4ae;")

    def set_command_rate(self, rate_hz: float) -> None:
        """更新指令发送频率"""
        self._cmd_rate_label.setText(f"发送频率: {rate_hz:.1f} Hz")

    def set_last_command(self, description: str) -> None:
        """更新最后指令描述"""
        self._last_cmd_label.setText(f"最后指令: {description}")
