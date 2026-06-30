"""连接状态指示器 — 显示与机器人的连接状态和质量

以可视化方式展示连接状态、延迟和丢包率。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from console.core.signaling.client import ConnectionState


class ConnectionIndicator(QWidget):
    """连接状态指示器

    以圆点 + 文字显示当前连接状态，
    支持脉冲动画表示连接中/重连中。
    """

    SIZE = 60

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, 80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("未连接")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self._label)

        self._state = ConnectionState.DISCONNECTED
        self._pulse_phase = 0.0

        # 脉冲动画计时器
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._update_pulse)
        self._pulse_timer.start(50)  # 20fps

    def _update_pulse(self) -> None:
        """更新脉冲动画"""
        self._pulse_phase = (self._pulse_phase + 0.1) % (2 * 3.14159)
        if self._state in (ConnectionState.CONNECTING, ConnectionState.RECONNECTING):
            self.update()

    def set_state(self, state: ConnectionState) -> None:
        """更新连接状态"""
        self._state = state

        state_text = {
            ConnectionState.DISCONNECTED: "未连接",
            ConnectionState.CONNECTING: "连接中...",
            ConnectionState.CONNECTED: "已连接",
            ConnectionState.AUTHENTICATED: "已认证",
            ConnectionState.SESSION_ACTIVE: "会话活跃",
            ConnectionState.RECONNECTING: "重连中...",
        }
        self._label.setText(state_text.get(state, "未知"))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = 20
        radius = 12

        # 脉冲效果
        if self._state in (ConnectionState.CONNECTING, ConnectionState.RECONNECTING):
            pulse_r = radius + 6 + int(4 * abs(0.5 - (self._pulse_phase % 1.0)) * 2)

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#f39c12").lighter(150))
            painter.setOpacity(0.3)
            painter.drawEllipse(QRectF(cx - pulse_r, cy - pulse_r,
                                       pulse_r * 2, pulse_r * 2))
            painter.setOpacity(1.0)

        # 状态圆点
        state_colors = {
            ConnectionState.DISCONNECTED: QColor("#718093"),
            ConnectionState.CONNECTING: QColor("#f39c12"),
            ConnectionState.CONNECTED: QColor("#3498db"),
            ConnectionState.AUTHENTICATED: QColor("#2ecc71"),
            ConnectionState.SESSION_ACTIVE: QColor("#2ecc71"),
            ConnectionState.RECONNECTING: QColor("#e67e22"),
        }
        color = state_colors.get(self._state, QColor("#718093"))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QRectF(cx - radius, cy - radius, radius * 2, radius * 2))

        # 外围光晕
        glow_r = radius + 4
        glow_color = QColor(color)
        glow_color.setAlpha(60)
        painter.setBrush(glow_color)
        painter.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))
