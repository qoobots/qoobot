"""录制面板 — 录制控制、回放管理、标记操作

对应功能 TCH-01/02（操作录制 + 操作回放）。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QWidget, QSlider, QSpinBox, QGroupBox, QCheckBox,
)

from console.core.recording.recorder import RecordingState, RecordingMode, RecordingMetadata
from console.core.recording.player import PlaybackState, PlaybackProgress


class RecordingPanel(QFrame):
    """录制控制面板

    功能：
    - 开始/暂停/停止录制（TCH-01）
    - 添加标记（TCH-04）
    - 回放控制（TCH-02）
    - 录制统计
    """

    # 录制信号
    record_start_requested = Signal()                 # 请求开始录制
    record_pause_requested = Signal()                 # 请求暂停
    record_stop_requested = Signal()                  # 请求停止
    marker_add_requested = Signal(str)               # 添加标记
    export_requested = Signal(str)                   # 请求导出 (format)

    # 回放信号
    playback_play = Signal()                          # 播放
    playback_pause = Signal()                        # 暂停
    playback_stop = Signal()                         # 停止
    playback_seek = Signal(int)                      # 跳转到帧
    playback_speed_changed = Signal(float)           # 速度变更
    playback_repeat_toggled = Signal(bool)           # 循环切换

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._recording_state = RecordingState.IDLE
        self._playback_state = PlaybackState.IDLE
        self._recording_metadata: RecordingMetadata | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("⏺️ 录制与回放")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # ---- 录制控制 ----
        record_group = QGroupBox("录制 (TCH-01)")
        rec_layout = QVBoxLayout(record_group)

        # 录制按钮行
        rec_btn_row = QHBoxLayout()

        self._start_btn = QPushButton("⏺️ 开始录制")
        self._start_btn.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white;
                font-weight: bold; padding: 6px 12px; border-radius: 4px; }
            QPushButton:disabled { background-color: #666; }
        """)
        self._start_btn.clicked.connect(self._on_start)
        rec_btn_row.addWidget(self._start_btn)

        self._pause_btn = QPushButton("⏸️ 暂停")
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._on_pause)
        rec_btn_row.addWidget(self._pause_btn)

        self._stop_btn = QPushButton("⏹️ 停止")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        rec_btn_row.addWidget(self._stop_btn)

        rec_layout.addLayout(rec_btn_row)

        # 标记输入
        marker_row = QHBoxLayout()
        self._marker_input = QLineEdit()
        self._marker_input.setPlaceholderText("输入标记文本...")
        marker_row.addWidget(self._marker_input)

        self._marker_btn = QPushButton("📌 标记")
        self._marker_btn.setEnabled(False)
        self._marker_btn.clicked.connect(self._on_add_marker)
        marker_row.addWidget(self._marker_btn)
        rec_layout.addLayout(marker_row)

        # 录制统计
        self._recording_stats = QLabel("就绪")
        self._recording_stats.setStyleSheet("color: #888; font-size: 11px;")
        rec_layout.addWidget(self._recording_stats)

        layout.addWidget(record_group)

        # ---- 回放控制 ----
        play_group = QGroupBox("回放 (TCH-02)")
        play_layout = QVBoxLayout(play_group)

        # 回放按钮行
        play_btn_row = QHBoxLayout()

        self._play_btn = QPushButton("▶️ 播放")
        self._play_btn.setEnabled(False)
        self._play_btn.clicked.connect(self._on_play)
        play_btn_row.addWidget(self._play_btn)

        self._play_pause_btn = QPushButton("⏸️ 暂停")
        self._play_pause_btn.setEnabled(False)
        play_btn_row.addWidget(self._play_pause_btn)

        self._play_stop_btn = QPushButton("⏹️ 停止")
        self._play_stop_btn.setEnabled(False)
        play_btn_row.addWidget(self._play_stop_btn)

        self._step_btn = QPushButton("⏭️ 步进")
        self._step_btn.setEnabled(False)
        play_btn_row.addWidget(self._step_btn)

        play_layout.addLayout(play_btn_row)

        # 速度/循环控制
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("速度:"))

        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(10, 200)
        self._speed_slider.setValue(100)
        self._speed_slider.setTickInterval(10)
        self._speed_slider.valueChanged.connect(
            lambda v: self._on_speed_changed(v / 100.0)
        )
        speed_row.addWidget(self._speed_slider)

        self._speed_label = QLabel("1.0x")
        self._speed_label.setFixedWidth(40)
        speed_row.addWidget(self._speed_label)

        self._repeat_check = QCheckBox("🔁 循环")
        speed_row.addWidget(self._repeat_check)

        play_layout.addLayout(speed_row)

        # 进度信息
        self._playback_progress = QLabel("未加载数据")
        self._playback_progress.setStyleSheet("color: #888; font-size: 11px;")
        play_layout.addWidget(self._playback_progress)

        layout.addWidget(play_group)

        # ---- 导出 ----
        export_group = QGroupBox("导出 (TCH-03)")
        export_layout = QHBoxLayout(export_group)

        for fmt, label in [("jsonl", "JSONL"), ("h5", "HDF5"), ("csv", "CSV"),
                           ("qoorlog", "Qoorlog"), ("rosbag", "ROS Bag")]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, f=fmt: self.export_requested.emit(f))
            export_layout.addWidget(btn)

        layout.addWidget(export_group)
        layout.addStretch()

    # ---- 公开方法 ----

    def set_recording_state(self, state: RecordingState) -> None:
        """更新录制状态 UI"""
        self._recording_state = state
        is_idle = state == RecordingState.IDLE
        is_recording = state == RecordingState.RECORDING
        is_paused = state == RecordingState.PAUSED

        self._start_btn.setEnabled(is_idle)
        self._pause_btn.setEnabled(is_recording)
        self._stop_btn.setEnabled(not is_idle)
        self._marker_btn.setEnabled(is_recording)

        if is_recording:
            self._start_btn.setText("⏺️ 录制中...")
        else:
            self._start_btn.setText("⏺️ 开始录制")

    def set_playback_state(self, state: PlaybackState) -> None:
        """更新回放状态 UI"""
        self._playback_state = state
        is_idle = state == PlaybackState.IDLE
        is_playing = state == PlaybackState.PLAYING
        is_paused = state == PlaybackState.PAUSED

        self._play_btn.setEnabled(is_idle or is_paused)
        self._play_pause_btn.setEnabled(is_playing)
        self._play_stop_btn.setEnabled(not is_idle)
        self._step_btn.setEnabled(is_paused)

    def update_recording_stats(self, metadata: RecordingMetadata, elapsed: float) -> None:
        """更新录制统计信息"""
        self._recording_metadata = metadata
        hours = int(elapsed // 3600)
        mins = int((elapsed % 3600) // 60)
        secs = int(elapsed % 60)
        self._recording_stats.setText(
            f"⏱ {hours:02d}:{mins:02d}:{secs:02d} | "
            f"帧: {metadata.total_frames} | "
            f"模式: {metadata.mode.value}"
        )

    def update_playback_progress(self, progress: PlaybackProgress) -> None:
        """更新回放进度"""
        pct = (progress.current_frame / progress.total_frames * 100) if progress.total_frames > 0 else 0
        self._playback_progress.setText(
            f"帧: {progress.current_frame}/{progress.total_frames} ({pct:.1f}%) | "
            f"{progress.elapsed_s:.1f}s / {progress.total_duration_s:.1f}s"
        )

    def set_data_loaded(self, frame_count: int, duration_s: float) -> None:
        """通知数据已加载"""
        self._play_btn.setEnabled(frame_count > 0)
        self._playback_progress.setText(
            f"已加载 {frame_count} 帧, {duration_s:.1f}s"
        )

    # ---- 槽 ----

    def _on_start(self) -> None:
        self.record_start_requested.emit()

    def _on_pause(self) -> None:
        if self._recording_state == RecordingState.RECORDING:
            self.record_pause_requested.emit()
        elif self._playback_state == PlaybackState.PLAYING:
            self.playback_pause.emit()

    def _on_stop(self) -> None:
        if self._recording_state != RecordingState.IDLE:
            self.record_stop_requested.emit()
        elif self._playback_state != PlaybackState.IDLE:
            self.playback_stop.emit()

    def _on_play(self) -> None:
        self.playback_play.emit()

    def _on_speed_changed(self, speed: float) -> None:
        self._speed_label.setText(f"{speed:.1f}x")
        self.playback_speed_changed.emit(speed)

    def _on_add_marker(self) -> None:
        text = self._marker_input.text().strip()
        if text:
            self.marker_add_requested.emit(text)
            self._marker_input.clear()
