"""视频轨管理 — 视频流的编码/解码/渲染管线

对应功能 VID-01/02（视频回传 + 自适应码率）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 视频配置
# ------------------------------------------------------------------

class VideoCodec(Enum):
    """视频编码格式"""
    H264 = "h264"
    H265 = "h265"
    VP8 = "vp8"
    VP9 = "vp9"
    AV1 = "av1"


@dataclass
class VideoResolution:
    """视频分辨率"""
    width: int
    height: int

    @property
    def total_pixels(self) -> int:
        return self.width * self.height

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height else 1.0

    def __str__(self) -> str:
        labels = {
            (1920, 1080): "1080p",
            (1280, 720): "720p",
            (960, 540): "540p",
            (640, 480): "480p",
            (320, 240): "240p",
        }
        return labels.get((self.width, self.height), f"{self.width}x{self.height}")

    @classmethod
    def p1080(cls) -> "VideoResolution":
        return cls(1920, 1080)

    @classmethod
    def p720(cls) -> "VideoResolution":
        return cls(1280, 720)

    @classmethod
    def p540(cls) -> "VideoResolution":
        return cls(960, 540)

    @classmethod
    def p480(cls) -> "VideoResolution":
        return cls(640, 480)


@dataclass
class VideoConfig:
    """视频编码配置"""
    codec: VideoCodec = VideoCodec.H264
    resolution: VideoResolution = field(default_factory=VideoResolution.p720)
    fps: int = 30
    max_bitrate_kbps: int = 2500
    min_bitrate_kbps: int = 300
    keyframe_interval: int = 60  # 关键帧间隔（帧数）
    hardware_encoder: bool = False

    @property
    def target_bitrate_per_pixel(self) -> float:
        """每像素目标码率 (bps/px)"""
        pixels = self.resolution.total_pixels * self.fps
        return (self.max_bitrate_kbps * 1000) / pixels if pixels else 0


# ------------------------------------------------------------------
# 自适应码率控制
# ------------------------------------------------------------------

@dataclass
class BitrateProfile:
    """码率档位（对应 VID-02 自适应码率）"""
    resolution: VideoResolution
    fps: int
    bitrate_kbps: int

    @classmethod
    def profiles(cls) -> list["BitrateProfile"]:
        """预定义的码率档位（从高到低）"""
        return [
            cls(VideoResolution.p1080(), 30, 4000),
            cls(VideoResolution.p720(), 30, 2500),
            cls(VideoResolution.p720(), 24, 1500),
            cls(VideoResolution.p540(), 24, 800),
            cls(VideoResolution.p480(), 20, 400),
            cls(VideoResolution.p480(), 15, 200),
        ]


class AdaptiveBitrateController:
    """自适应码率控制器

    根据网络延迟和丢包率动态调整视频质量。
    使用加性增/乘性减 (AIMD) 策略。

    对应功能 VID-02（自适应码率）。
    """

    def __init__(self, profiles: Optional[list[BitrateProfile]] = None) -> None:
        self._profiles = profiles or BitrateProfile.profiles()
        self._current_idx = 1  # 默认从 720p@30fps 开始
        self._rtt_samples: list[float] = []
        self._loss_samples: list[float] = []
        self._max_samples = 20

        # 阈值
        self.rtt_upgrade_threshold_ms: float = 50.0   # RTT < 50ms 可升级
        self.rtt_downgrade_threshold_ms: float = 200.0 # RTT > 200ms 降级
        self.loss_upgrade_threshold: float = 0.01      # 丢包 < 1% 可升级
        self.loss_downgrade_threshold: float = 0.05    # 丢包 > 5% 降级

        # 冷却
        self._last_switch_time: float = 0.0
        self._switch_cooldown_s: float = 3.0

    @property
    def current_profile(self) -> BitrateProfile:
        return self._profiles[self._current_idx]

    def feed_stats(self, rtt_ms: float, loss_rate: float) -> None:
        """喂入网络统计，触发自适应调整

        Args:
            rtt_ms: 往返延迟（毫秒）
            loss_rate: 丢包率 (0.0 ~ 1.0)
        """
        self._rtt_samples.append(rtt_ms)
        self._loss_samples.append(loss_rate)
        if len(self._rtt_samples) > self._max_samples:
            self._rtt_samples.pop(0)
            self._loss_samples.pop(0)

        import time
        now = time.time()
        if now - self._last_switch_time < self._switch_cooldown_s:
            return

        avg_rtt = sum(self._rtt_samples) / len(self._rtt_samples)
        avg_loss = sum(self._loss_samples) / len(self._loss_samples)

        if avg_rtt > self.rtt_downgrade_threshold_ms or avg_loss > self.loss_downgrade_threshold:
            self._downgrade()
        elif (avg_rtt < self.rtt_upgrade_threshold_ms and avg_loss < self.loss_upgrade_threshold
              and len(self._rtt_samples) >= 10):
            self._upgrade()

    def _downgrade(self) -> None:
        if self._current_idx < len(self._profiles) - 1:
            self._current_idx += 1
            self._last_switch_time = __import__("time").time()
            logger.info("ABR downgrade → %s @ %d kbps",
                        self.current_profile.resolution, self.current_profile.bitrate_kbps)

    def _upgrade(self) -> None:
        if self._current_idx > 0:
            self._current_idx -= 1
            self._last_switch_time = __import__("time").time()
            logger.info("ABR upgrade → %s @ %d kbps",
                        self.current_profile.resolution, self.current_profile.bitrate_kbps)

    def reset(self) -> None:
        """重置控制器状态"""
        self._current_idx = 1
        self._rtt_samples.clear()
        self._loss_samples.clear()


# ------------------------------------------------------------------
# 视频轨
# ------------------------------------------------------------------

class VideoTrack:
    """单个视频轨管理

    封装视频帧接收/解码/渲染管线。
    """

    def __init__(self, camera_id: str, config: Optional[VideoConfig] = None) -> None:
        self.camera_id = camera_id
        self.config = config or VideoConfig()
        self._enabled = True
        self._muted = False
        self._last_frame: Optional[np.ndarray] = None
        self._frame_count = 0
        self._fps_actual = 0.0
        self._bytes_received = 0
        self._bitrate_kbps = 0.0
        self._abr = AdaptiveBitrateController()

        # 回调
        self.on_frame: callable | None = None  # (frame: np.ndarray) -> None
        self.on_stats: callable | None = None  # (stats: dict) -> None

    # ---- 属性 ----

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        self._muted = value

    @property
    def last_frame(self) -> Optional[np.ndarray]:
        return self._last_frame

    @property
    def fps(self) -> float:
        return self._fps_actual

    @property
    def bitrate_kbps(self) -> float:
        return self._bitrate_kbps

    @property
    def current_resolution(self) -> VideoResolution:
        return self._abr.current_profile.resolution

    # ---- 帧处理 ----

    def receive_frame(self, frame_data: np.ndarray | bytes) -> None:
        """接收视频帧

        Args:
            frame_data: 解码后的帧数据（H×W×3 numpy 数组或编码字节）
        """
        if not self._enabled:
            return

        if isinstance(frame_data, bytes):
            # 实际场景中需解码，此处假设已解码为 numpy
            import io
            try:
                from PIL import Image
                img = Image.open(io.BytesIO(frame_data))
                frame = np.array(img)
            except Exception:
                return
        else:
            frame = frame_data

        self._last_frame = frame
        self._frame_count += 1
        self._bytes_received += frame.nbytes

        if self.on_frame:
            self.on_frame(frame)

    def feed_network_stats(self, rtt_ms: float, loss_rate: float) -> None:
        """喂入网络统计以触发自适应码率"""
        self._abr.feed_stats(rtt_ms, loss_rate)

    def get_stats(self) -> dict:
        """获取视频轨统计"""
        return {
            "camera_id": self.camera_id,
            "enabled": self._enabled,
            "muted": self._muted,
            "frame_count": self._frame_count,
            "fps_actual": self._fps_actual,
            "bitrate_kbps": self._bitrate_kbps,
            "resolution": str(self.current_resolution),
            "codec": self.config.codec.value,
            "abr_profile": {
                "bitrate": self._abr.current_profile.bitrate_kbps,
                "fps": self._abr.current_profile.fps,
                "resolution": str(self._abr.current_profile.resolution),
            },
        }

    def reset(self) -> None:
        """重置统计"""
        self._last_frame = None
        self._frame_count = 0
        self._bytes_received = 0
        self._abr.reset()


# ------------------------------------------------------------------
# 视频轨管理
# ------------------------------------------------------------------

class VideoTrackManager:
    """多路视频轨管理器

    管理多个摄像头视频轨的集合。
    """

    def __init__(self) -> None:
        self._tracks: dict[str, VideoTrack] = {}

    @property
    def tracks(self) -> dict[str, VideoTrack]:
        return dict(self._tracks)

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._tracks.values() if t.enabled)

    def add_track(self, camera_id: str, config: Optional[VideoConfig] = None) -> VideoTrack:
        """添加视频轨"""
        track = VideoTrack(camera_id, config)
        self._tracks[camera_id] = track
        logger.info("Video track added: %s", camera_id)
        return track

    def remove_track(self, camera_id: str) -> None:
        """移除视频轨"""
        self._tracks.pop(camera_id, None)

    def get_track(self, camera_id: str) -> Optional[VideoTrack]:
        return self._tracks.get(camera_id)

    def enable_all(self, enabled: bool = True) -> None:
        """启用/禁用所有视频轨"""
        for track in self._tracks.values():
            track.enabled = enabled

    def get_combined_stats(self) -> dict:
        """获取所有视频轨的综合统计"""
        total_bitrate = sum(t.bitrate_kbps for t in self._tracks.values())
        return {
            "active_count": self.active_count,
            "total_count": len(self._tracks),
            "total_bitrate_kbps": total_bitrate,
            "tracks": {cid: t.get_stats() for cid, t in self._tracks.items()},
        }
