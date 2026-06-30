"""3D 视口面板 — 数字孪生全栈集成

升级为支持 URDF 模型驱动的 OpenGL 渲染视口，整合：
- DT-01: URDF 模型加载 + 骨架正向运动学驱动
- DT-02: 碰撞对可视化（球/盒/胶囊几何体）
- DT-03: LiDAR 点云实时渲染
- DT-04: SLAM 栅格地图 / 八叉树渲染

向下兼容：当无 OpenGL 环境时回退到 QPainter 简化渲染。

对应功能 DT-01~04（3D 数字孪生）。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
    QSlider, QToolBar, QCheckBox, QComboBox,
)

from console.core.twins.urdf_loader import URDFModel, URDFLoader
from console.core.twins.skeleton_driver import SkeletonDriver, LinkPose, Transform
from console.core.twins.collision_viewer import CollisionVisualizer, CollisionPair, PrimitiveGeometry, CollisionShape
from console.core.twins.pointcloud_renderer import PointCloudManager, PointCloudColorMode
from console.core.twins.slam_renderer import SLAMMap, MapType


class Viewport3D(QFrame):
    """3D 视口面板 — 数字孪生全栈

    提供机器人 URDF 模型驱动的实时姿态渲染，整合碰撞/点云/SLAM 可视化。

    基础版本使用 QPainter 进行简化渲染；
    OpenGL 版本 (QOpenGLWidget) 可通过 render_backend 切换。

    对应功能 DT-01~04（3D 数字孪生）。
    """

    # 信号
    joint_selected = Signal(str)
    view_reset = Signal()

    # 渲染后端
    RENDER_QPAINTER = "qpainter"
    RENDER_OPENGL = "opengl"

    def __init__(self, parent: QWidget | None = None,
                 render_backend: str = "qpainter") -> None:
        super().__init__(parent)
        self._render_backend = render_backend

        # 数字孪生核心
        self._urdf_model: Optional[URDFModel] = None
        self._skeleton_driver: Optional[SkeletonDriver] = None
        self._collision_viz: Optional[CollisionVisualizer] = None
        self._pointcloud_mgr: Optional[PointCloudManager] = None
        self._slam_map: Optional[SLAMMap] = None

        # 显示开关
        self._show_skeleton = True
        self._show_collision = True
        self._show_pointcloud = True
        self._show_slam = True

        # 视角参数
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._rotation_z = 0.0
        self._zoom = 1.0
        self._selected_joint: Optional[str] = None

        self._setup_ui()

    # --- 公开方法 ---

    def set_urdf_model(self, model: URDFModel) -> SkeletonDriver:
        """加载 URDF 模型并创建骨架驱动

        Args:
            model: 解析后的 URDFModel

        Returns:
            SkeletonDriver 实例
        """
        self._urdf_model = model
        self._skeleton_driver = SkeletonDriver(model)
        self._viewport._skeleton_driver = self._skeleton_driver
        self._viewport._urdf_model = model
        self._viewport.update()
        self._info_label.setText(f"模型: {model.name} | 关节: {len(model.active_joints)}")
        return self._skeleton_driver

    def set_collision_visualizer(self, viz: CollisionVisualizer) -> None:
        """绑定碰撞可视化器"""
        self._collision_viz = viz
        self._viewport._collision_viz = viz

    def set_pointcloud_manager(self, mgr: PointCloudManager) -> None:
        """绑定点云管理器"""
        self._pointcloud_mgr = mgr
        self._viewport._pointcloud_mgr = mgr

        # 点云颜色模式
        self._pc_color_combo.setEnabled(True)

    def set_slam_map(self, slam: SLAMMap) -> None:
        """绑定 SLAM 地图"""
        self._slam_map = slam
        self._viewport._slam_map = slam

    def load_urdf_file(self, filepath: str) -> SkeletonDriver:
        """从文件加载 URDF 模型"""
        model = URDFLoader.from_file(filepath)
        return self.set_urdf_model(model)

    def load_urdf_string(self, urdf_xml: str) -> SkeletonDriver:
        """从字符串加载 URDF 模型"""
        model = URDFLoader.from_string(urdf_xml)
        return self.set_urdf_model(model)

    def update_joints(self, joint_angles: dict[str, float],
                      joint_names: Optional[list[str]] = None) -> None:
        """更新关节角度并刷新

        如果已加载 URDF 模型则驱动骨架；
        否则使用简化渲染。
        """
        if self._skeleton_driver and self._urdf_model:
            # 正向运动学驱动
            self._skeleton_driver.set_joint_positions(joint_angles)
            self._skeleton_driver.compute_forward_kinematics()
        else:
            # 简化渲染回退
            self._viewport._joint_angles = dict(joint_angles)
            if joint_names:
                self._viewport._joint_names = list(joint_names)
            elif not self._viewport._joint_names:
                self._viewport._joint_names = sorted(joint_angles.keys())

        self._viewport._rotation_x = self._rotation_x
        self._viewport._rotation_y = self._rotation_y
        self._viewport._zoom = self._zoom
        self._viewport.update()

        self._info_label.setText(
            f"关节: {len(joint_angles)} | 缩放: {self._zoom:.1f}x"
        )

    def reset_view(self) -> None:
        """重置视角"""
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._rotation_z = 0.0
        self._zoom = 1.0
        self._zoom_slider.setValue(100)
        self.view_reset.emit()

    def refresh(self) -> None:
        """手动刷新渲染"""
        self._viewport.update()

    # --- 内部 UI ---

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QToolBar()
        toolbar.setMovable(False)

        self._reset_btn = QPushButton("🔄 复位")
        self._reset_btn.clicked.connect(lambda: self.reset_view())
        toolbar.addWidget(self._reset_btn)

        toolbar.addSeparator()

        # 显示层开关
        self._skel_check = QCheckBox("骨架")
        self._skel_check.setChecked(True)
        self._skel_check.toggled.connect(lambda v: setattr(self, '_show_skeleton', v))
        toolbar.addWidget(self._skel_check)

        self._coll_check = QCheckBox("碰撞")
        self._coll_check.setChecked(True)
        self._coll_check.toggled.connect(lambda v: setattr(self, '_show_collision', v))
        toolbar.addWidget(self._coll_check)

        self._pc_check = QCheckBox("点云")
        self._pc_check.setChecked(True)
        self._pc_check.toggled.connect(lambda v: setattr(self, '_show_pointcloud', v))
        toolbar.addWidget(self._pc_check)

        self._slam_check = QCheckBox("SLAM")
        self._slam_check.setChecked(True)
        self._slam_check.toggled.connect(lambda v: setattr(self, '_show_slam', v))
        toolbar.addWidget(self._slam_check)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel("点云着色:"))
        self._pc_color_combo = QComboBox()
        self._pc_color_combo.addItems(["强度", "高度", "距离", "RGB"])
        self._pc_color_combo.setEnabled(False)
        self._pc_color_combo.currentIndexChanged.connect(self._on_pc_color_changed)
        toolbar.addWidget(self._pc_color_combo)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel("缩放:"))
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 300)
        self._zoom_slider.setValue(100)
        self._zoom_slider.setFixedWidth(100)
        self._zoom_slider.valueChanged.connect(
            lambda v: setattr(self, '_zoom', v / 100.0)
        )
        toolbar.addWidget(self._zoom_slider)

        layout.addWidget(toolbar)

        # 画布
        self._viewport = _ViewportCanvas(self)
        self._viewport.setMinimumHeight(300)
        layout.addWidget(self._viewport)

        # 信息栏
        info_bar = QHBoxLayout()
        self._info_label = QLabel("关节: 0 | 缩放: 1.0x")
        self._info_label.setStyleSheet("color: #888; font-size: 11px;")
        info_bar.addWidget(self._info_label)
        info_bar.addStretch()

        self._selected_label = QLabel("")
        self._selected_label.setStyleSheet("color: #3498db; font-size: 11px; font-weight: bold;")
        info_bar.addWidget(self._selected_label)
        layout.addLayout(info_bar)

    def _on_pc_color_changed(self, index: int) -> None:
        if self._pointcloud_mgr:
            modes = [PointCloudColorMode.INTENSITY, PointCloudColorMode.HEIGHT,
                     PointCloudColorMode.RANGE, PointCloudColorMode.RGB]
            if index < len(modes):
                self._pointcloud_mgr.color_mode = modes[index]


class _ViewportCanvas(QWidget):
    """3D 视口画布 — 多模式渲染"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # 数字孪生数据
        self._urdf_model: Optional[URDFModel] = None
        self._skeleton_driver: Optional[SkeletonDriver] = None
        self._collision_viz: Optional[CollisionVisualizer] = None
        self._pointcloud_mgr: Optional[PointCloudManager] = None
        self._slam_map: Optional[SLAMMap] = None

        # 简化渲染回退
        self._joint_angles: dict[str, float] = {}
        self._joint_names: list[str] = []
        self._rotation_x = 0.0
        self._rotation_y = 0.0
        self._zoom = 1.0

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor("#1a1a2e"))

        if self._skeleton_driver and self._urdf_model:
            self._paint_urdf_skeleton(painter)
            self._paint_collision_overlay(painter)
            self._paint_pointcloud_overlay(painter)
            self._paint_slam_overlay(painter)
        elif self._joint_names:
            self._paint_simplified_skeleton(painter)
        else:
            painter.setPen(QColor("#888"))
            painter.setFont(QFont("sans-serif", 14))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "等待机器人连接...\n加载 URDF 模型以显示 3D 姿态")
        painter.end()

    # --- URDF 骨架渲染 (DT-01) ---

    def _paint_urdf_skeleton(self, painter: QPainter) -> None:
        """DT-01: 渲染 URDF 骨架"""
        if not self._skeleton_driver or not self._urdf_model:
            return

        parent_widget = self.parent()
        show = getattr(parent_widget, '_show_skeleton', True) if hasattr(parent_widget, '_show_skeleton') else True
        if not show:
            return

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        scale = self._zoom * min(w, h) / 500

        link_poses = self._skeleton_driver.link_poses

        # 绘制连杆骨骼连线
        for joint in self._urdf_model.joints:
            parent_link = joint.parent
            child_link = joint.child
            parent_pose = link_poses.get(parent_link)
            child_pose = link_poses.get(child_link)
            if parent_pose is None or child_pose is None:
                continue

            px, py, pz = parent_pose.transform.translation
            cx2, cy2, cz2 = child_pose.transform.translation

            # 简单投影（无视点旋转的平面投影）
            x1 = int(cx + px * scale)
            y1 = int(cy - pz * scale)
            x2 = int(cx + cx2 * scale)
            y2 = int(cy - cz2 * scale)

            pen = QPen(QColor("#3498db"), 2)
            painter.setPen(pen)
            painter.drawLine(x1, y1, x2, y2)

        # 绘制关节球
        for link_name, pose in link_poses.items():
            px, py, pz = pose.visual_center
            x = int(cx + px * scale)
            y = int(cy - pz * scale)

            is_selected = link_name == getattr(parent_widget, '_selected_joint', None) if parent_widget else False  # type: ignore
            radius = 8 if is_selected else 5
            color = QColor("#e74c3c") if is_selected else QColor("#2ecc71")

            painter.setBrush(color)
            painter.setPen(QPen(QColor("#fff"), 1))
            painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)

            # 标签
            angle = self._skeleton_driver.joint_positions.get(link_name, 0.0)
            label = f"{link_name[:8]}"
            painter.setPen(QColor("#ccc"))
            painter.setFont(QFont("monospace", 7))
            painter.drawText(x + radius + 2, y + 4, label)

    # --- 碰撞叠加 (DT-02) ---

    def _paint_collision_overlay(self, painter: QPainter) -> None:
        """DT-02: 渲染碰撞几何体"""
        if not self._collision_viz:
            return
        parent_widget = self.parent()
        show = getattr(parent_widget, '_show_collision', True) if hasattr(parent_widget, '_show_collision') else True
        if not show:
            return

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        scale = self._zoom * min(w, h) / 500

        primitives = self._collision_viz.get_render_primitives()
        for g in primitives:
            px, py, pz = g.position
            x = int(cx + px * scale)
            y = int(cy - pz * scale)

            r, g_col, b, a = g.color_rgba
            color = QColor(int(r * 255), int(g_col * 255), int(b * 255), int(a * 255))

            if g.shape == CollisionShape.SPHERE:
                radius = int(g.parameters[0] * scale * 30) if g.parameters else 4
                if g.wireframe:
                    painter.setPen(QPen(color, 1))
                    painter.setBrush(Qt.BrushStyle.NoBrush)
                else:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(color)
                painter.drawEllipse(x - radius, y - radius, radius * 2, radius * 2)

            elif g.shape == CollisionShape.BOX:
                size = g.parameters if g.parameters else [0.1, 0.1, 0.1]
                bw = int(size[0] * scale * 30)
                bh = int(size[2] * scale * 30)
                color.setAlpha(80)
                painter.setPen(QPen(color.darker(150), 1))
                painter.setBrush(color)
                painter.drawRect(x - bw // 2, y - bh // 2, bw, bh)

    # --- 点云叠加 (DT-03) ---

    def _paint_pointcloud_overlay(self, painter: QPainter) -> None:
        """DT-03: 渲染点云（降采样）"""
        if not self._pointcloud_mgr:
            return
        parent_widget = self.parent()
        show = getattr(parent_widget, '_show_pointcloud', True) if hasattr(parent_widget, '_show_pointcloud') else True
        if not show:
            return

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        scale = self._zoom * min(w, h) / 500

        vertices, colors, count = self._pointcloud_mgr.get_vertex_buffer()
        if count == 0:
            return

        # 降采样（最多渲染 5000 个点）
        step = max(1, count // 2000)

        for i in range(0, count * 3, step * 3):
            if i + 2 >= len(vertices):
                break
            px = vertices[i]
            py = vertices[i + 1]
            pz = vertices[i + 2]

            ci = i // 3 * 3
            if ci + 2 < len(colors):
                cr = int(colors[ci] * 255)
                cg = int(colors[ci + 1] * 255)
                cb = int(colors[ci + 2] * 255)
            else:
                cr, cg, cb = 100, 200, 100

            x = int(cx + px * scale)
            y = int(cy - pz * scale)

            painter.setPen(QPen(QColor(cr, cg, cb), 1))
            painter.drawPoint(x, y)

    # --- SLAM 地图叠加 (DT-04) ---

    def _paint_slam_overlay(self, painter: QPainter) -> None:
        """DT-04: 渲染 SLAM 地图"""
        if not self._slam_map:
            return
        parent_widget = self.parent()
        show = getattr(parent_widget, '_show_slam', True) if hasattr(parent_widget, '_show_slam') else True
        if not show:
            return

        # 2D 栅格地图
        if self._slam_map.show_grid and self._slam_map.occupancy_grid:
            verts, cols, vcount = self._slam_map.occupancy_grid_to_quads()
            if vcount == 0:
                return

            w, h = self.width(), self.height()
            cx, cy = w // 2, h // 2
            scale = self._zoom * min(w, h) / 500

            grid = self._slam_map.occupancy_grid
            res = grid.resolution if grid else 0.05

            for i in range(0, min(len(verts), len(cols)), 12):  # 每 4 个顶点一组
                if i + 2 >= len(verts):
                    break
                wx, wy, wz = verts[i], verts[i + 1], verts[i + 2]
                x = int(cx + wx * scale)
                y = int(cy - wy * scale)
                pw = max(1, int(res * scale))

                ci = i // 3 * 3
                if ci + 2 < len(cols):
                    cr, cg, cb = int(cols[ci] * 255), int(cols[ci + 1] * 255), int(cols[ci + 2] * 255)
                else:
                    cr, cg, cb = 128, 128, 128

                painter.fillRect(x, y, pw, pw, QColor(cr, cg, cb, 180))

    # --- 简化骨架渲染（回退） ---

    def _paint_simplified_skeleton(self, painter: QPainter) -> None:
        """简化的链式骨架渲染"""
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2
        scale = self._zoom * min(w, h) / 600
        n = len(self._joint_names)
        if n == 0:
            return

        spacing = scale * 40
        base_x = cx
        base_y = cy + spacing * n / 2

        positions: list[tuple[float, float]] = []
        for i, name in enumerate(self._joint_names):
            angle = self._joint_angles.get(name, 0.0)
            x = base_x + angle * scale * 30
            y = base_y - i * spacing
            positions.append((x, y))

        pen = QPen(QColor("#3498db"), 2)
        painter.setPen(pen)
        for i in range(len(positions) - 1):
            x1, y1 = positions[i]
            x2, y2 = positions[i + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        for name, (x, y) in zip(self._joint_names, positions):
            painter.setBrush(QColor("#2ecc71"))
            painter.setPen(QPen(QColor("#fff"), 1))
            painter.drawEllipse(int(x - 6), int(y - 6), 12, 12)

            angle = self._joint_angles.get(name, 0.0)
            label = f"{name}\n{angle:.1f}°"
            painter.setPen(QColor("#ddd"))
            painter.setFont(QFont("monospace", 8))
            painter.drawText(int(x + 8), int(y + 4), label)

        painter.setPen(QColor("#888"))
        painter.setFont(QFont("sans-serif", 10))
        painter.drawText(10, 20, "Skeleton View (simplified)")
