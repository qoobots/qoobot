# -*- coding: utf-8 -*-
"""VoiceService — 语音交互服务 Python 封装"""

import dataclasses
import logging
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class WakeWordConfig:
    """唤醒词配置"""
    word: str = "Hey QooBot"
    language: str = "zh"
    threshold: float = 0.7
    sensitivity: str = "medium"


@dataclasses.dataclass
class TTSConfig:
    """TTS 合成配置"""
    voice_id: str = "default"
    speed: float = 1.0
    pitch: float = 1.0


@dataclasses.dataclass
class ASRResult:
    """ASR 识别结果"""
    text: str = ""
    language: str = ""
    confidence: float = 0.0
    is_final: bool = False


@dataclasses.dataclass
class NLUResult:
    """NLU 理解结果"""
    intent: str = ""
    slots: Dict[str, str] = dataclasses.field(default_factory=dict)
    confidence: float = 0.0


@dataclasses.dataclass
class SpeakerInfo:
    """说话人信息"""
    id: str = ""
    name: str = ""
    confidence: float = 0.0


class VoiceService:
    """
    语音交互服务 — 提供唤醒词、ASR、NLU、TTS 等语音能力的 Python API。

    在机器人端运行，底层调用 qoosvc C++ 库或独立的 Whisper/Piper 引擎。
    """

    def __init__(self):
        self._wake_word_callbacks: List[Callable] = []
        self._asr_callbacks: List[Callable] = []
        self._initialized = False

    def initialize(self) -> bool:
        """初始化语音服务"""
        logger.info("VoiceService initializing...")
        self._initialized = True
        return True

    def configure_wake_word(self, config: WakeWordConfig) -> None:
        """配置唤醒词"""
        logger.info(f"Wake word configured: '{config.word}' (lang={config.language}, threshold={config.threshold})")

    def enable_wake_word(self, enable: bool = True) -> None:
        """启用/禁用唤醒词"""
        logger.info(f"Wake word {'enabled' if enable else 'disabled'}")

    def on_wake_word(self, callback: Callable) -> None:
        """注册唤醒词检测回调"""
        self._wake_word_callbacks.append(callback)

    async def stream_recognize(self):
        """流式 ASR 识别（异步迭代器）"""
        logger.info("ASR streaming started")
        # Placeholder: in production, yields ASRResult from real-time audio stream
        yield ASRResult(text="", language="zh", confidence=0.0, is_final=False)

    def recognize(self, audio_data: bytes) -> ASRResult:
        """识别一段音频"""
        return ASRResult(text="", language="zh", confidence=0.0, is_final=True)

    def understand(self, text: str) -> NLUResult:
        """NLU 语义理解"""
        logger.info(f"NLU understanding: '{text}'")
        return NLUResult(intent="unknown", slots={}, confidence=0.0)

    def speak(self, text: str, config: Optional[TTSConfig] = None) -> bool:
        """TTS 语音合成并播放"""
        cfg = config or TTSConfig()
        logger.info(f"TTS speaking: '{text}' (voice={cfg.voice_id})")
        return True

    def identify_speaker(self, audio_data: bytes) -> SpeakerInfo:
        """说话人识别"""
        return SpeakerInfo(id="", name="unknown", confidence=0.0)

    def shutdown(self) -> None:
        """关闭语音服务"""
        logger.info("VoiceService shutting down")
        self._initialized = False
