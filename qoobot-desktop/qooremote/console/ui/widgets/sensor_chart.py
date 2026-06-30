"""传感器曲线图控件 — 实时传感器数据可视化

使用 pyqtgraph 绘制 IMU/力传感器等实时数据曲线。
支持多通道叠加显示、自动滚动和自适应缩放。

对应功能 DASH-03（传感器数据面板）。
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from console.core.models.robot_state import ImuData, ForceData


class SensorChart(QWidget):
    """传感器实时曲线图

    使用 pyqtgraph 绘制实时传感器数据，
    支持 IMU 和力传感器多通道显示。
    """

    MAX_HISTORY = 300  # 最大历史数据点

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 通道选择工具栏
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("传感器:"))

        self._channel_combo = QComboBox()
        self._channel_combo.addItems([
            "IMU 加速度 (X)",
            "IMU 加速度 (Y)",
            "IMU 加速度 (Z)",
            "IMU 角速度 (X)",
            "IMU 角速度 (Y)",
            "IMU 角速度 (Z)",
            "IMU 姿态 (Roll)",
            "IMU 姿态 (Pitch)",
            "IMU 姿态 (Yaw)",
            "力传感器",
        ])
        self._channel_combo.currentIndexChanged.connect(self._on_channel_changed)
        toolbar.addWidget(self._channel_combo)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # pyqtgraph 绘图控件
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground("#1a1a2e")
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel("left", "值")
        self._plot_widget.setLabel("bottom", "采样点")
        self._plot_widget.setMouseEnabled(x=True, y=True)
        layout.addWidget(self._plot_widget)

        # 数据缓存
        self._history: dict[str, deque[float]] = {
            name: deque(maxlen=self.MAX_HISTORY)
            for name in [
                "accel_x", "accel_y", "accel_z",
                "gyro_x", "gyro_y", "gyro_z",
                "roll", "pitch", "yaw",
            ]
        }
        self._force_history: dict[str, deque[float]] = {}
        self._current_channel = 0

        # 创建曲线
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(color="#64b5f6", width=1.5),
            name="sensor",
        )
        self._force_curves: dict[str, pg.PlotDataItem] = {}

    def update_imu(self, imu: ImuData) -> None:
        """更新 IMU 数据"""
        self._history["accel_x"].append(imu.linear_acceleration.x)
        self._history["accel_y"].append(imu.linear_acceleration.y)
        self._history["accel_z"].append(imu.linear_acceleration.z)
        self._history["gyro_x"].append(imu.angular_velocity.x)
        self._history["gyro_y"].append(imu.angular_velocity.y)
        self._history["gyro_z"].append(imu.angular_velocity.z)
        # 从四元数提取欧拉角（简化）
        q = imu.orientation
        self._history["roll"].append(
            np.arctan2(2*(q.w*q.x + q.y*q.z), 1 - 2*(q.x*q.x + q.y*q.y))
        )
        self._history["pitch"].append(
            np.arcsin(2*(q.w*q.y - q.z*q.x))
        )
        self._history["yaw"].append(
            np.arctan2(2*(q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))
        )

        # 只在 IMU 相关通道时刷新
        if self._current_channel < 9:
            self._refresh_plot()

    def update_forces(self, forces: list[ForceData]) -> None:
        """更新力传感器数据"""
        for f in forces:
            if f.sensor not in self._force_history:
                self._force_history[f.sensor] = deque(maxlen=self.MAX_HISTORY)
            self._force_history[f.sensor].append(f.value_n)

        if self._current_channel == 9:
            self._refresh_force_plot()

    def _on_channel_changed(self, index: int) -> None:
        """通道切换"""
        self._current_channel = index
        self._plot_widget.clear()
        self._curve = self._plot_widget.plot(
            pen=pg.mkPen(color="#64b5f6", width=1.5),
        )
        self._force_curves.clear()

        if index < 9:
            self._refresh_plot()
        else:
            self._refresh_force_plot()

    def _refresh_plot(self) -> None:
        """刷新 IMU 曲线"""
        channel_map = {
            0: "accel_x", 1: "accel_y", 2: "accel_z",
            3: "gyro_x", 4: "gyro_y", 5: "gyro_z",
            6: "roll", 7: "pitch", 8: "yaw",
        }
        key = channel_map.get(self._current_channel, "accel_x")
        data = list(self._history[key])
        if data:
            self._curve.setData(data)

    def _refresh_force_plot(self) -> None:
        """刷新力传感器曲线"""
        colors = ["#2ecc71", "#e74c3c", "#f39c12", "#3498db", "#9b59b6"]
        for i, (name, history) in enumerate(self._force_history.items()):
            if name not in self._force_curves:
                pen = pg.mkPen(color=colors[i % len(colors)], width=1.5)
                self._force_curves[name] = self._plot_widget.plot(
                    pen=pen, name=name
                )
            self._force_curves[name].setData(list(history))
