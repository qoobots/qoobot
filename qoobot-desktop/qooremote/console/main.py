"""QooRemote 桌面控制台 — 应用入口

启动 QApplication、主窗口，连接 ViewModel 与 UI。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from console.app import create_application, setup_logging
from console.core.signaling.client import ConnectionState, SignalingClient, ConnectionConfig
from console.core.signaling.messages import MessageType
from console.ui.main_window import MainWindow
from console.ui.panels.dash_panel import DashPanel
from console.ui.panels.video_panel import VideoPanel
from console.ui.panels.control_panel import ControlPanel
from console.ui.viewmodels.robot_vm import RobotViewModel
from console.ui.viewmodels.video_vm import VideoViewModel
from console.ui.viewmodels.teleop_vm import TeleopViewModel

logger = logging.getLogger(__name__)


def main() -> int:
    """QooRemote 应用入口

    Returns:
        0 表示正常退出，非 0 表示异常退出。
    """
    setup_logging()
    logger.info("QooRemote v0.1.0 starting...")

    # 创建 Qt 应用
    app = create_application()

    # --- 核心服务层 ---
    # 信令客户端（准备就绪，实际连接由 UI 触发）
    signaling = SignalingClient(ConnectionConfig())

    # --- ViewModel 层 ---
    robot_vm = RobotViewModel()
    video_vm = VideoViewModel(camera_count=4)
    teleop_vm = TeleopViewModel()

    # 连接信令客户端回调到 ViewModel
    signaling.on_state_changed(robot_vm.on_connection_state)
    signaling.on_robot_state(robot_vm.on_robot_state)
    signaling.on_alert(robot_vm.alert_manager.add_alert)

    # --- UI 层 ---
    main_window = MainWindow()
    main_window.show()

    # 创建面板
    dash_panel = DashPanel(alert_manager=robot_vm.alert_manager)
    video_panel = VideoPanel(camera_count=4)
    control_panel = ControlPanel()

    # 将面板嵌入主窗口
    main_window.set_dashboard_widget(dash_panel)
    main_window.set_video_widget(video_panel)

    # --- 连接 UI 信号到 ViewModel ---

    # 连接/断开
    main_window.connect_requested.connect(
        lambda: _connect(signaling, main_window)
    )
    main_window.disconnect_requested.connect(
        lambda: _disconnect(signaling, main_window)
    )

    # 紧急制动 — TAK-02
    main_window.emergency_stop_requested.connect(teleop_vm.trigger_emergency_stop)
    main_window.emergency_stop_requested.connect(
        lambda reason: signaling.send_command(
            MessageType.EMERGENCY_STOP,
            payload={"reason": reason},
        )
    )

    # 仪表盘紧急按钮
    dash_panel.emergency_button.clicked.connect(
        lambda: main_window.emergency_stop_requested.emit("dash_button")
    )

    # 操控面板信号
    control_panel.mode_switch_requested.connect(teleop_vm.switch_mode)
    control_panel.control_mode_changed.connect(teleop_vm.set_control_mode)

    # ViewModel → UI 数据流
    robot_vm.state_updated.connect(dash_panel.update_robot_state)
    robot_vm.connection_changed.connect(main_window.update_connection_state)
    robot_vm.connection_changed.connect(dash_panel.connection_indicator.set_state)
    robot_vm.alerts_changed.connect(dash_panel.update_alerts)
    robot_vm.alerts_changed.connect(
        lambda: main_window.update_alert_count(
            len(robot_vm.alert_manager.active_alerts),
            robot_vm.alert_manager.critical_count,
        )
    )

    video_vm.bitrate_updated.connect(main_window.update_video_bitrate)
    video_vm.bitrate_updated.connect(video_panel.update_bitrate)

    # 连接信令延迟到主窗口
    # (实际实现中使用 QTimer 定期轮询 signaling.latency_ms)

    logger.info("QooRemote initialized successfully")

    # 运行事件循环
    exit_code = app.exec()
    logger.info("QooRemote exiting (code=%d)", exit_code)
    return exit_code


async def _connect(signaling: SignalingClient, main_window: MainWindow) -> None:
    """异步连接"""
    import asyncio
    loop = asyncio.get_event_loop()
    success = await signaling.connect()
    if success:
        main_window.update_connection_state(ConnectionState.SESSION_ACTIVE)
    else:
        main_window.update_connection_state(ConnectionState.DISCONNECTED)


async def _disconnect(signaling: SignalingClient, main_window: MainWindow) -> None:
    """异步断开"""
    await signaling.disconnect()
    main_window.update_connection_state(ConnectionState.DISCONNECTED)


if __name__ == "__main__":
    sys.exit(main())
