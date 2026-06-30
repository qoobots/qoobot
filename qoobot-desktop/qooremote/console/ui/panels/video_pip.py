"""画中画模式 — 多路视频叠加窗口

在视频网格布局基础上提供画中画 (PiP) 叠加窗口：
- 可拖拽的浮动小窗口
- PIP 源视频与目标视频可切换
- 透明度调节
- 窗口位置记忆

对应功能 VID-04（画中画模式）。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QRect, QPoint, QSize, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QMouseEvent, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QSlider, QLabel, QComboBox, QCheckBox,
)


class PipOverlay(QWidget):
    """画中画叠加层 — 可拖拽的浮动视频小窗

    特征：
    - 鼠标拖拽移动
    - 透明度调节
    - 尺寸缩放 (1/4, 1/6, 1/9 主窗口大小)
    - 边框高亮
    """

    # 信号
    position_changed = Signal(int, int)     # (x, y) 相对位置
    closed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dragging = False
        self._drag_offset = QPoint()
        self._opacity = 0.85
        self._corner_radius = 8
        self._size_ratio = 0.25             # 占主窗口 1/4

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(f"""
            PipOverlay {{
                background-color: rgba(30, 30, 46, {self._opacity});
                border: 2px solid #3498db;
                border-radius: {self._corner_radius}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        # 标题栏
        title_bar = QHBoxLayout()
        self._title_label = QLabel("PiP")
        self._title_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 10px;")
        title_bar.addWidget(self._title_label)
        title_bar.addStretch()

        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(16, 16)
        self._close_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #e74c3c; border: none; font-size: 12px; }
            QPushButton:hover { color: #c0392b; }
        """)
        self._close_btn.clicked.connect(self.close_pip)
        title_bar.addWidget(self._close_btn)

        layout.addLayout(title_bar)

        # 内容占位（实际视频渲染区域）
        self._content = QWidget()
        self._content.setStyleSheet("background-color: #1a1a2e;")
        self._content.setMinimumSize(160, 120)
        layout.addWidget(self._content)

    def set_title(self, title: str) -> None:
        self._title_label.setText(title)

    def set_opacity(self, opacity: float) -> None:
        self._opacity = max(0.3, min(1.0, opacity))
        self.setStyleSheet(f"""
            PipOverlay {{
                background-color: rgba(30, 30, 46, {self._opacity});
                border: 2px solid #3498db;
                border-radius: {self._corner_radius}px;
            }}
        """)

    def set_size_ratio(self, ratio: float) -> None:
        """设置窗口大小比例 (相对父窗口)"""
        self._size_ratio = max(0.1, min(0.5, ratio))
        if self.parent():
            self._resize_to_ratio()

    def _resize_to_ratio(self) -> None:
        if not self.parent():
            return
        pw = self.parent().width()
        ph = self.parent().height()
        w = int(pw * self._size_ratio)
        h = int(w * 0.75)  # 4:3 比例
        self.resize(w, h)

    def close_pip(self) -> None:
        """关闭 PiP"""
        self.hide()
        self.closed.emit()

    # --- 拖拽 ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            new_pos = self.mapToParent(event.pos() - self._drag_offset)
            # 限制在父窗口范围内
            if self.parent():
                pw = self.parent().width()
                ph = self.parent().height()
                new_x = max(0, min(pw - self.width(), new_pos.x()))
                new_y = max(0, min(ph - self.height(), new_pos.y()))
                self.move(new_x, new_y)
                self.position_changed.emit(new_x, new_y)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._dragging = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._size_ratio = self.width() / max(1, self.parent().width()) if self.parent() else 0.25


class PipControlBar(QWidget):
    """画中画控制栏

    提供 PiP 开关、源视频选择、透明度/大小调节。
    """

    pip_toggled = Signal(bool)              # PiP 开/关
    source_changed = Signal(int)            # 源视频索引
    opacity_changed = Signal(float)         # 透明度
    size_changed = Signal(float)            # 尺寸比例

    def __init__(self, camera_count: int = 4, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._camera_count = camera_count

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # PiP 开关
        self._pip_checkbox = QCheckBox("PiP")
        self._pip_checkbox.setStyleSheet("color: #ddd; font-weight: bold;")
        self._pip_checkbox.toggled.connect(self.pip_toggled.emit)
        layout.addWidget(self._pip_checkbox)

        # 源视频选择
        layout.addWidget(QLabel("源:"))
        self._source_combo = QComboBox()
        for i in range(camera_count):
            self._source_combo.addItem(f"摄像头 {i + 1}", i)
        self._source_combo.currentIndexChanged.connect(
            lambda idx: self.source_changed.emit(idx)
        )
        layout.addWidget(self._source_combo)

        # 透明度
        layout.addWidget(QLabel("透明:"))
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        self._opacity_slider.setValue(85)
        self._opacity_slider.setFixedWidth(60)
        self._opacity_slider.valueChanged.connect(
            lambda v: self.opacity_changed.emit(v / 100.0)
        )
        layout.addWidget(self._opacity_slider)

        # 尺寸
        layout.addWidget(QLabel("尺寸:"))
        self._size_combo = QComboBox()
        self._size_combo.addItems(["1/4", "1/6", "1/9", "1/3"])
        self._size_combo.currentIndexChanged.connect(self._on_size_changed)
        layout.addWidget(self._size_combo)

        layout.addStretch()

    def _on_size_changed(self, index: int) -> None:
        ratios = {0: 0.25, 1: 1/6, 2: 1/9, 3: 1/3}
        self.size_changed.emit(ratios.get(index, 0.25))

    @property
    def is_pip_enabled(self) -> bool:
        return self._pip_checkbox.isChecked()

    def set_pip_enabled(self, enabled: bool) -> None:
        self._pip_checkbox.setChecked(enabled)
