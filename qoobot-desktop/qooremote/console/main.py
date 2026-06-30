"""QooRemote 桌面控制台 — 应用入口

启动 QApplication、主窗口，连接 ViewModel 与 UI。
v0.3.0 Control: +语音对讲 + 3D视口 + 录制回放 + 会话管理 + 动捕接口
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from console.app import create_application, setup_logging
from console.core.signaling.client import ConnectionState, SignalingClient, ConnectionConfig
from console.core.signaling.messages import MessageType
from console.core.models.session import SessionManager, SessionConfig
from console.core.models.multi_robot import RobotRegistry
from console.core.recording.exporter import ExportFormat
from console.ui.main_window import MainWindow
from console.ui.panels.dash_panel import DashPanel
from console.ui.panels.video_panel import VideoPanel
from console.ui.panels.control_panel import ControlPanel
from console.ui.panels.voice_panel import VoicePanel
from console.ui.panels.viewport_3d import Viewport3D
from console.ui.panels.recording_panel import RecordingPanel
from console.ui.viewmodels.robot_vm import RobotViewModel
from console.ui.viewmodels.video_vm import VideoViewModel
from console.ui.viewmodels.teleop_vm import TeleopViewModel
from console.ui.viewmodels.voice_vm import VoiceViewModel
from console.ui.viewmodels.recording_vm import RecordingViewModel
from console.ui.dialogs.connection_dialog import ConnectionDialog

logger = logging.getLogger(__name__)


def main() -> int:
    """QooRemote 应用入口"""
    setup_logging()
    logger.info("QooRemote v0.3.0 starting...")

    app = create_application()

    # --- 核心服务层 ---
    signaling = SignalingClient(ConnectionConfig())
    session_mgr = SessionManager()
    robot_registry = RobotRegistry()

    # --- ViewModel 层 ---
    robot_vm = RobotViewModel()
    video_vm = VideoViewModel(camera_count=4)
    teleop_vm = TeleopViewModel()
    voice_vm = VoiceViewModel()
    recording_vm = RecordingViewModel()

    # 连接信令回调
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
    voice_panel = VoicePanel()
    viewport_3d = Viewport3D()
    recording_panel = RecordingPanel()

    # 嵌入主窗口
    main_window.set_dashboard_widget(dash_panel)
    main_window.set_video_widget(video_panel)
    main_window.set_control_widget(control_panel)
    main_window.set_voice_widget(voice_panel)
    main_window.set_viewport3d_widget(viewport_3d)
    main_window.set_recording_widget(recording_panel)

    # --- 连接 UI 信号 ---

    # 连接/断开 (使用 ConnectionDialog)
    main_window.connect_requested.connect(
        lambda: _show_connect_dialog(signaling, main_window, session_mgr, robot_registry)
    )
    main_window.disconnect_requested.connect(
        lambda: _disconnect(signaling, main_window, session_mgr)
    )

    # 紧急制动 — TAK-02
    main_window.emergency_stop_requested.connect(teleop_vm.trigger_emergency_stop)
    main_window.emergency_stop_requested.connect(
        lambda reason: signaling.send_command(
            MessageType.EMERGENCY_STOP, payload={"reason": reason},
        )
    )
    dash_panel.emergency_button.clicked.connect(
        lambda: main_window.emergency_stop_requested.emit("dash_button")
    )

    # 操控面板
    control_panel.mode_switch_requested.connect(teleop_vm.switch_mode)
    control_panel.control_mode_changed.connect(teleop_vm.set_control_mode)

    # 语音面板 — VOX-01/02
    voice_panel.ptt_pressed.connect(voice_vm.ptt_press)
    voice_panel.ptt_released.connect(voice_vm.ptt_release)
    voice_panel.mode_changed.connect(
        lambda mode: voice_vm.set_mode(__import__("console.core.webrtc.audio_track",
                                                    fromlist=["VoiceMode"]).VoiceMode(mode))
    )
    voice_vm.tx_level_changed.connect(
        lambda rms: voice_panel.update_levels(rms, voice_panel._rx_level)
    )
    voice_vm.rx_level_changed.connect(
        lambda rms: voice_panel.update_levels(voice_panel._tx_level, rms)
    )

    # 录制面板 — TCH-01/02
    recording_panel.record_start_requested.connect(
        lambda: recording_vm.start_recording(
            robot_id=robot_registry.selected_id or "unknown",
            operator="operator",
        )
    )
    recording_panel.record_pause_requested.connect(recording_vm.pause_recording)
    recording_panel.record_stop_requested.connect(recording_vm.stop_recording)
    recording_panel.marker_add_requested.connect(recording_vm.add_marker)

    # 回放
    recording_panel.playback_play.connect(
        lambda: recording_vm.play()
    )
    recording_panel.playback_pause.connect(recording_vm.pause_playback)
    recording_panel.playback_stop.connect(recording_vm.stop_playback)
    recording_panel.playback_speed_changed.connect(recording_vm.set_speed)

    # 导出 — TCH-03
    recording_panel.export_requested.connect(
        lambda fmt: _on_export(recording_vm, fmt)
    )

    # 录制状态同步
    recording_vm.recording_started.connect(
        lambda sid: recording_panel.set_recording_state(
            __import__("console.core.recording.recorder", fromlist=["RecordingState"]).RecordingState.RECORDING
        )
    )
    recording_vm.recording_stopped.connect(
        lambda _: recording_panel.set_recording_state(
            __import__("console.core.recording.recorder", fromlist=["RecordingState"]).RecordingState.STOPPED
        )
    )
    recording_vm.recording_paused.connect(
        lambda: recording_panel.set_recording_state(
            __import__("console.core.recording.recorder", fromlist=["RecordingState"]).RecordingState.PAUSED
        )
    )

    # ViewModel → UI 数据流
    robot_vm.state_updated.connect(dash_panel.update_robot_state)
    robot_vm.state_updated.connect(
        lambda state: viewport_3d.update_joints(
            {j.name: j.angle for j in state.joints} if hasattr(state, 'joints') else {}
        )
    )
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

    # 录制进度同步到主窗口状态栏
    def _update_recording_status():
        nonlocal recording_vm
        if recording_vm.recording_state == __import__(
            "console.core.recording.recorder", fromlist=["RecordingState"]
        ).RecordingState.RECORDING:
            main_window.update_recording_state(True, int(recording_vm.recording_elapsed))
        else:
            main_window.update_recording_state(False, 0)
        main_window._label_recording.setVisible(
            recording_vm.recording_state != __import__(
                "console.core.recording.recorder", fromlist=["RecordingState"]
            ).RecordingState.IDLE
        )

    logger.info("QooRemote v0.3.0 initialized — %d panels ready", 6)
    exit_code = app.exec()
    logger.info("QooRemote exiting (code=%d)", exit_code)
    return exit_code


async def _connect(signaling: SignalingClient, main_window: MainWindow,
                   session_mgr: SessionManager, robot_id: str) -> None:
    """异步连接"""
    import asyncio
    loop = asyncio.get_event_loop()
    session_mgr.create_session(robot_id)
    success = await signaling.connect()
    if success:
        main_window.update_connection_state(ConnectionState.SESSION_ACTIVE)
    else:
        main_window.update_connection_state(ConnectionState.DISCONNECTED)


async def _disconnect(signaling: SignalingClient, main_window: MainWindow,
                       session_mgr: SessionManager) -> None:
    """异步断开"""
    await signaling.disconnect()
    session_mgr.close_current()
    main_window.update_connection_state(ConnectionState.DISCONNECTED)


def _show_connect_dialog(signaling, main_window, session_mgr, robot_registry):
    """显示连接对话框并处理结果"""
    dlg = ConnectionDialog(main_window)
    dlg.connect_requested.connect(
        lambda params: _connect(signaling, main_window, session_mgr, params["robot_id"])
    )
    dlg.exec()


def _on_export(recording_vm, fmt: str) -> None:
    """处理导出请求"""
    import logging
    log = logging.getLogger(__name__)
    result = recording_vm.export(fmt)
    if result:
        log.info("Exported %d chars to %s format", len(result), fmt)
    else:
        log.warning("Export failed or no data")

