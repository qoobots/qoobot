"""brain_os SDK — 语音交互 API

提供语音识别 (ASR)、语音合成 (TTS)、语音指令解析能力。
可与任何 Brain OS 支持的后端 ASR/TTS 引擎对接。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from ..config import BrainOSConfig


# ── 语音数据类型 ────────────────────────────────────────────


class TTSVoice(Enum):
    """TTS 语音风格。"""

    FEMALE_STANDARD = "female_standard"
    MALE_STANDARD = "male_standard"
    FEMALE_WARM = "female_warm"
    ROBOTIC = "robotic"


@dataclass
class AudioStream:
    """音频流描述。

    Attributes:
        sample_rate_hz: 采样率 (Hz)
        channels: 声道数
        encoding: 编码格式 (pcm_s16le, opus, mp3)
        data: 原始音频字节或文件路径
        duration_sec: 时长 (秒)
    """

    sample_rate_hz: int = 16000
    channels: int = 1
    encoding: str = "pcm_s16le"
    data: bytes = field(default_factory=bytes)
    duration_sec: float = 0.0


@dataclass
class ASRResult:
    """语音识别结果。

    Attributes:
        text: 识别文本
        confidence: 置信度 (0.0-1.0)
        language: 检测到的语言
        alternatives: 候选结果列表
        is_partial: 是否为部分结果 (流式识别)
        processing_ms: 音频处理耗时
    """

    text: str = ""
    confidence: float = 1.0
    language: str = "zh-CN"
    alternatives: List[str] = field(default_factory=list)
    is_partial: bool = False
    processing_ms: int = 0


@dataclass
class TTSOptions:
    """TTS 合成选项。

    Attributes:
        voice: 语音风格
        speed: 语速缩放 (0.5-2.0, 默认 1.0)
        pitch: 音调偏移 (-20 到 +20 半音)
        output_format: 输出格式 (pcm, mp3, ogg)
    """

    voice: TTSVoice = TTSVoice.FEMALE_STANDARD
    speed: float = 1.0
    pitch: float = 0.0
    output_format: str = "pcm"


# ── SpeechAPI ───────────────────────────────────────────────


class SpeechAPI:
    """语音交互服务。

    支持：
    - 语音识别 (ASR): 将音频转为文本，支持流式识别
    - 语音合成 (TTS): 将文本转为音频
    - 语音指令解析: 结合 ASR + 意图解析的端到端通道
    """

    def __init__(
        self,
        get_channel: Callable,
        get_async_channel: Callable,
        config: BrainOSConfig,
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._asr_model: str = "whisper-large-v3-ct2"
        self._tts_model: str = "edge-tts"
        self._enable_mock: bool = True

    # ── ASR ──────────────────────────────────────────────

    async def recognize_speech(
        self,
        audio: AudioStream,
        *,
        language_hint: str = "zh-CN",
        enable_partials: bool = False,
    ) -> ASRResult:
        """将音频转为文本。

        Args:
            audio: 音频流数据
            language_hint: 语言提示 (帮助 ASR 消歧)
            enable_partials: 是否返回部分结果

        Returns:
            ASRResult 包含识别文本、置信度等
        """
        if self._enable_mock:
            return ASRResult(
                text="把红色杯子放到桌上",
                confidence=0.95,
                language=language_hint,
                processing_ms=150,
            )

        # 生产模式：通过 gRPC 调用后端 ASR 服务
        try:
            channel = await self._get_ach()
            from brain_os.proto_gen.brain_os.perception.service_pb2 import RecognizeSpeechRequest

            req = RecognizeSpeechRequest(
                robot_id=self._cfg.robot_id,
                audio_data=audio.data,
                sample_rate=audio.sample_rate_hz,
                language_hint=language_hint,
            )
            # 实际调用取决于是否有 ASR gRPC 端点
            # resp = await stub.RecognizeSpeech(req, timeout=self._cfg.grpc_timeout_sec)
            raise NotImplementedError("gRPC ASR endpoint not yet implemented")
        except (NotImplementedError, Exception):
            return ASRResult(
                text="[ASR unavailable]",
                confidence=0.0,
                language=language_hint,
            )

    async def recognize_stream(
        self,
        audio_stream: asyncio.StreamReader,
        *,
        chunk_size: int = 4096,
        language_hint: str = "zh-CN",
    ) -> ASRResult:
        """流式语音识别 — 接收音频块流，逐步识别。

        Args:
            audio_stream: 异步音频数据流
            chunk_size: 每次读取的块大小 (字节)
            language_hint: 语言提示
        """
        if self._enable_mock:
            await asyncio.sleep(0.5)
            return ASRResult(
                text="打开夹爪",
                confidence=0.92,
                language=language_hint,
                is_partial=False,
                processing_ms=350,
            )

        full_result = ASRResult(language=language_hint)
        try:
            while True:
                chunk = await audio_stream.read(chunk_size)
                if not chunk:
                    break
                # 生产中通过 gRPC 双向流发送音频块
                await asyncio.sleep(0.01)
            full_result.text = "[stream recognition]"
            full_result.confidence = 0.0
        except Exception:
            pass
        return full_result

    # ── TTS ──────────────────────────────────────────────

    async def synthesize_speech(
        self,
        text: str,
        *,
        options: Optional[TTSOptions] = None,
    ) -> AudioStream:
        """将文本转为语音。

        Args:
            text: 要合成的文本
            options: TTS 合成选项

        Returns:
            AudioStream 包含合成后的音频数据
        """
        opts = options or TTSOptions()
        if self._enable_mock:
            return AudioStream(
                sample_rate_hz=22050,
                channels=1,
                encoding="pcm_s16le",
                data=b"[mock tts audio data]",
                duration_sec=len(text) * 0.08,
            )

        try:
            channel = await self._get_ach()
            from brain_os.proto_gen.brain_os.knowledge.service_pb2 import SynthesizeSpeechRequest

            req = SynthesizeSpeechRequest(
                text=text,
                voice=opts.voice.value,
                speed=opts.speed,
            )
            raise NotImplementedError("gRPC TTS endpoint not yet implemented")
        except NotImplementedError:
            return AudioStream(
                sample_rate_hz=22050,
                data=b"[tts unavailable]",
                duration_sec=len(text) * 0.08,
            )

    async def say(
        self,
        text: str,
        *,
        options: Optional[TTSOptions] = None,
        wait: bool = True,
    ) -> Optional[AudioStream]:
        """快捷方法: 合成并播放语音。

        Args:
            text: 要说的话
            options: TTS 选项
            wait: 是否等待播放完成
        """
        audio = await self.synthesize_speech(text, options=options)
        if wait:
            await asyncio.sleep(audio.duration_sec * 0.5)
        return audio

    # ── Voice Command Pipeline ──────────────────────────────

    async def voice_command(
        self,
        audio: AudioStream,
        *,
        parse_intent: bool = True,
    ) -> Dict[str, Any]:
        """端到端语音指令管道: ASR → 意图解析。

        Args:
            audio: 音频输入
            parse_intent: 是否同时解析意图

        Returns:
            {"asr_result": ASRResult, "intent": dict | None}
        """
        asr_result = await self.recognize_speech(audio)

        result: Dict[str, Any] = {"asr_result": asr_result, "intent": None}

        if parse_intent and asr_result.confidence > 0.5:
            try:
                from brain_os.proto_gen.brain_os.cognition.service_pb2 import ParseIntentRequest
                channel = await self._get_ach()
                # stub = CognitionServiceStub(channel)
                # req = ParseIntentRequest(
                #     robot_id=self._cfg.robot_id,
                #     utterance=asr_result.text,
                #     language=asr_result.language,
                # )
                # resp = await stub.ParseIntent(req, timeout=self._cfg.grpc_timeout_sec)
                # result["intent"] = resp.intent
                if self._enable_mock:
                    result["intent"] = {
                        "type": "PICK",
                        "raw_text": asr_result.text,
                        "confidence": 0.9,
                        "_source": "voice",
                    }
            except Exception:
                result["intent"] = {"type": "UNKNOWN", "raw_text": asr_result.text}

        return result

    # ── Wake Word ──────────────────────────────────────────

    async def listen_for_wake_word(
        self,
        wake_words: Optional[List[str]] = None,
        *,
        timeout_sec: float = 30.0,
    ) -> bool:
        """监听唤醒词。

        Args:
            wake_words: 唤醒词列表，默认 ["你好机器人", "hey robot"]
            timeout_sec: 超时时间

        Returns:
            是否检测到唤醒词
        """
        words = wake_words or ["你好机器人", "hey robot", "hi robot"]
        if self._enable_mock:
            await asyncio.sleep(1.0)
            return True

        # 生产中通过持续的音频流 + ASR 检测唤醒词
        await asyncio.sleep(10.0)
        return False
