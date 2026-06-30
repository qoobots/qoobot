"""视频流 ViewModel

管理多路视频流的生命周期、码率/分辨率配置。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

import numpy as np


class VideoStreamInfo:
    """单路视频流信息"""
    def __init__(self, camera_id: int, name: str = "") -> None:
        self.camera_id = camera_id
        self.name = name or f"Camera {camera_id + 1}"
        self.resolution: str = "1280x720"
        self.fps: float = 0.0
        self.bitrate_mbps: float = 0.0
        self.latency_ms: float = 0.0
        self.connected: bool = False


class VideoViewModel(QObject):
    """视频流 ViewModel

    管理多路视频流状态，向 UI 层提供：
    - 视频流列表
    - 码率/帧率/延迟统计
    - 帧数据分发
    """

    frame_received = Signal(int, object)      # camera_id, np.ndarray
    bitrate_updated = Signal(float)           # total bitrate mbps
    stream_status_changed = Signal(int, bool)  # camera_id, connected

    def __init__(self, camera_count: int = 4, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._streams: list[VideoStreamInfo] = [
            VideoStreamInfo(i) for i in range(camera_count)
        ]

    @property
    def streams(self) -> list[VideoStreamInfo]:
        return self._streams

    @property
    def camera_count(self) -> int:
        return len(self._streams)

    def get_stream(self, camera_id: int) -> Optional[VideoStreamInfo]:
        for s in self._streams:
            if s.camera_id == camera_id:
                return s
        return None

    def on_video_frame(self, camera_id: int, frame: np.ndarray) -> None:
        """接收视频帧"""
        self.frame_received.emit(camera_id, frame)

        stream = self.get_stream(camera_id)
        if stream:
            stream.connected = True
            stream.latency_ms = 0  # 由上层填入实际延迟

    def on_stream_status(self, camera_id: int, connected: bool) -> None:
        """接收流状态变更"""
        stream = self.get_stream(camera_id)
        if stream:
            stream.connected = connected
        self.stream_status_changed.emit(camera_id, connected)

    def update_total_bitrate(self, bitrate_mbps: float) -> None:
        self.bitrate_updated.emit(bitrate_mbps)
