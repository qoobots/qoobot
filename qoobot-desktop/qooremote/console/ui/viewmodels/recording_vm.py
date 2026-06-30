"""录制 ViewModel — 连接 RecordingPanel 与录制核心

管理录制/回放状态、标记操作、数据导出。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal, QTimer

from console.core.recording.recorder import Recorder, RecordingState, RecordingMode, RecordingMetadata
from console.core.recording.player import Player, PlaybackState, PlaybackProgress
from console.core.recording.exporter import Exporter, ExportFormat, export_recording


class RecordingViewModel(QObject):
    """录制与回放 ViewModel

    桥接 UI (RecordingPanel) 与核心 (Recorder/Player/Exporter)。
    """

    # 录制信号
    recording_started = Signal(str)            # session_id
    recording_stopped = Signal(object)         # metadata
    recording_paused = Signal()
    recording_resumed = Signal()
    marker_added = Signal(str, int)            # text, frame_index

    # 回放信号
    playback_started = Signal()
    playback_stopped = Signal()
    playback_paused = Signal()
    playback_resumed = Signal()
    playback_frame = Signal(object)            # RecordingFrame
    playback_completed = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._recorder = Recorder()
        self._player = Player()
        self._exporter = Exporter()
        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(100)
        self._stats_timer.timeout.connect(self._tick)

        # 连接核心回调
        self._recorder.on_state_change = self._on_recorder_state
        self._player.on_state_change = self._on_player_state
        self._player.on_frame = self._on_player_frame
        self._player.on_completed = lambda: self.playback_completed.emit()

    # ---- 属性 ----

    @property
    def recorder(self) -> Recorder:
        return self._recorder

    @property
    def player(self) -> Player:
        return self._player

    @property
    def recording_state(self) -> RecordingState:
        return self._recorder.state

    @property
    def playback_state(self) -> PlaybackState:
        return self._player.state

    @property
    def recording_elapsed(self) -> float:
        return self._recorder.elapsed

    @property
    def recording_metadata(self) -> Optional[RecordingMetadata]:
        return self._recorder.metadata

    @property
    def playback_progress(self) -> PlaybackProgress:
        return self._player.progress

    # ---- 录制操作 ----

    def start_recording(self, robot_id: str, operator: str = "unknown",
                        mode: RecordingMode = RecordingMode.FULL,
                        joint_names: Optional[list[str]] = None,
                        notes: str = "") -> None:
        """开始录制"""
        metadata = self._recorder.start(
            robot_id=robot_id, operator=operator, mode=mode,
            joint_names=joint_names, notes=notes,
        )
        self._stats_timer.start()
        self.recording_started.emit(metadata.session_id)

    def pause_recording(self) -> None:
        self._recorder.pause()

    def resume_recording(self) -> None:
        self._recorder.resume()

    def stop_recording(self) -> None:
        self._stats_timer.stop()
        metadata = self._recorder.stop()
        if metadata:
            self.recording_stopped.emit(metadata)

    def add_marker(self, text: str) -> None:
        """添加时间标记"""
        self._recorder.add_marker(text)
        self.marker_added.emit(text, self._recorder.frame_count)

    def record_frame(self, joint_angles: Optional[dict[str, float]] = None,
                     end_effector_pose: Optional[list[float]] = None) -> None:
        """记录一帧（由外部定时调用）"""
        self._recorder.record_frame(joint_angles=joint_angles,
                                    end_effector_pose=end_effector_pose)

    # ---- 回放操作 ----

    def load_playback(self, frames: Optional[list] = None,
                      metadata: Optional[RecordingMetadata] = None) -> None:
        """加载回放数据"""
        if frames is None:
            frames = self._recorder.get_frames()
        if metadata is None:
            metadata = self._recorder.metadata
        self._player.load(list(frames), metadata)

    def play(self, speed: float = 1.0, repeat: bool = False) -> None:
        if self._player.total_frames == 0:
            self.load_playback()
        self._player.play(speed, repeat)
        self._stats_timer.start()

    def pause_playback(self) -> None:
        self._player.pause()

    def resume_playback(self) -> None:
        self._player.resume()

    def stop_playback(self) -> None:
        self._stats_timer.stop()
        self._player.stop()

    def seek(self, frame_index: int) -> None:
        self._player.seek(frame_index)

    def set_speed(self, speed: float) -> None:
        self._player._speed = max(0.1, min(10.0, speed))

    # ---- 导出 ----

    def export(self, fmt: str) -> Optional[str]:
        """导出录制数据

        Args:
            fmt: 格式名称 (jsonl/h5/csv/qoorlog/rosbag)

        Returns:
            导出数据字符串
        """
        try:
            ef = ExportFormat(fmt)
            result = export_recording(self._recorder, ef)
            return result.data if isinstance(result.data, str) else result.data.decode("utf-8")
        except Exception as e:
            return None

    # ---- 内部 ----

    def _tick(self) -> None:
        """定时器 — 推进回放"""
        if self._player.state == PlaybackState.PLAYING:
            self._player.tick()

    def _on_recorder_state(self, state: RecordingState) -> None:
        if state == RecordingState.PAUSED:
            self.recording_paused.emit()
        elif state == RecordingState.RECORDING:
            self.recording_resumed.emit()

    def _on_player_state(self, state: PlaybackState) -> None:
        if state == PlaybackState.PLAYING:
            self.playback_started.emit()
        elif state == PlaybackState.STOPPED:
            self.playback_stopped.emit()
        elif state == PlaybackState.PAUSED:
            self.playback_paused.emit()

    def _on_player_frame(self, frame, index: int) -> None:
        self.playback_frame.emit(frame)
