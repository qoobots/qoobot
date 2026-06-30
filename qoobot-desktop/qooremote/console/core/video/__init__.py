"""视频录制与回放 — 本地视频流持久化

管理从 WebRTC 视频轨收到的视频流，提供本地录制和回放功能。
支持多路视频同时录制、帧索引、关键帧提取。

对应功能 VID-03（视频录制与回放）。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VideoCodec(str, Enum):
    H264 = "h264"
    H265 = "h265"
    VP8 = "vp8"
    VP9 = "vp9"
    AV1 = "av1"
    RAW = "raw"       # 原始帧（未压缩）


@dataclass
class VideoFrame:
    """视频帧"""
    track_id: str = ""
    timestamp: float = 0.0          # Unix 时间
    pts: int = 0                    # 呈现时间戳 (Presentation Timestamp)
    width: int = 0
    height: int = 0
    pixel_format: str = "RGB24"     # RGB24 / YUV420 / NV12
    data: bytes = b""
    keyframe: bool = False
    sequence_number: int = 0


@dataclass
class VideoTrackInfo:
    """视频轨信息"""
    track_id: str = ""
    label: str = ""                 # 摄像头名称
    codec: VideoCodec = VideoCodec.H264
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    bitrate_bps: int = 4_000_000


@dataclass
class VideoRecording:
    """视频录制会话"""
    recording_id: str = ""
    tracks: list[VideoTrackInfo] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    total_frames: int = 0
    file_paths: dict[str, str] = field(default_factory=dict)  # track_id -> file_path
    metadata: dict = field(default_factory=dict)


class VideoRecorder:
    """视频录制器

    管理多路视频轨的本地录制，支持：
    - 多路视频独立文件存储
    - 关键帧提取
    - 录制元数据管理

    对应功能 VID-03（视频录制与回放）。
    """

    def __init__(self, output_dir: str = "") -> None:
        self._output_dir = Path(output_dir) if output_dir else Path("./recordings/videos")
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._active_recordings: dict[str, VideoRecording] = {}
        self._track_buffers: dict[str, dict[str, list[VideoFrame]]] = {}  # recording_id -> {track_id -> frames}
        self._completed_recordings: list[VideoRecording] = []
        self._is_recording: bool = False
        self._current_recording_id: Optional[str] = None

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def current_recording(self) -> Optional[VideoRecording]:
        if self._current_recording_id:
            return self._active_recordings.get(self._current_recording_id)
        return None

    @property
    def completed_recordings(self) -> list[VideoRecording]:
        return list(self._completed_recordings)

    def start(self, recording_id: str,
              tracks: list[VideoTrackInfo],
              metadata: Optional[dict] = None) -> None:
        """开始录制"""
        if self._is_recording:
            logger.warning("Already recording, stopping previous")
            self.stop()

        recording = VideoRecording(
            recording_id=recording_id,
            tracks=tracks,
            start_time=time.time(),
            metadata=metadata or {},
        )

        # 为每路视频轨分配文件路径
        for track in tracks:
            filename = f"{recording_id}_{track.track_id}_{track.label.replace(' ', '_')}.mp4"
            recording.file_paths[track.track_id] = str(self._output_dir / filename)

        self._active_recordings[recording_id] = recording
        self._track_buffers[recording_id] = {t.track_id: [] for t in tracks}
        self._current_recording_id = recording_id
        self._is_recording = True

        logger.info("Video recording started: %s with %d tracks",
                     recording_id, len(tracks))

    def record_frame(self, track_id: str, frame: VideoFrame) -> None:
        """记录一帧"""
        if not self._is_recording or not self._current_recording_id:
            return

        buffers = self._track_buffers.get(self._current_recording_id)
        if buffers is None:
            return

        track_buffer = buffers.get(track_id)
        if track_buffer is None:
            return

        track_buffer.append(frame)

        recording = self._active_recordings[self._current_recording_id]
        recording.total_frames += 1

    def stop(self) -> Optional[VideoRecording]:
        """停止当前录制"""
        if not self._is_recording or not self._current_recording_id:
            return None

        recording = self._active_recordings[self._current_recording_id]
        recording.end_time = time.time()

        self._is_recording = False

        # 将帧写入磁盘（实际项目中用 FFmpeg/OpenCV）
        self._flush_to_disk(recording)

        self._completed_recordings.append(recording)
        rid = self._current_recording_id
        self._current_recording_id = None

        # 清理缓冲区
        self._track_buffers.pop(rid, None)

        duration = recording.end_time - recording.start_time
        logger.info("Video recording stopped: %s (%.1fs, %d frames)",
                     recording.recording_id, duration, recording.total_frames)

        return recording

    def _flush_to_disk(self, recording: VideoRecording) -> None:
        """将帧缓冲写入磁盘

        实际项目中使用 FFmpeg/OpenCV VideoWriter，
        此处保存帧元数据索引。
        """
        buffers = self._track_buffers.get(recording.recording_id, {})

        for track_id, frames in buffers.items():
            filepath = recording.file_paths.get(track_id, "")
            if not filepath:
                continue

            # 写入帧索引 (.vididx JSON)
            import json
            idx_path = filepath + ".idx"
            index = [
                {
                    "seq": f.sequence_number,
                    "pts": f.pts,
                    "ts": f.timestamp,
                    "keyframe": f.keyframe,
                    "size": len(f.data),
                }
                for f in frames
            ]

            try:
                with open(idx_path, "w", encoding="utf-8") as f:
                    json.dump({"track_id": track_id, "frames": index}, f, indent=2)
                logger.debug("Index saved: %s (%d frames)", idx_path, len(index))
            except OSError as e:
                logger.error("Failed to write index %s: %s", idx_path, e)

            # 写入原始帧数据
            raw_path = filepath + ".raw"
            try:
                with open(raw_path, "wb") as f:
                    for frame in frames:
                        f.write(frame.data)
                logger.debug("Raw frames saved: %s (%.1f MB)",
                             raw_path, sum(len(fr.data) for fr in frames) / 1e6)
            except OSError as e:
                logger.error("Failed to write raw frames %s: %s", raw_path, e)

        # 写入录制元数据
        import json
        meta_path = str(self._output_dir / f"{recording.recording_id}.meta.json")
        meta = {
            "recording_id": recording.recording_id,
            "start_time": recording.start_time,
            "end_time": recording.end_time,
            "total_frames": recording.total_frames,
            "tracks": [
                {
                    "track_id": t.track_id,
                    "label": t.label,
                    "codec": t.codec.value,
                    "width": t.width,
                    "height": t.height,
                    "fps": t.fps,
                    "frame_count": len(buffers.get(t.track_id, [])),
                } for t in recording.tracks
            ],
            "metadata": recording.metadata,
        }
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except OSError as e:
            logger.error("Failed to write metadata %s: %s", meta_path, e)

    def extract_keyframes(self, recording_id: str,
                          track_id: str = "") -> list[VideoFrame]:
        """提取关键帧列表"""
        if recording_id not in self._track_buffers:
            if recording_id in self._active_recordings:
                return []
            return []

        buffers = self._track_buffers[recording_id]
        if track_id:
            return [f for f in buffers.get(track_id, []) if f.keyframe]

        all_keyframes: list[VideoFrame] = []
        for track_buffer in buffers.values():
            all_keyframes.extend(f for f in track_buffer if f.keyframe)
        return sorted(all_keyframes, key=lambda f: f.timestamp)
