"""主窗口 — QooRemote 桌面控制台主框架

包含菜单栏、工具栏、中央工作区（可拖拽面板布局）、状态栏。
采用 QMainWindow + QDockWidget 架构，支持自定义布局。

对应功能：TAK-02（紧急制动按钮）集成在工具栏中。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QColor
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QLabel,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QWidget,
    QVBoxLayout,
)

from console.core.models.robot_state import RobotState
from console.core.signaling.client import ConnectionState, SignalingClient

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """主窗口

    QooRemote 桌面控制台的顶层窗口，管理：
    - 菜单栏（连接/视图/录制/设置/帮助）
    - 工具栏（连接/紧急制动/录制/截图/语音）
    - 中央工作区（视频面板 + 仪表盘 + 操控面板）
    - 状态栏（连接状态/延迟/视频码率/录制状态/告警计数）
    """

    # 信号
    connect_requested = Signal()
    disconnect_requested = Signal()
    emergency_stop_requested = Signal(str)  # reason
    recording_toggle_requested = Signal()
    screenshot_requested = Signal()
    theme_changed = Signal(str)  # "dark" | "light"
    layout_changed = Signal(str)  # layout preset name

    APP_TITLE = "QooRemote — 远程机器人监控遥控控制台"
    ORG_NAME = "QooBot"
    APP_NAME = "qooremote"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_theme = "dark"
        self._signal_connected = False
        self._offline_timer: Optional[QTimer] = None

        self._setup_window()
        self._setup_menu_bar()
        self._setup_tool_bar()
        self._setup_central_widget()
        self._setup_status_bar()
        self._apply_theme(self._current_theme)

    # ------------------------------------------------------------------
    # 窗口初始化
    # ------------------------------------------------------------------

    def _setup_window(self) -> None:
        """初始化窗口属性"""
        self.setWindowTitle(self.APP_TITLE)
        self.resize(1400, 900)
        self.setMinimumSize(1024, 600)

        # 窗口居中
        screen = QApplication.primaryScreen()
        if screen:
            center = screen.availableGeometry().center()
            frame = self.frameGeometry()
            frame.moveCenter(center)
            self.move(frame.topLeft())

    # ------------------------------------------------------------------
    # 菜单栏
    # ------------------------------------------------------------------

    def _setup_menu_bar(self) -> None:
        """构建菜单栏"""
        menu_bar = self.menuBar()

        # --- 连接菜单 ---
        connection_menu = menu_bar.addMenu("连接(&C)")

        self._action_connect = QAction("连接机器人...", self)
        self._action_connect.setShortcut(QKeySequence("Ctrl+O"))
        self._action_connect.triggered.connect(self._on_connect)
        connection_menu.addAction(self._action_connect)

        self._action_disconnect = QAction("断开连接", self)
        self._action_disconnect.setShortcut(QKeySequence("Ctrl+D"))
        self._action_disconnect.setEnabled(False)
        self._action_disconnect.triggered.connect(self._on_disconnect)
        connection_menu.addAction(self._action_disconnect)

        connection_menu.addSeparator()

        self._action_robot_list = QAction("机器人列表...", self)
        self._action_robot_list.triggered.connect(self._on_robot_list)
        connection_menu.addAction(self._action_robot_list)

        connection_menu.addSeparator()

        self._action_exit = QAction("退出(&Q)", self)
        self._action_exit.setShortcut(QKeySequence("Alt+F4"))
        self._action_exit.triggered.connect(self.close)
        connection_menu.addAction(self._action_exit)

        # --- 视图菜单 ---
        view_menu = menu_bar.addMenu("视图(&V)")

        self._action_fullscreen = QAction("全屏", self)
        self._action_fullscreen.setShortcut(QKeySequence("F11"))
        self._action_fullscreen.setCheckable(True)
        self._action_fullscreen.triggered.connect(self._on_fullscreen)
        view_menu.addAction(self._action_fullscreen)

        view_menu.addSeparator()

        self._action_dark_theme = QAction("暗色主题", self)
        self._action_dark_theme.setCheckable(True)
        self._action_dark_theme.setChecked(True)
        self._action_dark_theme.triggered.connect(
            lambda: self._apply_theme("dark")
        )
        view_menu.addAction(self._action_dark_theme)

        self._action_light_theme = QAction("亮色主题", self)
        self._action_light_theme.setCheckable(True)
        self._action_light_theme.triggered.connect(
            lambda: self._apply_theme("light")
        )
        view_menu.addAction(self._action_light_theme)

        view_menu.addSeparator()

        layout_menu = view_menu.addMenu("布局预设")
        for preset in ("standard", "teleop", "recording", "immersive"):
            action = QAction(preset.capitalize(), self)
            action.triggered.connect(
                lambda checked, p=preset: self._on_layout_preset(p)
            )
            layout_menu.addAction(action)

        # --- 工具菜单 ---
        tools_menu = menu_bar.addMenu("工具(&T)")

        self._action_settings = QAction("偏好设置...", self)
        self._action_settings.setShortcut(QKeySequence("Ctrl+,"))
        self._action_settings.triggered.connect(self._on_settings)
        tools_menu.addAction(self._action_settings)

        tools_menu.addSeparator()

        self._action_screenshot = QAction("截图", self)
        self._action_screenshot.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._action_screenshot.triggered.connect(
            lambda: self.screenshot_requested.emit()
        )
        tools_menu.addAction(self._action_screenshot)

        # --- 帮助菜单 ---
        help_menu = menu_bar.addMenu("帮助(&H)")

        self._action_docs = QAction("开发文档", self)
        self._action_docs.triggered.connect(self._on_docs)
        help_menu.addAction(self._action_docs)

        self._action_about = QAction("关于 QooRemote", self)
        self._action_about.triggered.connect(self._on_about)
        help_menu.addAction(self._action_about)

    # ------------------------------------------------------------------
    # 工具栏
    # ------------------------------------------------------------------

    def _setup_tool_bar(self) -> None:
        """构建工具栏"""
        tool_bar = QToolBar("主工具栏")
        tool_bar.setObjectName("mainToolBar")
        tool_bar.setMovable(False)
        self.addToolBar(tool_bar)

        # 连接按钮
        self._btn_connect = tool_bar.addAction("连接")
        self._btn_connect.triggered.connect(self._on_connect)

        tool_bar.addSeparator()

        # 紧急制动按钮 — TAK-02
        self._btn_emergency = QAction("紧急制动", self)
        self._btn_emergency.setToolTip("紧急制动 — 立即停止机器人所有运动 (Space)")
        # 通过 QSS #emergencyButton 样式设置为红色醒目
        tool_bar.addAction(self._btn_emergency)
        self._btn_emergency.triggered.connect(
            lambda: self._on_emergency_stop()
        )

        tool_bar.addSeparator()

        # 录制控制
        self._btn_recording = tool_bar.addAction("录制")
        self._btn_recording.setCheckable(True)
        self._btn_recording.triggered.connect(
            lambda: self.recording_toggle_requested.emit()
        )

        # 截图
        self._btn_screenshot = tool_bar.addAction("截图")
        self._btn_screenshot.triggered.connect(
            lambda: self.screenshot_requested.emit()
        )

        tool_bar.addSeparator()

        # 语音开关
        self._btn_voice = tool_bar.addAction("语音")
        self._btn_voice.setCheckable(True)

    # ------------------------------------------------------------------
    # 中央工作区
    # ------------------------------------------------------------------

    def _setup_central_widget(self) -> None:
        """构建中央工作区（可拖拽面板布局）"""
        # 创建中心分割器
        central_splitter = QSplitter(Qt.Orientation.Horizontal)
        central_splitter.setObjectName("centralSplitter")
        self.setCentralWidget(central_splitter)

        # 视频面板占位
        self._video_container = QWidget()
        self._video_container.setObjectName("videoContainer")
        video_layout = QVBoxLayout(self._video_container)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_placeholder = QLabel("视频面板")
        video_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_placeholder.setStyleSheet("color: #90a4ae; font-size: 18px;")
        video_layout.addWidget(video_placeholder)
        central_splitter.addWidget(self._video_container)

        # 仪表盘面板占位
        self._dashboard_container = QWidget()
        self._dashboard_container.setObjectName("dashboardContainer")
        dash_layout = QVBoxLayout(self._dashboard_container)
        dash_layout.setContentsMargins(0, 0, 0, 0)
        dash_placeholder = QLabel("仪表盘面板")
        dash_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dash_placeholder.setStyleSheet("color: #90a4ae; font-size: 18px;")
        dash_layout.addWidget(dash_placeholder)
        central_splitter.addWidget(self._dashboard_container)

        # 设置分割比例
        central_splitter.setSizes([700, 500])

    # ------------------------------------------------------------------
    # 状态栏
    # ------------------------------------------------------------------

    def _setup_status_bar(self) -> None:
        """构建状态栏"""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        # 连接状态
        self._label_connection = QLabel("⬤ 未连接")
        self._status_bar.addWidget(self._label_connection)

        # 延迟
        self._label_latency = QLabel("延迟: -- ms")
        self._status_bar.addWidget(self._label_latency)

        # 视频码率
        self._label_bitrate = QLabel("视频: -- Mbps")
        self._status_bar.addWidget(self._label_bitrate)

        # 录制状态
        self._label_recording = QLabel("")
        self._status_bar.addWidget(self._label_recording)

        # 告警计数
        self._label_alerts = QLabel("")
        self._status_bar.addPermanentWidget(self._label_alerts)

    # ------------------------------------------------------------------
    # 公共方法
    # ------------------------------------------------------------------

    def update_connection_state(self, state: ConnectionState) -> None:
        """更新连接状态显示"""
        state_map = {
            ConnectionState.DISCONNECTED: ("⬤ 未连接", "gray"),
            ConnectionState.CONNECTING: ("◉ 连接中...", "#f39c12"),
            ConnectionState.CONNECTED: ("◉ 已连接", "#3498db"),
            ConnectionState.AUTHENTICATED: ("◉ 已认证", "#2ecc71"),
            ConnectionState.SESSION_ACTIVE: ("● 会话活跃", "#2ecc71"),
            ConnectionState.RECONNECTING: ("⟳ 重连中...", "#e67e22"),
        }
        text, color = state_map.get(state, ("⬤ 未知", "gray"))
        self._label_connection.setText(text)
        self._label_connection.setStyleSheet(f"color: {color}; font-weight: bold;")

        # 更新菜单状态
        is_connected = state in (ConnectionState.CONNECTED,
                                 ConnectionState.AUTHENTICATED,
                                 ConnectionState.SESSION_ACTIVE)
        self._action_connect.setEnabled(not is_connected)
        self._action_disconnect.setEnabled(is_connected)

    def update_latency(self, latency_ms: float) -> None:
        """更新延迟显示"""
        self._label_latency.setText(f"延迟: {latency_ms:.0f} ms")
        if latency_ms < 50:
            color = "#2ecc71"
        elif latency_ms < 200:
            color = "#f39c12"
        else:
            color = "#e74c3c"
        self._label_latency.setStyleSheet(f"color: {color};")

    def update_video_bitrate(self, bitrate_mbps: float) -> None:
        """更新视频码率显示"""
        self._label_bitrate.setText(f"视频: {bitrate_mbps:.1f} Mbps")

    def update_recording_state(self, is_recording: bool, duration_seconds: int = 0) -> None:
        """更新录制状态显示"""
        if is_recording:
            m = duration_seconds // 60
            s = duration_seconds % 60
            self._label_recording.setText(f"⏺ 录制中 {m:02d}:{s:02d}")
            self._label_recording.setStyleSheet("color: #e74c3c; font-weight: bold;")
        else:
            self._label_recording.setText("")

    def update_alert_count(self, total: int, critical: int) -> None:
        """更新告警计数显示"""
        if total == 0:
            self._label_alerts.setText("")
        else:
            text = f"🔔 {total} 条告警"
            if critical > 0:
                text += f" ({critical} 严重)"
            self._label_alerts.setText(text)
            self._label_alerts.setStyleSheet("color: #e74c3c; font-weight: bold;")

    def set_dashboard_widget(self, widget: QWidget) -> None:
        """替换仪表盘面板占位"""
        old_layout = self._dashboard_container.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            old_layout.addWidget(widget)

    def set_video_widget(self, widget: QWidget) -> None:
        """替换视频面板占位"""
        old_layout = self._video_container.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            old_layout.addWidget(widget)

    # ------------------------------------------------------------------
    # 主题管理
    # ------------------------------------------------------------------

    def _apply_theme(self, theme: str) -> None:
        """应用主题样式表"""
        self._current_theme = theme
        self._action_dark_theme.setChecked(theme == "dark")
        self._action_light_theme.setChecked(theme == "light")

        style_dir = Path(__file__).parent / "resources" / "styles"
        qss_file = style_dir / f"{theme}.qss"
        if qss_file.exists():
            with open(qss_file, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        self.theme_changed.emit(theme)

    # ------------------------------------------------------------------
    # 槽函数
    # ------------------------------------------------------------------

    def _on_connect(self) -> None:
        """连接按钮/菜单槽"""
        self.connect_requested.emit()

    def _on_disconnect(self) -> None:
        """断开连接槽"""
        self.disconnect_requested.emit()

    def _on_robot_list(self) -> None:
        """机器人列表槽"""
        QMessageBox.information(self, "机器人列表", "功能开发中...")

    def _on_emergency_stop(self) -> None:
        """紧急制动槽 — TAK-02"""
        reply = QMessageBox.warning(
            self,
            "紧急制动",
            "确认执行紧急制动？\n\n⚠ 这将立即停止机器人所有运动！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.emergency_stop_requested.emit("ui_button")

    def _on_fullscreen(self, checked: bool) -> None:
        """全屏切换"""
        if checked:
            self.showFullScreen()
        else:
            self.showNormal()

    def _on_layout_preset(self, preset: str) -> None:
        """布局预设切换"""
        self.layout_changed.emit(preset)
        QMessageBox.information(self, "布局切换", f"切换到布局: {preset}")

    def _on_settings(self) -> None:
        """偏好设置"""
        QMessageBox.information(self, "偏好设置", "功能开发中...")

    def _on_docs(self) -> None:
        """打开开发文档"""
        QMessageBox.information(self, "开发文档", "请参考 docs/ 目录下的设计文档。")

    def _on_about(self) -> None:
        """关于对话框"""
        QMessageBox.about(
            self,
            "关于 QooRemote",
            f"<h3>QooRemote v0.1.0</h3>"
            f"<p>QooBot 远程机器人监控遥控控制台</p>"
            f"<p>适用平台：Windows / Linux / macOS</p>"
            f"<p>技术栈：Python 3.11+ / PySide6</p>"
            f"<p>许可证：Apache License 2.0</p>"
            f"<p>© 2026 QooBot Project</p>",
        )

    def closeEvent(self, event) -> None:
        """关闭窗口确认"""
        reply = QMessageBox.question(
            self,
            "退出确认",
            "确定要退出 QooRemote 吗？\n如有录制正在进行，将停止录制。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._signal_connected:
                self.disconnect_requested.emit()
            event.accept()
        else:
            event.ignore()
