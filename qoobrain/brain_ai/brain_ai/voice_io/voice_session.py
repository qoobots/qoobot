"""
brain_ai/voice_io/voice_session.py — Full voice interaction session manager.

Orchestrates: AudioStream → ASREngine → BrainAgent → TTSEngine → speaker
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VoiceSession:
    """
    A complete voice interaction loop.

    Usage:
        session = VoiceSession(agent=brain_agent)
        asyncio.run(session.run())   # blocking loop
        # or
        result = await session.listen_once()
    """

    def __init__(
        self,
        agent=None,              # BrainAgent instance
        asr_engine=None,         # ASREngine instance (optional, auto-init)
        tts_engine=None,         # TTSEngine instance (optional, auto-init)
        language: str = "zh",
    ) -> None:
        self._agent  = agent
        self._asr    = asr_engine
        self._tts    = tts_engine
        self._lang   = language
        self._active = False

    def _ensure_engines(self) -> None:
        if self._asr is None:
            from brain_ai.voice_io.asr_engine import ASREngine
            self._asr = ASREngine()
        if self._tts is None:
            from brain_ai.voice_io.tts_engine import TTSEngine
            self._tts = TTSEngine()

    async def listen_once(self) -> dict:
        """
        Listen for one utterance, process it, return the plan dict.
        """
        self._ensure_engines()
        from brain_ai.voice_io.audio_stream import AudioStream

        audio_stream = AudioStream()
        audio_stream.start()
        logger.info("VoiceSession: listening …")
        audio_bytes = audio_stream.read_utterance(timeout_sec=10.0)
        audio_stream.stop()

        if not audio_bytes:
            return {"error": "no_audio"}

        # ASR
        asr_result = self._asr.transcribe(audio_bytes)
        logger.info(f"ASR: {asr_result.text!r} (conf={asr_result.confidence:.2f})")
        if not asr_result.text.strip():
            await self._say("没有听清楚，请再说一遍。")
            return {"error": "empty_transcription"}

        # Feedback
        await self._say(f"好的，正在执行：{asr_result.text}")

        # Agent processing
        if self._agent is not None:
            plan = await self._agent.process(asr_result.text)
        else:
            plan = {"instruction": asr_result.text, "error": "no_agent"}

        return plan

    async def run(self) -> None:
        """Continuous voice interaction loop."""
        self._active = True
        logger.info("VoiceSession: starting continuous loop …")
        while self._active:
            try:
                result = await self.listen_once()
                if result.get("error"):
                    logger.warning(f"VoiceSession error: {result['error']}")
                else:
                    logger.info(f"Plan ready: {result.get('plan_id', '?')}")
            except KeyboardInterrupt:
                self._active = False
            except Exception as exc:
                logger.error(f"VoiceSession error: {exc}")
                await asyncio.sleep(1.0)

    def stop(self) -> None:
        self._active = False

    async def _say(self, text: str) -> None:
        if self._tts and self._tts.is_available:
            try:
                audio = await self._tts.asynthesize(text)
                # TODO: play audio via sounddevice or subprocess
                logger.debug(f"TTS output: {text!r} ({len(audio)} bytes)")
            except Exception as exc:
                logger.debug(f"TTS failed: {exc}")
        else:
            logger.info(f"[TTS stub] {text}")
