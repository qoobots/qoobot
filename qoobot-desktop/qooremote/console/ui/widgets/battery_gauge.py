"""电量仪表盘控件

以弧形仪表盘方式展示电池电量、充放电状态和预估续航。
支持动画过渡效果。

对应功能 DASH-02（电池与电源监控）。
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    Property,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QFont,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)


class BatteryGauge(QWidget):
    """电量弧形仪表盘

    以圆弧进度方式展示电池电量，带颜色渐变指示。
    支持充电动画和正常/低电量/严重低电量颜色变化。
    """

    MINIMUM_SIZE = 160

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(self.MINIMUM_SIZE, self.MINIMUM_SIZE)
        self.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        self._percentage: float = 100.0
        self._charging: bool = False
        self._voltage: float = 0.0
        self._current_amps: float = 0.0
        self._runtime_minutes: float = 0.0
        self._power_watts: float = 0.0
        self._animation_value: float = 0.0

        # 充电动画
        self._charge_anim = QPropertyAnimation(self, b"animation_value")
        self._charge_anim.setDuration(2000)
        self._charge_anim.setStartValue(0.0)
        self._charge_anim.setEndValue(360.0)
        self._charge_anim.setLoopCount(-1)

    # Qt 属性，用于动画
    def get_animation_value(self) -> float:
        return self._animation_value

    def set_animation_value(self, value: float) -> None:
        self._animation_value = value
        self.update()

    animation_value = Property(float, get_animation_value, set_animation_value)

    def update_data(
        self,
        percentage: float,
        charging: bool = False,
        voltage: float = 0,
        current: float = 0,
        power_watts: float = 0,
        runtime_minutes: float = 0,
    ) -> None:
        """更新电池数据"""
        self._percentage = max(0.0, min(100.0, percentage))
        self._charging = charging
        self._voltage = voltage
        self._current_amps = current
        self._power_watts = power_watts
        self._runtime_minutes = runtime_minutes

        if charging:
            self._charge_anim.start()
        else:
            self._charge_anim.stop()

        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h) - 20
        cx = w / 2.0
        cy = h / 2.0 + 10

        # 背景弧
        pen = QPen(QColor("#16213e"), 14)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            QRectF(cx - side / 2, cy - side / 2, side, side),
            225 * 16,  # 起始角度
            270 * 16,  # 跨度角度
        )

        # 根据电量选择颜色
        if self._percentage <= 10:
            arc_color = QColor("#e74c3c")  # 红色: < 10%
        elif self._percentage <= 20:
            arc_color = QColor("#f39c12")  # 黄色: 10-20%
        elif self._percentage <= 50:
            arc_color = QColor("#f1c40f")  # 浅黄: 20-50%
        else:
            arc_color = QColor("#2ecc71")  # 绿色: > 50%

        if self._charging:
            # 充电动画: 颜色交替
            anim_offset = int(self._animation_value / 60) % 2
            if anim_offset == 0:
                arc_color = arc_color.lighter(120)

        # 电量弧
        span_angle = int(270 * self._percentage / 100.0)
        pen = QPen(arc_color, 14)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(
            QRectF(cx - side / 2, cy - side / 2, side, side),
            225 * 16,
            -span_angle * 16,
        )

        # 文字显示
        # 百分比
        painter.setPen(QColor("#e0e0e0"))
        font = QFont("Segoe UI", 28)
        font.setBold(True)
        painter.setFont(font)
        text = f"{self._percentage:.0f}%"
        painter.drawText(
            QRectF(cx - 60, cy - 50, 120, 40),
            Qt.AlignmentFlag.AlignCenter,
            text,
        )

        # 充放电状态
        painter.setPen(QColor("#90a4ae"))
        font = QFont("Segoe UI", 10)
        painter.setFont(font)

        if self._charging:
            status_text = "⚡ 充电中"
        elif self._percentage <= 20:
            status_text = "⚠ 电量低"
        else:
            status_text = "● 放电中"

        painter.drawText(
            QRectF(cx - 60, cy, 120, 20),
            Qt.AlignmentFlag.AlignCenter,
            status_text,
        )

        # 续航时间
        if self._runtime_minutes > 0 and not self._charging:
            hours = int(self._runtime_minutes // 60)
            mins = int(self._runtime_minutes % 60)
            runtime_text = f"剩余 {hours}h{mins}m"
        elif self._charging:
            runtime_text = f"{self._voltage:.1f}V {self._current_amps:.1f}A"
        else:
            runtime_text = "--"

        painter.drawText(
            QRectF(cx - 60, cy + 20, 120, 20),
            Qt.AlignmentFlag.AlignCenter,
            runtime_text,
        )


class BatteryDetailPanel(QWidget):
    """电池详情面板 — 电量仪表盘 + 详细数据"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 左侧: 仪表盘
        self._gauge = BatteryGauge()
        layout.addWidget(self._gauge)

        # 右侧: 详细数据
        detail_layout = QVBoxLayout()
        detail_layout.setSpacing(8)

        self._voltage_label = QLabel("电压: -- V")
        self._voltage_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        detail_layout.addWidget(self._voltage_label)

        self._current_label = QLabel("电流: -- A")
        self._current_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        detail_layout.addWidget(self._current_label)

        self._power_label = QLabel("功耗: -- W")
        self._power_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        detail_layout.addWidget(self._power_label)

        self._runtime_label = QLabel("续航: --")
        self._runtime_label.setStyleSheet("color: #e0e0e0; font-size: 13px;")
        detail_layout.addWidget(self._runtime_label)

        detail_layout.addStretch()
        layout.addLayout(detail_layout)

    def update_power_info(
        self,
        percentage: float,
        charging: bool,
        voltage: float,
        current: float,
        power_watts: float,
        runtime_minutes: float,
    ) -> None:
        """更新电源信息"""
        self._gauge.update_data(
            percentage, charging, voltage, current, power_watts, runtime_minutes
        )
        self._voltage_label.setText(f"电压: {voltage:.1f} V")
        self._current_label.setText(f"电流: {current:.1f} A")
        self._power_label.setText(f"功耗: {power_watts:.1f} W")

        if runtime_minutes > 0:
            h = int(runtime_minutes // 60)
            m = int(runtime_minutes % 60)
            self._runtime_label.setText(f"续航: {h}h{m}m")
        else:
            self._runtime_label.setText("续航: --")
