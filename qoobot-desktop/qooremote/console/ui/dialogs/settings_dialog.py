"""设置对话框 — 偏好设置多页签

页面：连接设置 / 告警规则配置 / UI 偏好
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QPushButton, QSlider, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget, QDoubleSpinBox,
)


class SettingsDialog(QDialog):
    """应用设置对话框"""

    settings_applied = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("偏好设置")
        self.setMinimumSize(500, 420)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()

        # 连接设置页
        tabs.addTab(self._create_connection_tab(), "连接")
        # 告警规则页
        tabs.addTab(self._create_alert_rules_tab(), "告警规则")
        # UI 偏好页
        tabs.addTab(self._create_ui_tab(), "界面")
        # 关于页
        tabs.addTab(self._create_about_tab(), "关于")

        layout.addWidget(tabs)

        # 按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("应用")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(apply_btn)

        layout.addLayout(btn_row)

    def _create_connection_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # 重连
        reconnect = QGroupBox("自动重连")
        form = QFormLayout(reconnect)
        self._auto_reconnect = QCheckBox("启用自动重连")
        self._auto_reconnect.setChecked(True)
        form.addRow("", self._auto_reconnect)
        self._reconnect_max_retries = QSpinBox()
        self._reconnect_max_retries.setRange(1, 100)
        self._reconnect_max_retries.setValue(10)
        form.addRow("最大重试次数:", self._reconnect_max_retries)
        self._reconnect_interval = QSpinBox()
        self._reconnect_interval.setRange(1, 60)
        self._reconnect_interval.setValue(3)
        self._reconnect_interval.setSuffix(" 秒")
        form.addRow("重连间隔:", self._reconnect_interval)
        layout.addWidget(reconnect)

        # 心跳
        heartbeat = QGroupBox("心跳检测")
        hb_form = QFormLayout(heartbeat)
        self._heartbeat_interval = QSpinBox()
        self._heartbeat_interval.setRange(1, 60)
        self._heartbeat_interval.setValue(5)
        self._heartbeat_interval.setSuffix(" 秒")
        hb_form.addRow("心跳间隔:", self._heartbeat_interval)
        self._heartbeat_timeout = QSpinBox()
        self._heartbeat_timeout.setRange(5, 120)
        self._heartbeat_timeout.setValue(15)
        self._heartbeat_timeout.setSuffix(" 秒")
        hb_form.addRow("心跳超时:", self._heartbeat_timeout)
        layout.addWidget(heartbeat)

        layout.addStretch()
        return w

    def _create_alert_rules_tab(self) -> QWidget:
        """告警规则配置 — 对应 ALT-02"""
        w = QWidget()
        layout = QVBoxLayout(w)

        rules_group = QGroupBox("告警阈值")
        form = QFormLayout(rules_group)

        self._cpu_warning = QSpinBox()
        self._cpu_warning.setRange(50, 100)
        self._cpu_warning.setValue(80)
        self._cpu_warning.setSuffix(" %")
        form.addRow("CPU 告警阈值:", self._cpu_warning)

        self._mem_warning = QSpinBox()
        self._mem_warning.setRange(50, 100)
        self._mem_warning.setValue(85)
        self._mem_warning.setSuffix(" %")
        form.addRow("内存告警阈值:", self._mem_warning)

        self._temp_warning = QSpinBox()
        self._temp_warning.setRange(50, 120)
        self._temp_warning.setValue(80)
        self._temp_warning.setSuffix(" °C")
        form.addRow("温度告警阈值:", self._temp_warning)

        self._battery_warning = QSpinBox()
        self._battery_warning.setRange(5, 50)
        self._battery_warning.setValue(15)
        self._battery_warning.setSuffix(" %")
        form.addRow("低电量告警:", self._battery_warning)

        self._latency_warning = QSpinBox()
        self._latency_warning.setRange(50, 1000)
        self._latency_warning.setValue(200)
        self._latency_warning.setSuffix(" ms")
        form.addRow("高延迟告警:", self._latency_warning)

        self._loss_warning = QDoubleSpinBox()
        self._loss_warning.setRange(1, 50)
        self._loss_warning.setValue(5.0)
        self._loss_warning.setSuffix(" %")
        self._loss_warning.setDecimals(1)
        form.addRow("丢包率告警:", self._loss_warning)

        layout.addWidget(rules_group)

        notify_group = QGroupBox("通知策略")
        nf_form = QFormLayout(notify_group)
        self._sound_on = QCheckBox("启用声音通知")
        self._sound_on.setChecked(True)
        nf_form.addRow("", self._sound_on)
        self._toast_on = QCheckBox("启用弹窗通知")
        self._toast_on.setChecked(True)
        nf_form.addRow("", self._toast_on)
        layout.addWidget(notify_group)

        layout.addStretch()
        return w

    def _create_ui_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        theme_group = QGroupBox("主题")
        tf = QFormLayout(theme_group)
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["深色主题 (Dark)", "浅色主题 (Light)", "跟随系统"])
        self._theme_combo.setCurrentIndex(0)
        tf.addRow("主题:", self._theme_combo)
        layout.addWidget(theme_group)

        lang_group = QGroupBox("语言")
        lf = QFormLayout(lang_group)
        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["中文 (zh_CN)", "English (en_US)"])
        lf.addRow("语言:", self._lang_combo)
        layout.addWidget(lang_group)

        video_group = QGroupBox("视频默认值")
        vf = QFormLayout(video_group)
        self._video_resolution = QComboBox()
        self._video_resolution.addItems(["1080p (1920×1080)", "720p (1280×720)",
                                          "540p (960×540)", "480p (640×480)"])
        self._video_resolution.setCurrentIndex(1)
        vf.addRow("默认分辨率:", self._video_resolution)
        self._video_fps = QSpinBox()
        self._video_fps.setRange(10, 60)
        self._video_fps.setValue(30)
        vf.addRow("默认帧率:", self._video_fps)
        layout.addWidget(video_group)

        layout.addStretch()
        return w

    def _create_about_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("QooRemote")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        version = QLabel("版本: v0.3.0 (Control)")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        desc = QLabel("QooBot 远程机器人监控遥控控制台\n\n"
                      "提供视频回传、遥操作控制、语音对讲、\n"
                      "示教录制等一站式远程操作体验。")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #888;")
        layout.addWidget(desc)

        license_label = QLabel("许可证: Apache 2.0")
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_label.setStyleSheet("color: #666;")
        layout.addWidget(license_label)

        layout.addStretch()
        return w

    def _on_apply(self) -> None:
        settings = {
            "connection": {
                "auto_reconnect": self._auto_reconnect.isChecked(),
                "max_retries": self._reconnect_max_retries.value(),
                "reconnect_interval": self._reconnect_interval.value(),
                "heartbeat_interval": self._heartbeat_interval.value(),
                "heartbeat_timeout": self._heartbeat_timeout.value(),
            },
            "alerts": {
                "cpu_warning": self._cpu_warning.value(),
                "mem_warning": self._mem_warning.value(),
                "temp_warning": self._temp_warning.value(),
                "battery_warning": self._battery_warning.value(),
                "latency_warning": self._latency_warning.value(),
                "loss_warning": self._loss_warning.value(),
                "sound_notify": self._sound_on.isChecked(),
                "toast_notify": self._toast_on.isChecked(),
            },
            "ui": {
                "theme": self._theme_combo.currentIndex(),
                "language": self._lang_combo.currentText(),
                "video_resolution": self._video_resolution.currentIndex(),
                "video_fps": self._video_fps.value(),
            },
        }
        self.settings_applied.emit(settings)
        self.accept()
