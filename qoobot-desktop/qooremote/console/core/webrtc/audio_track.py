"""音频轨管理 — 音频流的采集/编码/传输管线

对应功能 VOX-01/02（双向语音通话 + 一键对讲）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 音频配置
# ------------------------------------------------------------------

class AudioCodec(Enum):
    """音频编码格式"""
    OPUS = "opus"
    PCMU = "pcmu"  # G.711 μ-law
    PCMA = "pcma"  # G.711 A-law
    G722 = "g722"


@dataclass
class AudioConfig:
    """音频编码配置"""
    codec: AudioCodec = AudioCodec.OPUS
    sample_rate: int = 48000           # 采样率 (Hz)
    channels: int = 1                  # 声道数
    bitrate_kbps: int = 64             # 编码码率
    frame_duration_ms: int = 20        # 帧时长
    ptime: int = 20                    # 打包时长 (ms)
    echo_cancellation: bool = True     # 回声消除
    noise_suppression: bool = True     # 降噪（对应 VOX-04）
    auto_gain_control: bool = True     # 自动增益
    vad: bool = True                   # 语音活动检测

    @property
    def frame_size_samples(self) -> int:
        """每帧采样数"""
        return int(self.sample_rate * self.frame_duration_ms / 1000)

    @property
    def frame_size_bytes_hint(self) -> int:
        """每帧预估字节数"""
        return int(self.bitrate_kbps * 1000 * self.frame_duration_ms / 1000 / 8)


# ------------------------------------------------------------------
# 语音模式
# ------------------------------------------------------------------

class VoiceMode(Enum):
    """语音通话模式"""
    PTT = "ptt"              # 按键说话（VOX-02）
    FULL_DUPLEX = "full"     # 全双工免提（VOX-03）
    DISABLED = "disabled"


# ------------------------------------------------------------------
# 音频轨
# ------------------------------------------------------------------

class AudioTrack:
    """单个音频轨管理

    封装音频采集/编码/降噪/传输管线。
    """

    def __init__(self, track_id: str, config: Optional[AudioConfig] = None) -> None:
        self.track_id = track_id
        self.config = config or AudioConfig()
        self._mode = VoiceMode.PTT
        self._enabled = True
        self._muted = False
        self._tx_active = False  # 正在发送音频
        self._samples_sent = 0
        self._samples_received = 0
        self._rms_level_tx = 0.0  # 发送音量 RMS
        self._rms_level_rx = 0.0  # 接收音量 RMS

        # 回调
        self.on_audio_tx: callable | None = None  # (samples: np.ndarray) -> None
        self.on_audio_rx: callable | None = None  # (samples: np.ndarray) -> None
        self.on_level_change: callable | None = None  # (tx_rms: float, rx_rms: float) -> None

    # ---- 属性 ----

    @property
    def mode(self) -> VoiceMode:
        return self._mode

    @mode.setter
    def mode(self, value: VoiceMode) -> None:
        old = self._mode
        self._mode = value
        if old != value:
            logger.info("Voice mode: %s → %s", old.value, value.value)
            if value == VoiceMode.DISABLED:
                self._tx_active = False

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
    def is_tx_active(self) -> bool:
        return self._tx_active

    @property
    def rms_tx(self) -> float:
        return self._rms_level_tx

    @property
    def rms_rx(self) -> float:
        return self._rms_level_rx

    # ---- PTT 控制 ----

    def ptt_press(self) -> None:
        """按下 PTT 按键 — 开始发送语音（VOX-02）"""
        if self._mode == VoiceMode.PTT and not self._muted:
            self._tx_active = True
            logger.debug("PTT pressed — TX active")

    def ptt_release(self) -> None:
        """松开 PTT 按键 — 停止发送语音"""
        self._tx_active = False
        logger.debug("PTT released — TX inactive")

    def toggle_full_duplex(self) -> None:
        """切换全双工模式"""
        if self._mode == VoiceMode.FULL_DUPLEX:
            self._mode = VoiceMode.PTT
            self._tx_active = False
        else:
            self._mode = VoiceMode.FULL_DUPLEX
            self._tx_active = True

    # ---- 音频数据处理 ----

    def send_samples(self, samples: np.ndarray) -> None:
        """发送音频采样数据

        Args:
            samples: 音频采样数据 (N,) 或 (N, channels)
        """
        if not self._tx_active or self._muted:
            return

        # 计算 RMS 音量
        self._rms_level_tx = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        self._samples_sent += len(samples) if samples.ndim == 1 else samples.shape[0]

        if self.on_audio_tx:
            self.on_audio_tx(samples)
        if self.on_level_change:
            self.on_level_change(self._rms_level_tx, self._rms_level_rx)

    def receive_samples(self, samples: np.ndarray) -> None:
        """接收远程音频采样数据"""
        if self._muted:
            return

        self._rms_level_rx = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        self._samples_received += len(samples) if samples.ndim == 1 else samples.shape[0]

        if self.on_audio_rx:
            self.on_audio_rx(samples)
        if self.on_level_change:
            self.on_level_change(self._rms_level_tx, self._rms_level_rx)

    # ---- 统计 ----

    def get_stats(self) -> dict:
        """获取音频轨统计"""
        return {
            "track_id": self.track_id,
            "mode": self._mode.value,
            "enabled": self._enabled,
            "muted": self._muted,
            "tx_active": self._tx_active,
            "rms_tx": round(self._rms_level_tx, 4),
            "rms_rx": round(self._rms_level_rx, 4),
            "samples_sent": self._samples_sent,
            "samples_received": self._samples_received,
            "codec": self.config.codec.value,
            "sample_rate": self.config.sample_rate,
            "channels": self.config.channels,
            "noise_suppression": self.config.noise_suppression,
            "echo_cancellation": self.config.echo_cancellation,
        }

    def reset(self) -> None:
        """重置统计"""
        self._samples_sent = 0
        self._samples_received = 0
        self._rms_level_tx = 0.0
        self._rms_level_rx = 0.0
