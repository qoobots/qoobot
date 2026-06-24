"""
brain_ai/model_runtime/llama_cpp_adapter.py — llama.cpp CPU fallback backend.

Wraps llama-cpp-python to run Qwen2.5-1.5B-Instruct-GGUF on CPU.
Requires: pip install llama-cpp-python
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from brain_ai.model_runtime.runtime_factory import BackendType, BaseLLMBackend

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_PATH = os.environ.get(
    "LLAMA_CPP_MODEL",
    "/models/qwen2.5-1.5b-instruct-q4_k_m.gguf",
)
_DEFAULT_N_CTX   = int(os.environ.get("LLAMA_N_CTX",   "4096"))
_DEFAULT_N_THREADS = int(os.environ.get("LLAMA_THREADS", "8"))


class LlamaCppAdapter(BaseLLMBackend):
    """
    llama.cpp CPU backend for Qwen2.5-1.5B-Instruct (GGUF format).

    Used when no GPU is available. Slower but always works on Jetson CPU
    or any Linux host.
    """

    backend_type = BackendType.LLAMA_CPP

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self._model_path = cfg.get("model_path", _DEFAULT_MODEL_PATH)
        self._n_ctx      = cfg.get("n_ctx",       _DEFAULT_N_CTX)
        self._n_threads  = cfg.get("n_threads",   _DEFAULT_N_THREADS)
        self._llm        = None
        self._available  = False
        self._try_load()

    def _try_load(self) -> None:
        if not os.path.isfile(self._model_path):
            logger.debug(f"llama.cpp model not found: {self._model_path}")
            return
        try:
            from llama_cpp import Llama  # type: ignore

            logger.info(f"Loading llama.cpp model from {self._model_path} …")
            self._llm = Llama(
                model_path=self._model_path,
                n_ctx=self._n_ctx,
                n_threads=self._n_threads,
                verbose=False,
            )
            self._available = True
            logger.info("llama.cpp backend ready.")
        except ImportError:
            logger.debug("llama-cpp-python not installed — llama.cpp backend unavailable.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"llama.cpp init failed: {exc}")

    def is_available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        if not self._available:
            raise RuntimeError("llama.cpp backend is not available.")

        result = self._llm(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop_sequences or [],
            echo=False,
        )
        return result["choices"][0]["text"].strip()

    async def agenerate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.generate(prompt, max_tokens, temperature, stop_sequences)
        )
