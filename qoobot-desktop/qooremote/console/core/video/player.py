"""视频回放器 — 录制视频的本地回放

支持多路视频同步回放、快进/快退/跳转、帧步进。

对应功能 VID-03（视频录制与回放）。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from console.core.video import VideoFrame, VideoTrackInfo, VideoRecorder  # noqa

logger = logging.getLogger(__name__)


class PlaybackState(str, Enum):
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class FrameIndex:
    """帧索引条目"""
    sequence: int = 0
    pts: int = 0
    timestamp: float = 0.0
    keyframe: bool = False
    size_bytes: int = 0


@dataclass
class TrackIndex:
    """视频轨索引"""
    track_id: str = ""
    frames: list[FrameIndex] = field(default_factory=list)
    total_duration: float = 0.0


class VideoPlayer:
    """视频回放器

    从 .vididx 索引文件加载帧元数据，支持：
    - 播放/暂停/停止
    - 快进/快退 (1x~8x)
    - 帧跳转
    - 时间轴跳转
    - 多路视频同步

    对应功能 VID-03（视频录制与回放）。
    """

    def __init__(self) -> None:
        self._state: PlaybackState = PlaybackState.IDLE
        self._tracks: dict[str, TrackIndex] = {}
        self._current_track_id: str = ""
        self._current_frame_index: int = 0
        self._speed: float = 1.0        # 回放速度倍率
        self._start_time: float = 0.0   # 回放开始时间（实际）
        self._seek_time: float = 0.0    # 跳转目标时间
        self._looping: bool = False
        self._frame_callback: Optional[callable] = None  # type: ignore
        self._raw_file_handles: dict[str, object] = {}

    @property
    def state(self) -> PlaybackState:
        return self._state

    @property
    def speed(self) -> float:
        return self._speed

    @speed.setter
    def speed(self, val: float) -> None:
        self._speed = max(0.125, min(8.0, val))

    @property
    def total_duration(self) -> float:
        if not self._tracks:
            return 0.0
        return max(
            (t.total_duration for t in self._tracks.values()),
            default=0.0,
        )

    @property
    def current_time(self) -> float:
        """当前回放时间 (s)"""
        if self._state != PlaybackState.PLAYING:
            return self._seek_time
        import time
        elapsed = (time.time() - self._start_time) * self._speed
        return self._seek_time + elapsed

    @property
    def progress(self) -> float:
        """回放进度 [0, 1]"""
        total = self.total_duration
        if total <= 0:
            return 0.0
        return min(1.0, max(0.0, self.current_time / total))

    def load_recording(self, recording_meta_path: str) -> bool:
        """加载录制元数据与帧索引"""
        try:
            with open(recording_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Failed to load recording metadata: %s", e)
            return False

        base_dir = Path(recording_meta_path).parent
        self._tracks.clear()

        for track_meta in meta.get("tracks", []):
            track_id = track_meta["track_id"]
            idx_path = base_dir / f"{meta['recording_id']}_{track_id}_{track_meta['label'].replace(' ', '_')}.mp4.idx"

            if not idx_path.exists():
                logger.warning("Index file not found: %s", idx_path)
                continue

            try:
                with open(idx_path, "r", encoding="utf-8") as f:
                    idx_data = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.error("Failed to load index: %s", e)
                continue

            frames = [
                FrameIndex(
                    sequence=f["seq"],
                    pts=f["pts"],
                    timestamp=f["ts"],
                    keyframe=f.get("keyframe", False),
                    size_bytes=f.get("size", 0),
                )
                for f in idx_data.get("frames", [])
            ]

            total_dur = 0.0
            if frames:
                total_dur = frames[-1].timestamp - frames[0].timestamp

            self._tracks[track_id] = TrackIndex(
                track_id=track_id,
                frames=frames,
                total_duration=total_dur if total_dur > 0 else len(frames) / (track_meta.get("fps", 30)),
            )

            if not self._current_track_id:
                self._current_track_id = track_id

            logger.info("Loaded track %s: %d frames, %.1fs",
                        track_id, len(frames), self._tracks[track_id].total_duration)

        return len(self._tracks) > 0

    def play(self) -> None:
        """开始播放"""
        if not self._tracks:
            return
        self._state = PlaybackState.PLAYING
        self._start_time = __import__("time").time()

    def pause(self) -> None:
        """暂停"""
        if self._state == PlaybackState.PLAYING:
            self._seek_time = self.current_time
            self._state = PlaybackState.PAUSED

    def stop(self) -> None:
        """停止"""
        self._state = PlaybackState.STOPPED
        self._seek_time = 0.0
        self._current_frame_index = 0

    def seek(self, time_seconds: float) -> None:
        """跳转到指定时间"""
        total = self.total_duration
        self._seek_time = max(0.0, min(total, time_seconds))
        if self._state == PlaybackState.PLAYING:
            self._start_time = __import__("time").time()

        # 寻找最近的关键帧
        track = self._tracks.get(self._current_track_id)
        if track and track.frames:
            self._current_frame_index = self._find_nearest_frame(track, self._seek_time)

    def seek_frame(self, frame_index: int) -> None:
        """跳转到指定帧"""
        track = self._tracks.get(self._current_track_id)
        if not track:
            return
        frame_index = max(0, min(len(track.frames) - 1, frame_index))
        self._current_frame_index = frame_index
        self._seek_time = track.frames[frame_index].timestamp
        if self._state == PlaybackState.PLAYING:
            self._start_time = __import__("time").time()

    def step_forward(self) -> None:
        """前进一帧"""
        track = self._tracks.get(self._current_track_id)
        if track:
            next_idx = min(len(track.frames) - 1, self._current_frame_index + 1)
            self.seek_frame(next_idx)

    def step_backward(self) -> None:
        """后退一帧"""
        track = self._tracks.get(self._current_track_id)
        if track:
            prev_idx = max(0, self._current_frame_index - 1)
            self.seek_frame(prev_idx)

    def get_current_frame(self, track_id: str = "") -> Optional[dict]:
        """获取当前时间点的帧元数据（所有轨）"""
        t = self.current_time
        result: dict[str, FrameIndex] = {}

        for tid, track in self._tracks.items():
            if track_id and tid != track_id:
                continue
            idx = self._find_nearest_frame(track, t)
            if idx < len(track.frames):
                result[tid] = track.frames[idx]

        return result

    def set_frame_callback(self, callback: callable) -> None:  # type: ignore
        """设置帧更新回调 callback(track_id, frame_index, frame_data)"""
        self._frame_callback = callback

    @staticmethod
    def _find_nearest_frame(track: TrackIndex, time_seconds: float) -> int:
        """二分查找最接近时间的帧索引"""
        frames = track.frames
        if not frames:
            return 0
        lo, hi = 0, len(frames) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if frames[mid].timestamp < time_seconds:
                lo = mid + 1
            else:
                hi = mid
        return min(lo, len(frames) - 1)
