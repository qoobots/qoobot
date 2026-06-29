"""
brain_ai/voice_io/audio_stream.py — Microphone capture and audio streaming.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_DEFAULT_SAMPLE_RATE  = 16000
_DEFAULT_CHUNK_SIZE   = 1024
_DEFAULT_VAD_SILENCE  = 0.8   # seconds of silence to detect end of utterance


class AudioStream:
    """
    Captures audio from the microphone in a background thread.
    Supports VAD (Voice Activity Detection) for automatic segmentation.
    """

    def __init__(
        self,
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
        chunk_size:  int = _DEFAULT_CHUNK_SIZE,
        vad_silence_sec: float = _DEFAULT_VAD_SILENCE,
    ) -> None:
        self._sample_rate    = sample_rate
        self._chunk_size     = chunk_size
        self._vad_silence    = vad_silence_sec
        self._audio_queue: queue.Queue[bytes] = queue.Queue()
        self._running        = False
        self._thread: Optional[threading.Thread] = None
        self._stream         = None  # PyAudio stream

    def start(self, callback: Optional[Callable[[bytes], None]] = None) -> None:
        """Start capturing audio. If callback is given, call it for each chunk."""
        try:
            import pyaudio  # type: ignore
            pa = pyaudio.PyAudio()
            self._stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self._sample_rate,
                input=True,
                frames_per_buffer=self._chunk_size,
            )
            self._running = True

            def _capture():
                while self._running:
                    try:
                        data = self._stream.read(self._chunk_size, exception_on_overflow=False)
                        self._audio_queue.put(data)
                        if callback:
                            callback(data)
                    except Exception:
                        break

            self._thread = threading.Thread(target=_capture, daemon=True)
            self._thread.start()
            logger.info("AudioStream started.")
        except ImportError:
            logger.warning("pyaudio not installed — AudioStream unavailable.")
        except Exception as exc:
            logger.warning(f"AudioStream start failed: {exc}")

    def stop(self) -> None:
        self._running = False
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)

    def read_utterance(self, timeout_sec: float = 10.0) -> bytes:
        """
        Block until a complete utterance is captured (VAD-based).
        Returns concatenated PCM audio bytes.
        """
        import time
        frames: list[bytes] = []
        silent_chunks = 0
        chunks_per_sec = self._sample_rate // self._chunk_size
        silent_threshold = int(self._vad_silence * chunks_per_sec)

        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            try:
                chunk = self._audio_queue.get(timeout=0.1)
                frames.append(chunk)
                # Simple energy-based VAD
                energy = sum(abs(b - 128) for b in chunk) / len(chunk)
                if energy < 5:
                    silent_chunks += 1
                    if silent_chunks > silent_threshold and frames:
                        break
                else:
                    silent_chunks = 0
            except queue.Empty:
                continue
        return b"".join(frames)
