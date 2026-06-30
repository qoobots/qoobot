"""语音对讲面板 — PTT 按键/音量指示器/通话状态

对应功能 VOX-01（双向语音通话）、VOX-02（一键对讲 PTT）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QProgressBar, QComboBox, QCheckBox, QGroupBox,
)

from console.core.webrtc.audio_track import VoiceMode, AudioConfig, AudioCodec


class VolumeIndicator(QProgressBar):
    """音量指示条"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRange(0, 100)
        self.setTextVisible(False)
        self.setFixedHeight(12)
        self.setFixedWidth(120)
        self.setValue(0)

    def set_level(self, rms: float) -> None:
        """设置音量级别 (0.0 ~ 1.0 归一化)"""
        value = min(int(rms * 200), 100)  # RMS 映射到 0-100
        self.setValue(value)

        # 颜色梯度
        if value > 80:
            self.setStyleSheet("QProgressBar::chunk { background: #e74c3c; }")
        elif value > 50:
            self.setStyleSheet("QProgressBar::chunk { background: #f39c12; }")
        else:
            self.setStyleSheet("QProgressBar::chunk { background: #2ecc71; }")


class VoicePanel(QFrame):
    """语音对讲控制面板

    功能：
    - PTT 按键说话/松开监听（VOX-02）
    - 全双工切换（VOX-03）
    - TX/RX 实时音量指示
    - 音频编码配置
    - 降噪开关（VOX-04）
    """

    # 信号
    ptt_pressed = Signal()                # PTT 按下
    ptt_released = Signal()               # PTT 松开
    mode_changed = Signal(str)            # 模式变更 (ptt/full/disabled)
    mute_toggled = Signal(bool)           # 静音切换
    codec_changed = Signal(str)           # 编码格式变更
    config_changed = Signal(object)       # 配置变更 (AudioConfig)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mode = VoiceMode.PTT
        self._muted = False
        self._tx_level = 0.0
        self._rx_level = 0.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题
        title = QLabel("🎤 语音对讲")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # ---- 模式选择 ----
        mode_group = QGroupBox("通话模式")
        mode_layout = QVBoxLayout(mode_group)

        mode_row = QHBoxLayout()
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("🔘 一键对讲 (PTT)", VoiceMode.PTT.value)
        self._mode_combo.addItem("📞 全双工免提", VoiceMode.FULL_DUPLEX.value)
        self._mode_combo.addItem("🚫 禁用语音", VoiceMode.DISABLED.value)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        mode_row.addWidget(self._mode_combo)
        mode_layout.addLayout(mode_row)

        # PTT 按钮
        self._ptt_button = QPushButton("🎙️ 按住说话")
        self._ptt_button.setMinimumHeight(48)
        self._ptt_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white;
                font-size: 16px; font-weight: bold;
                border-radius: 6px; padding: 8px;
            }
            QPushButton:pressed {
                background-color: #e74c3c;
            }
        """)
        self._ptt_button.pressed.connect(self._on_ptt_press)
        self._ptt_button.released.connect(self._on_ptt_release)
        mode_layout.addWidget(self._ptt_button)

        # 静音复选框
        self._mute_check = QCheckBox("🔇 静音麦克风")
        self._mute_check.toggled.connect(self._on_mute_toggled)
        mode_layout.addWidget(self._mute_check)

        layout.addWidget(mode_group)

        # ---- 音量指示 ----
        vol_group = QGroupBox("音量")
        vol_layout = QVBoxLayout(vol_group)

        tx_row = QHBoxLayout()
        tx_row.addWidget(QLabel("发送 (TX):"))
        self._tx_indicator = VolumeIndicator()
        self._tx_label = QLabel("0%")
        tx_row.addWidget(self._tx_indicator)
        tx_row.addWidget(self._tx_label)
        vol_layout.addLayout(tx_row)

        rx_row = QHBoxLayout()
        rx_row.addWidget(QLabel("接收 (RX):"))
        self._rx_indicator = VolumeIndicator()
        self._rx_label = QLabel("0%")
        rx_row.addWidget(self._rx_indicator)
        rx_row.addWidget(self._rx_label)
        vol_layout.addLayout(rx_row)

        layout.addWidget(vol_group)

        # ---- 编码配置 ----
        codec_group = QGroupBox("编码")
        codec_layout = QVBoxLayout(codec_group)

        codec_row = QHBoxLayout()
        codec_row.addWidget(QLabel("格式:"))
        self._codec_combo = QComboBox()
        for c in AudioCodec:
            self._codec_combo.addItem(c.value.upper(), c.value)
        self._codec_combo.currentIndexChanged.connect(
            lambda: self.codec_changed.emit(self._codec_combo.currentData())
        )
        codec_row.addWidget(self._codec_combo)
        codec_layout.addLayout(codec_row)

        self._nr_check = QCheckBox("🔉 AI 降噪 (VOX-04)")
        self._nr_check.setChecked(True)
        codec_layout.addWidget(self._nr_check)

        self._ec_check = QCheckBox("🔄 回声消除")
        self._ec_check.setChecked(True)
        codec_layout.addWidget(self._ec_check)

        self._agc_check = QCheckBox("📊 自动增益")
        self._agc_check.setChecked(True)
        codec_layout.addWidget(self._agc_check)

        layout.addWidget(codec_group)
        layout.addStretch()

    # ---- 属性 ----

    @property
    def voice_mode(self) -> VoiceMode:
        return self._mode

    @property
    def is_muted(self) -> bool:
        return self._muted

    @property
    def audio_config(self) -> AudioConfig:
        codec = AudioCodec(self._codec_combo.currentData() or "opus")
        return AudioConfig(
            codec=codec,
            noise_suppression=self._nr_check.isChecked(),
            echo_cancellation=self._ec_check.isChecked(),
            auto_gain_control=self._agc_check.isChecked(),
        )

    # ---- 公开方法 ----

    def update_levels(self, tx_rms: float, rx_rms: float) -> None:
        """更新音量指示"""
        self._tx_level = tx_rms
        self._rx_level = rx_rms
        self._tx_indicator.set_level(tx_rms)
        self._rx_indicator.set_level(rx_rms)
        self._tx_label.setText(f"{min(int(tx_rms * 200), 100)}%")
        self._rx_label.setText(f"{min(int(rx_rms * 200), 100)}%")

    def set_ptt_active(self, active: bool) -> None:
        """设置 PTT 状态"""
        if active:
            self._ptt_button.setStyleSheet("""
                QPushButton { background-color: #e74c3c; color: white;
                    font-size: 16px; font-weight: bold; border-radius: 6px; padding: 8px; }
            """)
            self._ptt_button.setText("🔴 正在说话...")
        else:
            self._ptt_button.setStyleSheet("""
                QPushButton { background-color: #3498db; color: white;
                    font-size: 16px; font-weight: bold; border-radius: 6px; padding: 8px; }
            """)
            self._ptt_button.setText("🎙️ 按住说话")

    # ---- 槽 ----

    def _on_ptt_press(self) -> None:
        self.set_ptt_active(True)
        self.ptt_pressed.emit()

    def _on_ptt_release(self) -> None:
        self.set_ptt_active(False)
        self.ptt_released.emit()

    def _on_mode_changed(self, index: int) -> None:
        mode_value = self._mode_combo.currentData()
        try:
            self._mode = VoiceMode(mode_value)
        except ValueError:
            self._mode = VoiceMode.PTT
        self._ptt_button.setVisible(self._mode == VoiceMode.PTT)
        self.mode_changed.emit(self._mode.value)

    def _on_mute_toggled(self, checked: bool) -> None:
        self._muted = checked
        self._ptt_button.setEnabled(not checked)
        self.mute_toggled.emit(checked)
