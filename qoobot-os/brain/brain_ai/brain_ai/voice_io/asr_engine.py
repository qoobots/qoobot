"""
brain_ai/voice_io/asr_engine.py — Automatic Speech Recognition engine wrapper.

Supports:
  1. FunASR (local, Paraformer-zh) — default on-device
  2. Whisper (via openai-whisper or faster-whisper)
  3. Cloud ASR API (fallback)
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.environ.get("ASR_MODEL", "paraformer-zh")
_DEFAULT_DEVICE = os.environ.get("ASR_DEVICE", "cpu")


class ASRResult:
    def __init__(self, text: str, confidence: float = 1.0, language: str = "zh") -> None:
        self.text       = text
        self.confidence = confidence
        self.language   = language

    def __repr__(self) -> str:
        return f"ASRResult(text={self.text!r}, confidence={self.confidence:.2f})"


class ASREngine:
    """
    ASR engine wrapper. Tries FunASR → Whisper → stub in order.

    Usage:
        asr = ASREngine()
        result = asr.transcribe(audio_bytes, sample_rate=16000)
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL, device: str = _DEFAULT_DEVICE) -> None:
        self._model_name = model_name
        self._device     = device
        self._model      = None
        self._backend    = "stub"
        self._try_load()

    @staticmethod
    def _resolve_whisper_path() -> Optional[str]:
        """Resolve whisper-large-v3-ct2 model directory from registry.

        Returns:
            Absolute path to the CTranslate2 model directory, or None if not found.
        """
        try:
            from brain_models.model_path_resolver import ModelResolver
            resolver = ModelResolver()
            model_dir = resolver.resolve("whisper-large-v3-ct2")
            if model_dir:
                return str(model_dir.parent)  # model_dir = .../model.bin → parent is the dir
            return None
        except Exception:
            return None

    def _try_load(self) -> None:
        # Try FunASR first
        try:
            from funasr import AutoModel  # type: ignore
            self._model   = AutoModel(model=self._model_name, device=self._device)
            self._backend = "funasr"
            logger.info(f"ASR: FunASR loaded ({self._model_name})")
            return
        except ImportError:
            pass
        except Exception as exc:
            logger.debug(f"FunASR load failed: {exc}")

        # Try faster-whisper (prefer whisper-large-v3-ct2 if available in registry)
        try:
            from faster_whisper import WhisperModel  # type: ignore
            # Try to resolve whisper-large-v3-ct2 from model registry
            model_path = self._resolve_whisper_path()
            if model_path and os.path.isdir(model_path):
                self._model = WhisperModel(model_path, device=self._device, compute_type="int8")
                self._backend = "whisper"
                logger.info(f"ASR: faster-whisper loaded (whisper-large-v3-ct2 @ {model_path})")
            else:
                # Fallback to small model
                self._model = WhisperModel("small", device=self._device, compute_type="int8")
                self._backend = "whisper"
                logger.info("ASR: faster-whisper loaded (small) — large-v3 not found in registry")
            return
        except ImportError:
            pass
        except Exception as exc:
            logger.debug(f"Whisper load failed: {exc}")

        logger.warning("ASR: No ASR backend available — stub mode (returns empty string).")

    @property
    def is_available(self) -> bool:
        return self._backend != "stub"

    def transcribe(self, audio_bytes: bytes, sample_rate: int = 16000) -> ASRResult:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: Raw PCM audio (16-bit, mono)
            sample_rate: Sample rate in Hz

        Returns:
            ASRResult with text and confidence
        """
        if self._backend == "funasr":
            return self._transcribe_funasr(audio_bytes, sample_rate)
        elif self._backend == "whisper":
            return self._transcribe_whisper(audio_bytes, sample_rate)
        else:
            logger.warning("ASR stub: returning empty string.")
            return ASRResult(text="", confidence=0.0)

    def _transcribe_funasr(self, audio_bytes: bytes, sample_rate: int) -> ASRResult:
        import numpy as np
        audio = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        result = self._model.generate(input=audio, batch_size=1)
        text = result[0].get("text", "") if result else ""
        return ASRResult(text=text, language="zh")

    def _transcribe_whisper(self, audio_bytes: bytes, sample_rate: int) -> ASRResult:
        import tempfile, wave, os
        import numpy as np

        # Write to temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_bytes)

        try:
            segments, info = self._model.transcribe(tmp_path, language="zh")
            text = " ".join(s.text for s in segments).strip()
            return ASRResult(text=text, language=info.language)
        finally:
            os.unlink(tmp_path)
