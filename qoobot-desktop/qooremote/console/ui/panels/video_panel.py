"""视频面板 — 多路视频网格布局

管理多路视频流的布局和渲染，支持：
- 1/4/9 宫格视频布局切换
- 单路全屏
- 码率/帧率/分辨率显示

对应功能 VID-01（多路视频回传）。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from console.ui.panels.video_widget import VideoWidget


class VideoPanel(QWidget):
    """视频面板

    管理多路视频渲染控件的网格布局。
    支持布局切换、单路全屏等操作。
    """

    def __init__(self, camera_count: int = 4, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._camera_count = camera_count
        self._current_layout: int = 4  # 默认 2×2
        self._video_widgets: list[VideoWidget] = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # 工具栏
        toolbar = QHBoxLayout()

        self._layout_combo = QComboBox()
        self._layout_combo.addItems(["1×1 单路", "2×2 四路", "3×3 九路"])
        self._layout_combo.currentIndexChanged.connect(self._on_layout_changed)
        toolbar.addWidget(QLabel("布局:"))
        toolbar.addWidget(self._layout_combo)

        self._bitrate_label = QLabel("码率: -- Mbps")
        toolbar.addWidget(self._bitrate_label)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # 视频网格
        self._grid = QGridLayout()
        self._grid.setSpacing(2)
        main_layout.addLayout(self._grid, stretch=1)

        # 创建视频控件
        for i in range(min(self._camera_count, 9)):
            video = VideoWidget(f"Camera {i + 1}")
            self._video_widgets.append(video)

        self._apply_grid_layout(4)

    @property
    def video_widgets(self) -> list[VideoWidget]:
        return self._video_widgets

    def get_video(self, index: int) -> Optional[VideoWidget]:
        """获取指定索引的视频控件"""
        if 0 <= index < len(self._video_widgets):
            return self._video_widgets[index]
        return None

    def update_bitrate(self, bitrate_mbps: float) -> None:
        self._bitrate_label.setText(f"码率: {bitrate_mbps:.1f} Mbps")

    def _on_layout_changed(self, index: int) -> None:
        """布局切换"""
        layouts = {0: 1, 1: 4, 2: 9}
        count = layouts.get(index, 4)
        self._apply_grid_layout(count)

    def _apply_grid_layout(self, count: int) -> None:
        """应用网格布局"""
        # 清除现有布局
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if count == 1:
            cols, rows = 1, 1
        elif count == 4:
            cols, rows = 2, 2
        else:  # 9
            cols, rows = 3, 3

        for i in range(min(count, len(self._video_widgets))):
            row = i // cols
            col = i % cols
            self._grid.addWidget(self._video_widgets[i], row, col)

        self._current_layout = count
