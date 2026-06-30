"""视频渲染控件 — 单个 WebRTC 视频流渲染

负责在 QWidget 上渲染一路视频流，支持叠加信息显示
（摄像头名称、分辨率、帧率、延迟）。

对应功能 VID-01（多路视频回传）的视频渲染部分。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget, QSizePolicy

import numpy as np


class VideoWidget(QWidget):
    """单个视频渲染控件

    使用 QPainter 渲染视频帧，支持：
    - QImage 直接渲染（高效像素传输）
    - 叠加 OSD 信息（名称/分辨率/FPS/延迟）
    - 信号丢失时显示占位图
    """

    def __init__(self, camera_name: str = "Camera 1", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._camera_name = camera_name
        self._current_frame: QImage | None = None
        self._fps: float = 0.0
        self._latency_ms: float = 0.0
        self._resolution: str = "1280x720"
        self._connected: bool = False
        self._frame_count: int = 0

    def set_camera_name(self, name: str) -> None:
        self._camera_name = name

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self.update()

    def update_frame(self, frame: np.ndarray, fps: float = 0, latency_ms: float = 0) -> None:
        """更新视频帧

        Args:
            frame: BGR 或 RGB 格式的 numpy 数组 (H, W, 3)
            fps: 当前帧率
            latency_ms: 视频延迟 (ms)
        """
        h, w, ch = frame.shape
        bytes_per_line = ch * w

        if ch == 3:
            # 假设 BGR (OpenCV 默认) → 转为 RGB
            rgb = frame[..., ::-1].copy()
            fmt = QImage.Format.Format_RGB888
        else:
            rgb = frame
            fmt = QImage.Format.Format_RGBA8888

        self._current_frame = QImage(rgb.data, w, h, bytes_per_line, fmt)
        self._fps = fps
        self._latency_ms = latency_ms
        self._resolution = f"{w}x{h}"
        self._connected = True
        self._frame_count += 1
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = self.width()
        h = self.height()

        if self._current_frame and self._connected:
            # 缩放绘制帧
            scaled = self._current_frame.scaled(
                w, h, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (w - scaled.width()) // 2
            y = (h - scaled.height()) // 2
            painter.drawImage(x, y, scaled)
        else:
            # 占位画面
            painter.fillRect(0, 0, w, h, QColor("#0d1117"))
            painter.setPen(QColor("#30363d"))
            painter.drawRect(0, 0, w - 1, h - 1)

            # 中间文字
            painter.setPen(QColor("#484f58"))
            font = QFont("Segoe UI", 16)
            painter.setFont(font)
            painter.drawText(
                QRectF(0, 0, w, h),
                Qt.AlignmentFlag.AlignCenter,
                f"📷 {self._camera_name}\n无信号",
            )

        # OSD 叠加层
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.drawRect(0, 0, w, 28)

        painter.setPen(QColor("#e0e0e0"))
        font = QFont("Segoe UI", 10)
        painter.setFont(font)

        osd_text = f"{self._camera_name} | {self._resolution}"
        if self._fps > 0:
            osd_text += f" | {self._fps:.0f} FPS"
        if self._latency_ms > 0:
            osd_text += f" | {self._latency_ms:.0f}ms"
        if not self._connected:
            osd_text += " | 离线"

        painter.drawText(8, 8, w - 16, 20, Qt.AlignmentFlag.AlignLeft, osd_text)
