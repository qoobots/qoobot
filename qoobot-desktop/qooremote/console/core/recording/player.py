"""录制回放器 — 精确回放录制数据，驱动 UI 和数据管道

对应功能 TCH-02（操作回放）。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

import numpy as np

from console.core.recording.recorder import RecordingFrame, RecordingMetadata

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 回放状态
# ------------------------------------------------------------------

class PlaybackState(Enum):
    """回放状态"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class PlaybackProgress:
    """回放进度"""
    current_frame: int = 0
    total_frames: int = 0
    elapsed_s: float = 0.0
    total_duration_s: float = 0.0
    speed: float = 1.0
    repeat: bool = False


# ------------------------------------------------------------------
# 回放器
# ------------------------------------------------------------------

class Player:
    """录制数据精确回放器

    按时间戳顺序回放 RecordingFrame 数据。
    支持变速、跳转、循环和帧步进。

    对应功能 TCH-02（操作回放）。
    """

    def __init__(self) -> None:
        self._metadata: Optional[RecordingMetadata] = None
        self._frames: list[RecordingFrame] = []
        self._state = PlaybackState.IDLE
        self._current_idx = 0
        self._speed = 1.0
        self._repeat = False
        self._start_wall_time = 0.0
        self._start_recording_time = 0.0
        self._pause_offset = 0.0

        # 回调
        self.on_state_change: Optional[Callable[[PlaybackState], None]] = None
        self.on_frame: Optional[Callable[[RecordingFrame, int], None]] = None
        self.on_progress: Optional[Callable[[PlaybackProgress], None]] = None
        self.on_completed: Optional[Callable[[], None]] = None

    # ---- 属性 ----

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def metadata(self) -> Optional[RecordingMetadata]:
        return self._metadata

    @property
    def current_frame_index(self) -> int:
        return self._current_idx

    @property
    def total_frames(self) -> int:
        return len(self._frames)

    @property
    def progress(self) -> PlaybackProgress:
        total_duration = 0.0
        if self._frames and self._metadata:
            total_duration = self._metadata.total_duration_s
        elapsed = 0.0
        if self._current_idx > 0 and self._frames:
            elapsed = self._frames[self._current_idx - 1].timestamp - (
                self._frames[0].timestamp if self._frames else 0
            )
        return PlaybackProgress(
            current_frame=self._current_idx,
            total_frames=len(self._frames),
            elapsed_s=elapsed,
            total_duration_s=total_duration,
            speed=self._speed,
            repeat=self._repeat,
        )

    # ---- 加载 ----

    def load(self, frames: list[RecordingFrame],
             metadata: Optional[RecordingMetadata] = None) -> None:
        """加载录制数据

        Args:
            frames: 录制帧列表
            metadata: 录制元信息
        """
        self.stop()
        self._frames = list(frames)
        self._metadata = metadata
        self._current_idx = 0
        logger.info("Loaded %d frames for playback", len(self._frames))

    # ---- 播放控制 ----

    def play(self, speed: float = 1.0, repeat: bool = False) -> None:
        """开始回放

        Args:
            speed: 回放速度倍率（1.0=原速, 2.0=二倍速, 0.5=半速）
            repeat: 是否循环
        """
        if not self._frames:
            logger.warning("No frames loaded for playback")
            return

        self._speed = max(0.1, min(10.0, speed))
        self._repeat = repeat
        if self._state == PlaybackState.PAUSED and self._current_idx > 0:
            # 恢复
            pass
        else:
            self._current_idx = 0

        self._start_wall_time = time.time()
        self._start_recording_time = (
            self._frames[self._current_idx].timestamp if self._current_idx < len(self._frames)
            else 0.0
        )
        self._transition_to(PlaybackState.PLAYING)
        logger.info("Playback started: speed=%.1fx", self._speed)

    def pause(self) -> None:
        """暂停回放"""
        if self._state == PlaybackState.PLAYING:
            self._transition_to(PlaybackState.PAUSED)
            self._pause_offset = (time.time() - self._start_wall_time) * self._speed

    def resume(self) -> None:
        """恢复回放"""
        if self._state == PlaybackState.PAUSED:
            self._start_wall_time = time.time() - self._pause_offset / self._speed
            self._transition_to(PlaybackState.PLAYING)

    def stop(self) -> None:
        """停止回放"""
        self._transition_to(PlaybackState.STOPPED)
        self._current_idx = 0
        logger.info("Playback stopped")

    def seek(self, frame_index: int) -> None:
        """跳转到指定帧"""
        self._current_idx = max(0, min(frame_index, len(self._frames) - 1))
        if self._state == PlaybackState.PLAYING:
            self._start_wall_time = time.time()
            if self._current_idx < len(self._frames):
                self._start_recording_time = self._frames[self._current_idx].timestamp

    def seek_time(self, offset_s: float) -> None:
        """跳转到指定时间偏移（秒）"""
        if not self._frames:
            return
        start_ts = self._frames[0].timestamp
        target_ts = start_ts + offset_s
        # 二分查找最近的帧
        idx = 0
        for i, f in enumerate(self._frames):
            if f.timestamp >= target_ts:
                idx = i
                break
        else:
            idx = len(self._frames) - 1
        self.seek(idx)

    def step_forward(self, steps: int = 1) -> None:
        """步进 N 帧"""
        if self._state == PlaybackState.PAUSED:
            self._current_idx = min(self._current_idx + steps, len(self._frames) - 1)
            self._emit_frame()

    # ---- 帧推进 ----

    def tick(self) -> Optional[RecordingFrame]:
        """每帧调用以推进回放

        Returns:
            当前帧，或 None
        """
        if self._state != PlaybackState.PLAYING or not self._frames:
            return None

        elapsed_wall = (time.time() - self._start_wall_time) * self._speed
        target_time = self._start_recording_time + elapsed_wall

        found_idx = self._current_idx
        for i in range(self._current_idx, len(self._frames)):
            if self._frames[i].timestamp >= target_time:
                found_idx = i
                break
        else:
            found_idx = len(self._frames)

        frames_to_emit = found_idx - self._current_idx
        if frames_to_emit <= 0:
            return None

        last_frame = None
        for offset in range(frames_to_emit):
            idx = self._current_idx + offset
            if idx >= len(self._frames):
                break
            frame = self._frames[idx]
            if self.on_frame:
                self.on_frame(frame, idx)
            last_frame = frame

        self._current_idx += frames_to_emit

        # 进度回调
        if self.on_progress:
            self.on_progress(self.progress)

        # 检测结束
        if self._current_idx >= len(self._frames):
            if self._repeat:
                self._current_idx = 0
                self._start_wall_time = time.time()
                self._start_recording_time = self._frames[0].timestamp if self._frames else 0
            else:
                self._transition_to(PlaybackState.STOPPED)
                if self.on_completed:
                    self.on_completed()

        return last_frame

    # ---- 内部 ----

    def _transition_to(self, state: PlaybackState) -> None:
        old = self._state
        self._state = state
        if old != state and self.on_state_change:
            self.on_state_change(state)

    def _emit_frame(self) -> None:
        """发送当前帧（用于 Pause 状态下的步进）"""
        if 0 <= self._current_idx < len(self._frames):
            if self.on_frame:
                self.on_frame(self._frames[self._current_idx], self._current_idx)
