"""语音 ViewModel — 连接 VoicePanel 与核心语音服务

管理语音通话状态、PTT 控制、音量指标。
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal

from console.core.webrtc.audio_track import AudioTrack, VoiceMode, AudioConfig


class VoiceViewModel(QObject):
    """语音通话 ViewModel

    桥接 UI (VoicePanel) 与核心 (AudioTrack)。
    """

    voice_mode_changed = Signal(str)
    tx_level_changed = Signal(float)
    rx_level_changed = Signal(float)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._audio_track: Optional[AudioTrack] = None
        self._mode = VoiceMode.PTT

    @property
    def audio_track(self) -> Optional[AudioTrack]:
        return self._audio_track

    @property
    def mode(self) -> VoiceMode:
        return self._mode

    def bind_audio_track(self, track: AudioTrack) -> None:
        """绑定音频轨"""
        self._audio_track = track
        track.on_level_change = self._on_level_change

    def set_mode(self, mode: VoiceMode) -> None:
        """切换语音模式"""
        self._mode = mode
        if self._audio_track:
            self._audio_track.mode = mode
        self.voice_mode_changed.emit(mode.value)

    def ptt_press(self) -> None:
        """PTT 按下"""
        if self._audio_track:
            self._audio_track.ptt_press()

    def ptt_release(self) -> None:
        """PTT 松开"""
        if self._audio_track:
            self._audio_track.ptt_release()

    def toggle_full_duplex(self) -> None:
        """切换全双工"""
        if self._mode == VoiceMode.FULL_DUPLEX:
            self.set_mode(VoiceMode.PTT)
        else:
            self.set_mode(VoiceMode.FULL_DUPLEX)

    def set_muted(self, muted: bool) -> None:
        """设置静音"""
        if self._audio_track:
            self._audio_track.muted = muted

    def apply_config(self, config: AudioConfig) -> None:
        """应用音频配置"""
        if self._audio_track:
            self._audio_track.config = config

    def _on_level_change(self, tx_rms: float, rx_rms: float) -> None:
        self.tx_level_changed.emit(tx_rms)
        self.rx_level_changed.emit(rx_rms)
