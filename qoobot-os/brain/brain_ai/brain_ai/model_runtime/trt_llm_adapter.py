"""
brain_ai/model_runtime/trt_llm_adapter.py — TensorRT-LLM backend adapter.

Wraps TensorRT-LLM's Python runtime (tensorrt_llm.runtime.GenerationSession)
for Qwen2.5-7B-Instruct running on Jetson Orin / A100.

If tensorrt_llm is not installed, is_available() returns False and the
RuntimeFactory automatically falls back to the next backend.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from brain_ai.model_runtime.runtime_factory import BackendType, BaseLLMBackend

logger = logging.getLogger(__name__)

# TensorRT-LLM model defaults (override via config dict or env)
_DEFAULT_ENGINE_DIR  = os.environ.get("TRT_ENGINE_DIR",  "/models/qwen2.5-7b-trt/")
_DEFAULT_TOKENIZER   = os.environ.get("TRT_TOKENIZER",   "Qwen/Qwen2.5-7B-Instruct")
_DEFAULT_MAX_BATCH   = int(os.environ.get("TRT_MAX_BATCH", "4"))


class TrtLLMAdapter(BaseLLMBackend):
    """
    TensorRT-LLM backend for Qwen2.5-7B.

    Install: pip install tensorrt-llm (NVIDIA developer index)
    Requires: CUDA-compatible GPU, TRT engine pre-built with trtllm-build.
    """

    backend_type = BackendType.TRT_LLM

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self._engine_dir  = cfg.get("engine_dir",  _DEFAULT_ENGINE_DIR)
        self._tokenizer   = cfg.get("tokenizer",   _DEFAULT_TOKENIZER)
        self._max_batch   = cfg.get("max_batch",   _DEFAULT_MAX_BATCH)
        self._session     = None
        self._tok         = None
        self._available   = False
        self._try_load()

    # ─── Init ──────────────────────────────────────────────────

    def _try_load(self) -> None:
        try:
            import tensorrt_llm  # noqa: F401
            from tensorrt_llm.runtime import ModelRunnerCpp
            from transformers import AutoTokenizer

            logger.info(f"Loading TRT-LLM engine from {self._engine_dir} …")
            self._tok = AutoTokenizer.from_pretrained(
                self._tokenizer, trust_remote_code=True
            )
            self._session = ModelRunnerCpp.from_dir(
                engine_dir=self._engine_dir,
                rank=0,
            )
            self._available = True
            logger.info("TRT-LLM backend ready.")
        except ImportError:
            logger.debug("tensorrt_llm not installed — TRT backend unavailable.")
        except FileNotFoundError:
            logger.debug(f"TRT engine not found at {self._engine_dir}.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"TRT-LLM init failed: {exc}")

    # ─── Interface ─────────────────────────────────────────────

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
            raise RuntimeError("TRT-LLM backend is not available.")

        import torch

        # Tokenize
        input_ids = self._tok.encode(prompt, return_tensors="pt")
        batch = [input_ids[0].tolist()]

        # Run inference
        outputs = self._session.generate(
            batch_input_ids=batch,
            max_new_tokens=max_tokens,
            temperature=temperature,
            end_id=self._tok.eos_token_id,
            pad_id=self._tok.pad_token_id,
        )

        output_ids = outputs["output_ids"][0][0].tolist()
        prompt_len  = len(batch[0])
        new_tokens  = output_ids[prompt_len:]
        text = self._tok.decode(new_tokens, skip_special_tokens=True)

        # Apply stop sequences
        if stop_sequences:
            for stop in stop_sequences:
                idx = text.find(stop)
                if idx != -1:
                    text = text[:idx]

        return text.strip()

    async def agenerate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        # TRT-LLM does not have native async; run sync in thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.generate(prompt, max_tokens, temperature, stop_sequences)
        )
