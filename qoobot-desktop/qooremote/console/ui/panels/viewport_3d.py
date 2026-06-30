"""3D 视口面板 — 机器人 URDF 模型实时姿态驱动

使用 OpenGL 渲染机器人 3D 模型，实现关节角度驱动的实时姿态同步。

对应功能 DASH-05（姿态3D可视化）。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QVector3D
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QSlider, QToolBar,
)


class Viewport3D(QFrame):
    """3D 视口面板

    提供机器人 3D 模型的实时姿态渲染。

    基础版本使用 PySide6 自带的 QPainter 进行简化的骨架渲染；
    完整版本可由 OpenGL (QOpenGLWidget) 实现 URDF 模型驱动。

    对应功能 DASH-05（姿态3D可视化）。
    """

    # 信号
    joint_selected = Signal(str)         # 关节被选中
    view_reset = Signal()               # 视图重置

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._joint_angles: dict[str, float] = {}
        self._joint_names: list[str] = []
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._rotation_z = 0.0
        self._zoom = 1.0
        self._selected_joint: Optional[str] = None
        self._show_wireframe = True
        self._show_joint_labels = True
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QToolBar()
        toolbar.setMovable(False)

        self._reset_btn = QPushButton("🔄 复位")
        self._reset_btn.clicked.connect(self._on_reset_view)
        toolbar.addWidget(self._reset_btn)

        self._wireframe_btn = QPushButton("📐 线框")
        self._wireframe_btn.setCheckable(True)
        self._wireframe_btn.setChecked(True)
        toolbar.addWidget(self._wireframe_btn)

        self._labels_btn = QPushButton("🏷️ 标签")
        self._labels_btn.setCheckable(True)
        self._labels_btn.setChecked(True)
        toolbar.addWidget(self._labels_btn)

        toolbar.addSeparator()

        zoom_label = QLabel("缩放:")
        toolbar.addWidget(zoom_label)
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 300)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(self._zoom_slider)

        layout.addWidget(toolbar)

        # 视口区域（简化渲染）
        self._viewport = _ViewportCanvas(self)
        self._viewport.setMinimumHeight(300)
        layout.addWidget(self._viewport)

        # 信息栏
        info_bar = QHBoxLayout()
        self._info_label = QLabel("关节: 0 | FPS: --")
        self._info_label.setStyleSheet("color: #888; font-size: 11px;")
        info_bar.addWidget(self._info_label)
        info_bar.addStretch()

        self._selected_label = QLabel("")
        self._selected_label.setStyleSheet("color: #3498db; font-size: 11px; font-weight: bold;")
        info_bar.addWidget(self._selected_label)
        layout.addLayout(info_bar)

    # ---- 公开方法 ----

    def update_joints(self, joint_angles: dict[str, float],
                      joint_names: Optional[list[str]] = None) -> None:
        """更新关节角度并刷新渲染

        Args:
            joint_angles: {joint_name: angle_rad}
            joint_names: 关节名称列表（用于确定顺序）
        """
        self._joint_angles = dict(joint_angles)
        if joint_names:
            self._joint_names = list(joint_names)
        elif not self._joint_names:
            self._joint_names = sorted(joint_angles.keys())

        self._viewport._joint_angles = self._joint_angles
        self._viewport._joint_names = self._joint_names
        self._viewport._rotation_x = self._rotation_x
        self._viewport._rotation_y = self._rotation_y
        self._viewport._zoom = self._zoom
        self._viewport._selected_joint = self._selected_joint
        self._viewport._show_labels = self._show_joint_labels
        self._viewport.update()

        self._info_label.setText(
            f"关节: {len(joint_angles)} | 缩放: {self._zoom:.1f}x"
        )

    def set_selected_joint(self, joint_name: Optional[str]) -> None:
        """设置选中的关节"""
        self._selected_joint = joint_name
        self._selected_label.setText(
            f"选中: {joint_name}" if joint_name else ""
        )

    def reset_view(self) -> None:
        """重置视角"""
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._rotation_z = 0.0
        self._zoom = 1.0
        self._zoom_slider.setValue(100)
        self.view_reset.emit()

    # ---- 槽 ----

    def _on_reset_view(self) -> None:
        self.reset_view()

    def _on_zoom_changed(self, value: int) -> None:
        self._zoom = value / 100.0
        self._show_wireframe = self._wireframe_btn.isChecked()
        self._show_joint_labels = self._labels_btn.isChecked()


class _ViewportCanvas(QWidget):
    """3D 视口画布 — 简化的骨架渲染"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._joint_angles: dict[str, float] = {}
        self._joint_names: list[str] = []
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._zoom = 1.0
        self._selected_joint: Optional[str] = None
        self._show_labels = True
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor("#1a1a2e"))

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        if not self._joint_names:
            painter.setPen(QColor("#888"))
            painter.setFont(QFont("sans-serif", 14))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "等待机器人连接...\n3D 姿态将在此显示")
            painter.end()
            return

        # 缩放
        scale = self._zoom * min(w, h) / 600

        # 绘制简化的骨架结构
        # 链式关节布局：从基座向末端排列
        n = len(self._joint_names)
        if n == 0:
            painter.end()
            return

        # 计算关节位置（简化：垂直链式布局）
        spacing = scale * 40
        base_x = cx
        base_y = cy + spacing * n / 2

        positions: list[tuple[float, float]] = []
        for i, name in enumerate(self._joint_names):
            angle = self._joint_angles.get(name, 0.0)
            x = base_x + angle * scale * 30
            y = base_y - i * spacing
            positions.append((x, y))

        # 绘制连接线
        pen = QPen(QColor("#3498db"), 2)
        painter.setPen(pen)
        for i in range(len(positions) - 1):
            x1, y1 = positions[i]
            x2, y2 = positions[i + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 绘制关节点
        for i, (name, (x, y)) in enumerate(zip(self._joint_names, positions)):
            is_selected = name == self._selected_joint
            radius = 10 if is_selected else 6
            color = QColor("#e74c3c") if is_selected else QColor("#2ecc71")

            painter.setBrush(color)
            painter.setPen(QPen(QColor("#fff"), 1))
            painter.drawEllipse(int(x - radius), int(y - radius),
                              int(radius * 2), int(radius * 2))

            # 标签
            if self._show_labels:
                angle = self._joint_angles.get(name, 0.0)
                label = f"{name}\n{angle:.1f}°"
                painter.setPen(QColor("#ddd"))
                painter.setFont(QFont("monospace", 8))
                painter.drawText(int(x + radius + 4), int(y + 4), label)

        # 标题
        painter.setPen(QColor("#888"))
        painter.setFont(QFont("sans-serif", 10))
        painter.drawText(10, 20, "Robot Skeleton View (simplified)")

        painter.end()
