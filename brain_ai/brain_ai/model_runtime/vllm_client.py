"""
brain_ai/model_runtime/vllm_client.py — vLLM OpenAI-compatible REST client.

Connects to a running vLLM server (e.g. `vllm serve Qwen/Qwen2.5-7B-Instruct`)
via its OpenAI-compatible /v1/completions API.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from brain_ai.model_runtime.runtime_factory import BackendType, BaseLLMBackend

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
_DEFAULT_MODEL    = os.environ.get("VLLM_MODEL",    "Qwen/Qwen2.5-7B-Instruct")
_DEFAULT_TIMEOUT  = float(os.environ.get("VLLM_TIMEOUT", "30"))


class VllmClient(BaseLLMBackend):
    """
    vLLM client using OpenAI-compatible HTTP API.

    Start server:
        vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000 --dtype auto

    Config keys: base_url, model, timeout_sec
    """

    backend_type = BackendType.VLLM

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self._base_url   = cfg.get("base_url",    _DEFAULT_BASE_URL)
        self._model      = cfg.get("model",        _DEFAULT_MODEL)
        self._timeout    = cfg.get("timeout_sec",  _DEFAULT_TIMEOUT)
        self._client     = None
        self._available  = False
        self._try_connect()

    def _try_connect(self) -> None:
        try:
            import httpx  # type: ignore
            resp = httpx.get(f"{self._base_url}/models", timeout=3.0)
            if resp.status_code == 200:
                self._client   = httpx.Client(base_url=self._base_url, timeout=self._timeout)
                self._available = True
                logger.info(f"vLLM backend connected: {self._base_url}")
        except Exception as exc:  # noqa: BLE001
            logger.debug(f"vLLM not reachable at {self._base_url}: {exc}")

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
            raise RuntimeError("vLLM backend is not available.")

        payload = {
            "model": self._model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if stop_sequences:
            payload["stop"] = stop_sequences

        resp = self._client.post("/completions", json=payload)
        resp.raise_for_status()
        return resp.json()["choices"][0]["text"].strip()

    async def agenerate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        try:
            import httpx

            payload = {
                "model": self._model,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if stop_sequences:
                payload["stop"] = stop_sequences

            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                resp = await client.post("/completions", json=payload)
                resp.raise_for_status()
                return resp.json()["choices"][0]["text"].strip()
        except ImportError:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.generate(prompt, max_tokens, temperature, stop_sequences)
            )
