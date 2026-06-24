"""
brain_ai/voice_io/tts_engine.py — Text-To-Speech engine wrapper.

Supports: CosyVoice (local) → edge-tts (cloud) → pyttsx3 (stub).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TTSEngine:
    """TTS engine: CosyVoice → edge-tts → pyttsx3 fallback."""

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural") -> None:
        self._voice   = voice
        self._backend = "stub"
        self._model   = None
        self._try_load()

    def _try_load(self) -> None:
        try:
            import edge_tts  # type: ignore
            self._backend = "edge_tts"
            logger.info("TTS: edge-tts loaded.")
            return
        except ImportError:
            pass
        try:
            import pyttsx3  # type: ignore
            self._model   = pyttsx3.init()
            self._backend = "pyttsx3"
            logger.info("TTS: pyttsx3 loaded.")
        except Exception:
            logger.warning("TTS: stub mode (no audio output).")

    @property
    def is_available(self) -> bool:
        return self._backend != "stub"

    def synthesize(self, text: str, output_path: Optional[str] = None) -> bytes:
        """
        Synthesize text to speech.
        Returns raw MP3/WAV bytes, and optionally saves to output_path.
        """
        if self._backend == "edge_tts":
            return asyncio.get_event_loop().run_until_complete(
                self._synthesize_edge(text, output_path)
            )
        elif self._backend == "pyttsx3":
            return self._synthesize_pyttsx3(text, output_path)
        else:
            logger.warning(f"TTS stub: would say: {text!r}")
            return b""

    async def asynthesize(self, text: str, output_path: Optional[str] = None) -> bytes:
        if self._backend == "edge_tts":
            return await self._synthesize_edge(text, output_path)
        return self.synthesize(text, output_path)

    async def _synthesize_edge(self, text: str, output_path: Optional[str]) -> bytes:
        import edge_tts, io
        comm = edge_tts.Communicate(text, self._voice)
        buf = io.BytesIO()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        data = buf.getvalue()
        if output_path:
            with open(output_path, "wb") as f:
                f.write(data)
        return data

    def _synthesize_pyttsx3(self, text: str, output_path: Optional[str]) -> bytes:
        import tempfile, os
        tmp = output_path or tempfile.mktemp(suffix=".wav")
        self._model.save_to_file(text, tmp)
        self._model.runAndWait()
        if os.path.isfile(tmp):
            with open(tmp, "rb") as f:
                data = f.read()
            if not output_path:
                os.unlink(tmp)
            return data
        return b""
