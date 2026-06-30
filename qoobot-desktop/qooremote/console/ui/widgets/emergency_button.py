"""紧急制动按钮 — 醒目的大号红色按钮

对应功能 TAK-02（一键紧急接管+紧急制动）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QTimer, QRectF, Property
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QBrush, QRadialGradient
from PySide6.QtWidgets import QWidget, QSizePolicy


class EmergencyButton(QWidget):
    """紧急制动按钮

    大尺寸红色圆形按钮，带发光脉冲动画。
    点击触发紧急制动信号。
    """

    clicked = Signal()
    SIZE = 100

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE + 20, self.SIZE + 20)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._hovered = False
        self._pressed = False
        self._pulse_value: float = 0.0

        # 脉冲动画
        self._pulse_timer = QTimer()
        self._pulse_timer.timeout.connect(self._update_pulse)
        self._pulse_timer.setInterval(50)
        self._pulse_timer.start()

        # 闪烁警告脉冲
        self._warn_timer = QTimer()
        self._warn_timer.timeout.connect(self.update)
        self._warn_timer.setInterval(800)
        self._warn_timer.start()

    def _update_pulse(self) -> None:
        self._pulse_value = (self._pulse_value + 0.06) % (2 * 3.14159)
        self.update()

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._pressed:
            self._pressed = False
            self.update()
            self.clicked.emit()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        radius = self.SIZE / 2

        # 脉冲光晕
        pulse_factor = abs(self._pulse_value % 2.0 - 1.0)
        pulse_r = radius + 10 + int(pulse_factor * 15)

        glow = QRadialGradient(cx, cy, pulse_r)
        glow.setColorAt(0, QColor(231, 76, 60, 100))
        glow.setColorAt(0.7, QColor(231, 76, 60, 30))
        glow.setColorAt(1, QColor(231, 76, 60, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glow)
        painter.drawEllipse(QRectF(cx - pulse_r, cy - pulse_r, pulse_r * 2, pulse_r * 2))

        # 按钮主体
        base_r = radius
        if self._pressed:
            base_r -= 3

        gradient = QRadialGradient(cx - 5, cy - 5, base_r)
        if self._hovered:
            gradient.setColorAt(0, QColor(255, 99, 71))
            gradient.setColorAt(1, QColor(192, 57, 43))
        else:
            gradient.setColorAt(0, QColor(231, 76, 60))
            gradient.setColorAt(1, QColor(169, 50, 38))

        painter.setBrush(gradient)
        painter.setPen(QPen(QColor("#7f0000"), 2))
        painter.drawEllipse(QRectF(cx - base_r, cy - base_r, base_r * 2, base_r * 2))

        # 文字
        painter.setPen(QColor("#ffffff"))
        font = QFont("Microsoft YaHei", 16)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QRectF(cx - radius, cy - 14, radius * 2, 28),
            Qt.AlignmentFlag.AlignCenter,
            "紧急\n制动"
        )

        # 图标装饰
        painter.setPen(QPen(QColor("#ffffff"), 2))
        # 停止图标 (两条竖线)
        margin = 8
        bar_w = 5
        bar_h = 14
        bar_y = cy + 15
        painter.drawRect(int(cx - bar_w - margin), int(bar_y), bar_w, bar_h)
        painter.drawRect(int(cx + margin), int(bar_y), bar_w, bar_h)
