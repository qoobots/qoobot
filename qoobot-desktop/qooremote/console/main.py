"""QooRemote 桌面控制台 — 应用入口

启动 QApplication、主窗口，连接 ViewModel 与 UI。
v1.0.0 GA: +权限管理(TAK-03) + 接管审计(TAK-04) — 40/40 全部完成
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
from console.core.models.alert_history import AlertHistoryService
from console.core.recording.exporter import ExportFormat
from console.core.recording.recorder import RecordingState
from console.core.twins import CollisionVisualizer, PointCloudManager, SLAMMap
from console.core.video import VideoRecorder, VideoTrackInfo, VideoCodec
from console.core.video.player import VideoPlayer
from console.core.teleop.vr import VrTeleopBridge
from console.plugins.vr import MetaQuestDriver
from console.ui.main_window import MainWindow
from console.ui.panels.dash_panel import DashPanel
from console.ui.panels.video_panel import VideoPanel
from console.ui.panels.control_panel import ControlPanel
from console.ui.panels.voice_panel import VoicePanel
from console.ui.panels.viewport_3d import Viewport3D
from console.ui.panels.recording_panel import RecordingPanel
from console.ui.panels.alert_history_panel import AlertHistoryPanel
from console.ui.panels.video_pip import PipOverlay, PipControlBar
from console.ui.viewmodels.robot_vm import RobotViewModel
from console.ui.viewmodels.video_vm import VideoViewModel
from console.ui.viewmodels.teleop_vm import TeleopViewModel
from console.ui.viewmodels.voice_vm import VoiceViewModel
from console.ui.viewmodels.recording_vm import RecordingViewModel
from console.ui.viewmodels.alert_history_vm import AlertHistoryViewModel
from console.ui.viewmodels.takeover_vm import TakeoverViewModel
from console.ui.panels.takeover_panel import TakeoverPanel
from console.ui.dialogs.connection_dialog import ConnectionDialog

logger = logging.getLogger(__name__)


def main() -> int:
    """QooRemote 应用入口"""
    setup_logging()
    logger.info("QooRemote v1.0.0 GA starting...")

    app = create_application()

    # ================================================================
    # 核心服务层
    # ================================================================
    signaling = SignalingClient(ConnectionConfig())
    session_mgr = SessionManager()
    robot_registry = RobotRegistry()

    # 数字孪生核心
    collision_viz = CollisionVisualizer(max_collision_pairs=100)
    pointcloud_mgr = PointCloudManager(max_frames=10)
    slam_map = SLAMMap()

    # VR 设备
    vr_driver = MetaQuestDriver()
    vr_bridge = VrTeleopBridge()

    # 视频录制回放
    video_recorder = VideoRecorder()
    video_player = VideoPlayer()

    # 告警历史
    alert_history_service = AlertHistoryService()

    # TAK-03/04: 接管权限管理 + 审计
    takeover_vm = TakeoverViewModel()

    # ================================================================
    # ViewModel 层
    # ================================================================
    robot_vm = RobotViewModel()
    video_vm = VideoViewModel(camera_count=4)
    teleop_vm = TeleopViewModel()
    voice_vm = VoiceViewModel()
    recording_vm = RecordingViewModel()
    alert_history_vm = AlertHistoryViewModel()

    # 绑定告警管理
    alert_history_vm.bind_alert_manager(robot_vm.alert_manager)

    # 信令回调
    signaling.on_state_changed(robot_vm.on_connection_state)
    signaling.on_robot_state(robot_vm.on_robot_state)
    signaling.on_alert(robot_vm.alert_manager.add_alert)

    # ================================================================
    # UI 层
    # ================================================================
    main_window = MainWindow()
    main_window.show()

    # 面板
    dash_panel = DashPanel(alert_manager=robot_vm.alert_manager)
    video_panel = VideoPanel(camera_count=4)
    control_panel = ControlPanel()
    voice_panel = VoicePanel()
    viewport_3d = Viewport3D()
    recording_panel = RecordingPanel()
    alert_history_panel = AlertHistoryPanel()
    takeover_panel = TakeoverPanel()

    # 画中画组件
    pip_overlay = PipOverlay(video_panel)
    pip_control = PipControlBar(camera_count=4)

    # 嵌入主窗口
    main_window.set_dashboard_widget(dash_panel)
    main_window.set_video_widget(video_panel)
    main_window.set_control_widget(control_panel)
    main_window.set_voice_widget(voice_panel)
    main_window.set_viewport3d_widget(viewport_3d)
    main_window.set_recording_widget(recording_panel)
    main_window.set_alert_history_widget(alert_history_panel)
    main_window.set_takeover_widget(takeover_panel)

    # ================================================================
    # 连接 UI 信号
    # ================================================================

    # 连接/断开
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

    # 语音面板 — VOX-01~04
    voice_panel.ptt_pressed.connect(voice_vm.ptt_press)
    voice_panel.ptt_released.connect(voice_vm.ptt_release)
    voice_panel.mode_changed.connect(
        lambda mode: voice_vm.set_mode(__import__(
            "console.core.webrtc.audio_track", fromlist=["VoiceMode"]
        ).VoiceMode(mode))
    )
    voice_vm.tx_level_changed.connect(
        lambda rms: voice_panel.update_levels(rms, voice_panel._rx_level)
    )
    voice_vm.rx_level_changed.connect(
        lambda rms: voice_panel.update_levels(voice_panel._tx_level, rms)
    )

    # 录制面板 — TCH-01~04
    recording_panel.record_start_requested.connect(
        lambda: recording_vm.start_recording(
            robot_id=robot_registry.selected_id or "unknown",
            operator="operator",
        )
    )
    recording_panel.record_pause_requested.connect(recording_vm.pause_recording)
    recording_panel.record_stop_requested.connect(recording_vm.stop_recording)
    recording_panel.marker_add_requested.connect(recording_vm.add_marker)
    recording_panel.playback_play.connect(lambda: recording_vm.play())
    recording_panel.playback_pause.connect(recording_vm.pause_playback)
    recording_panel.playback_stop.connect(recording_vm.stop_playback)
    recording_panel.playback_speed_changed.connect(recording_vm.set_speed)
    recording_panel.export_requested.connect(lambda fmt: _on_export(recording_vm, fmt))

    # 录制状态同步
    recording_vm.recording_started.connect(
        lambda sid: recording_panel.set_recording_state(RecordingState.RECORDING)
    )
    recording_vm.recording_stopped.connect(
        lambda _: recording_panel.set_recording_state(RecordingState.STOPPED)
    )
    recording_vm.recording_paused.connect(
        lambda: recording_panel.set_recording_state(RecordingState.PAUSED)
    )

    # 画中画 — VID-04
    pip_control.pip_toggled.connect(pip_overlay.setVisible)
    pip_control.source_changed.connect(
        lambda idx: pip_overlay.set_title(f"摄像头 {idx + 1}")
    )
    pip_control.opacity_changed.connect(pip_overlay.set_opacity)
    pip_control.size_changed.connect(pip_overlay.set_size_ratio)
    pip_overlay.closed.connect(lambda: pip_control.set_pip_enabled(False))

    # 告警历史面板 — ALT-03
    alert_history_panel.query_requested.connect(alert_history_vm.query)
    alert_history_panel.export_requested.connect(
        lambda fp, fmt: alert_history_vm.export(fp, fmt)
    )
    alert_history_panel.refresh_requested.connect(alert_history_vm.refresh)
    alert_history_vm.query_completed.connect(alert_history_panel.populate_table)
    alert_history_vm.statistics_updated.connect(
        lambda s: alert_history_panel.update_statistics(s.to_dict())
    )

    # 接管面板 — TAK-03 权限管理 + TAK-04 接管审计
    takeover_panel.login_requested.connect(takeover_vm.login)
    takeover_panel.logout_requested.connect(takeover_vm.logout)
    takeover_panel.operator_add_requested.connect(takeover_vm.add_operator)
    takeover_panel.operator_remove_requested.connect(takeover_vm.remove_operator)
    takeover_panel.takeover_requested.connect(takeover_vm.request_takeover)
    takeover_panel.takeover_approve_requested.connect(takeover_vm.approve_takeover)
    takeover_panel.takeover_reject_requested.connect(takeover_vm.reject_takeover)
    takeover_panel.control_release_requested.connect(takeover_vm.release_control)

    # 审计查询/导出
    takeover_panel.audit_query_requested.connect(takeover_vm.query_audit)
    takeover_panel.audit_export_requested.connect(takeover_vm.export_audit)
    takeover_panel.audit_refresh_requested.connect(takeover_vm.refresh_audit)

    # ViewModel → Panel 数据流
    takeover_vm.operators_updated.connect(takeover_panel.update_operators)
    takeover_vm.requests_updated.connect(takeover_panel.update_requests)
    takeover_vm.audit_query_completed.connect(takeover_panel.populate_audit_table)
    takeover_vm.audit_statistics_updated.connect(
        lambda s: takeover_panel.update_audit_statistics(s.to_dict())
    )
    takeover_vm.status_message.connect(
        lambda msg: takeover_panel.update_login_status(
            takeover_vm.current_operator is not None,
            takeover_vm.current_operator.name if takeover_vm.current_operator else ""
        )
    )

    # 紧急制动审计记录
    main_window.emergency_stop_requested.connect(takeover_vm.record_emergency)

    # 模式切换审计记录
    control_panel.mode_switch_requested.connect(
        lambda to_mode: takeover_vm.record_mode_switch("current", to_mode)
    )

    # ViewModel → UI 数据流
    robot_vm.state_updated.connect(dash_panel.update_robot_state)
    robot_vm.state_updated.connect(
        lambda state: _update_viewport(viewport_3d, state)
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

    # 告警同步到历史存储
    robot_vm.alerts_changed.connect(
        lambda: _sync_alerts_to_history(alert_history_service, robot_vm)
    )

    video_vm.bitrate_updated.connect(main_window.update_video_bitrate)
    video_vm.bitrate_updated.connect(video_panel.update_bitrate)

    # 录制状态同步
    def _update_recording_status():
        if recording_vm.recording_state == RecordingState.RECORDING:
            main_window.update_recording_state(True, int(recording_vm.recording_elapsed))
        else:
            main_window.update_recording_state(False, 0)
        main_window._label_recording.setVisible(
            recording_vm.recording_state != RecordingState.IDLE
        )

    # VR 设备状态轮询 (TEL-05)
    _vr_timer = None
    def _start_vr_polling():
        nonlocal _vr_timer
        if vr_driver.connected:
            from PySide6.QtCore import QTimer
            _vr_timer = QTimer()
            _vr_timer.timeout.connect(lambda: _poll_vr(vr_driver, vr_bridge, teleop_vm, viewport_3d))
            _vr_timer.start(11)  # ~90Hz

    vr_driver.connect()
    _start_vr_polling()

    logger.info("QooRemote v1.0.0 GA initialized — %d panels ready", 8)

    # 启动时做一次告警历史同步
    alert_history_vm.sync_current()

    exit_code = app.exec()

    # 清理
    alert_history_vm.cleanup()
    takeover_vm.cleanup()
    if _vr_timer:
        _vr_timer.stop()
    vr_driver.disconnect()

    logger.info("QooRemote exiting (code=%d)", exit_code)
    return exit_code


# ================================================================
# 辅助函数
# ================================================================

async def _connect(signaling: SignalingClient, main_window: MainWindow,
                   session_mgr: SessionManager, robot_id: str) -> None:
    """异步连接"""
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
    """显示连接对话框"""
    dlg = ConnectionDialog(main_window)
    dlg.connect_requested.connect(
        lambda params: _connect(signaling, main_window, session_mgr, params["robot_id"])
    )
    dlg.exec()


def _on_export(recording_vm, fmt: str) -> None:
    """处理导出请求"""
    result = recording_vm.export(fmt)
    if result:
        logger.info("Exported %d chars to %s format", len(result), fmt)
    else:
        logger.warning("Export failed or no data")


def _update_viewport(viewport: Viewport3D, state) -> None:
    """更新 3D 视口关节数据"""
    joint_angles = {}
    if hasattr(state, 'joints'):
        for j in state.joints:
            joint_angles[j.name] = j.angle
    viewport.update_joints(joint_angles)


def _poll_vr(vr_driver: MetaQuestDriver, bridge: VrTeleopBridge,
             teleop_vm: TeleopViewModel, viewport: Viewport3D) -> None:
    """VR 设备轮询"""
    frame = vr_driver.poll()
    if frame is None:
        return

    # 末端执行器跟随（右手控制末端）
    ee_target = bridge.compute_end_effector_target(frame, bridge._right_ctrl_target)
    if ee_target:
        teleop_vm.set_end_effector_pose(
            ee_target.get("position", (0, 0, 0)),
            ee_target.get("rotation", (1, 0, 0, 0)),
            ee_target.get("gripper", 0.0),
        )

    # 左手关节控制（可选）
    joint_targets = bridge.compute_joint_targets(frame, bridge._left_ctrl_target)
    if joint_targets and bridge.mode in (VrTeleopBridge.ControlMode.JOINT_MIRROR,
                                          VrTeleopBridge.ControlMode.BOTH):
        viewport.update_joints(joint_targets)


def _sync_alerts_to_history(service: AlertHistoryService,
                            robot_vm: RobotViewModel) -> None:
    """告警同步到历史存储"""
    try:
        service.sync_alerts(robot_vm.alert_manager)
    except Exception as e:
        logger.debug("Alert history sync skipped: %s", e)


if __name__ == "__main__":
    sys.exit(main())
