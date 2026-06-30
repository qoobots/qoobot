"""状态卡片控件 — 用于显示系统状态指标

显示 CPU、内存、磁盘、温度等系统资源状态，
以卡片形式呈现，带颜色编码的进度条和数值显示。

对应功能 DASH-01（机器人状态总览）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from console.core.utils.units import bytes_to_human


@dataclass
class StatusCardData:
    """状态卡片数据"""
    title: str = ""
    value: str = ""
    value_unit: str = ""
    percentage: float = 0.0        # 0-100
    sub_text: str = ""
    status: str = "normal"         # normal, warning, error


class StatusCard(QFrame):
    """状态卡片

    通用状态指标显示卡片，支持：
    - 标题 + 大数值
    - 彩色进度条（根据百分比自动变色）
    - 副文本描述
    - normal/warning/error 三色状态指示
    """

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 标题
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet("color: #90a4ae; font-size: 11px;")
        layout.addWidget(self._title_label)

        # 数值行
        value_layout = QHBoxLayout()
        value_layout.setSpacing(4)

        self._value_label = QLabel("--")
        self._value_label.setObjectName("valueLabel")
        value_layout.addWidget(self._value_label)

        self._unit_label = QLabel("")
        self._unit_label.setStyleSheet("color: #90a4ae; font-size: 12px;")
        value_layout.addWidget(self._unit_label)

        value_layout.addStretch()
        layout.addLayout(value_layout)

        # 进度条
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        layout.addWidget(self._progress_bar)

        # 副文本
        self._sub_label = QLabel("")
        self._sub_label.setStyleSheet("color: #718093; font-size: 10px;")
        layout.addWidget(self._sub_label)

    def update_data(self, data: StatusCardData) -> None:
        """更新卡片数据"""
        self._title_label.setText(data.title)
        self._value_label.setText(data.value)
        self._unit_label.setText(data.value_unit)
        self._progress_bar.setValue(int(data.percentage))
        self._sub_label.setText(data.sub_text)

        # 根据百分比调整进度条颜色
        if data.percentage >= 90:
            color = "#e74c3c"  # 红色: 高负载
        elif data.percentage >= 70:
            color = "#f39c12"  # 黄色: 中负载
        else:
            color = "#2ecc71"  # 绿色: 正常

        self._progress_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}"
        )

        # 根据状态调整数值颜色
        status_colors = {
            "normal": "#e0e0e0",
            "warning": "#f39c12",
            "error": "#e74c3c",
        }
        self._value_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {status_colors.get(data.status, '#e0e0e0')};"
        )

    @classmethod
    def for_cpu(cls, cpu_percent: float) -> StatusCard:
        """创建 CPU 状态卡片"""
        card = cls("CPU 使用率")
        status = "normal"
        if cpu_percent > 90:
            status = "error"
        elif cpu_percent > 70:
            status = "warning"

        card.update_data(StatusCardData(
            title="CPU 使用率",
            value=f"{cpu_percent:.1f}",
            value_unit="%",
            percentage=cpu_percent,
            sub_text=f"{cpu_percent:.0f}% 占用",
            status=status,
        ))
        return card

    @classmethod
    def for_memory(cls, used_mb: float, total_mb: float) -> StatusCard:
        """创建内存状态卡片"""
        pct = (used_mb / total_mb * 100) if total_mb > 0 else 0
        status = "normal"
        if pct > 90:
            status = "error"
        elif pct > 70:
            status = "warning"

        card = cls("内存使用")
        card.update_data(StatusCardData(
            title="内存使用",
            value=f"{used_mb / 1024:.1f}" if used_mb >= 1024 else f"{used_mb:.0f}",
            value_unit="GB" if used_mb >= 1024 else "MB",
            percentage=pct,
            sub_text=f"{bytes_to_human(int(used_mb * 1024 * 1024))} / "
                     f"{bytes_to_human(int(total_mb * 1024 * 1024))}",
            status=status,
        ))
        return card

    @classmethod
    def for_disk(cls, used_gb: float, total_gb: float) -> StatusCard:
        """创建磁盘状态卡片"""
        pct = (used_gb / total_gb * 100) if total_gb > 0 else 0
        status = "normal"
        if pct > 90:
            status = "error"
        elif pct > 70:
            status = "warning"

        card = cls("磁盘使用")
        card.update_data(StatusCardData(
            title="磁盘使用",
            value=f"{used_gb:.1f}",
            value_unit="GB",
            percentage=pct,
            sub_text=f"{used_gb:.1f} / {total_gb:.0f} GB",
            status=status,
        ))
        return card

    @classmethod
    def for_temperature(cls, soc_temp: float, ambient_temp: float = 0) -> StatusCard:
        """创建温度状态卡片"""
        status = "normal"
        if soc_temp > 85:
            status = "error"
        elif soc_temp > 70:
            status = "warning"

        card = cls("SoC 温度")
        card.update_data(StatusCardData(
            title="SoC 温度",
            value=f"{soc_temp:.1f}",
            value_unit="°C",
            percentage=min(soc_temp / 100 * 100, 100),
            sub_text=f"环境 {ambient_temp:.1f}°C" if ambient_temp else "温度正常",
            status=status,
        ))
        return card

    @classmethod
    def for_uptime(cls, uptime_seconds: float) -> StatusCard:
        """创建运行时间卡片"""
        hours = uptime_seconds / 3600
        days = int(hours // 24)
        hrs = int(hours % 24)
        mins = int((uptime_seconds % 3600) // 60)

        if days > 0:
            value = f"{days}"
            unit = "天"
            sub = f"{days}d {hrs}h {mins}m"
        elif hrs > 0:
            value = f"{hrs}"
            unit = "小时"
            sub = f"{hrs}h {mins}m"
        else:
            value = f"{mins}"
            unit = "分钟"
            sub = f"运行 {mins} 分钟"

        card = cls("运行时间")
        card.update_data(StatusCardData(
            title="运行时间",
            value=value,
            value_unit=unit,
            percentage=min(hours / 720 * 100, 100),  # 720h = 30d
            sub_text=sub,
            status="normal",
        ))
        return card
