"""
brain_ai/llm_agent/ds3_cloud_client.py — DeepSeek-V3 cloud API client.

Used as the always-available cloud fallback backend when local LLM is unavailable.
API is OpenAI-compatible (https://api.deepseek.com/v1).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from brain_ai.model_runtime.runtime_factory import BackendType, BaseLLMBackend

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
_DEFAULT_MODEL    = "deepseek-chat"    # DeepSeek-V3
_DEFAULT_TIMEOUT  = 60.0


class DS3CloudClient(BaseLLMBackend):
    """
    DeepSeek-V3 cloud API client (OpenAI-compatible).

    Set DS3_API_KEY env var before use:
        export DS3_API_KEY="sk-..."

    Config keys: api_key, base_url, model, timeout_sec
    """

    backend_type = BackendType.DS3_CLOUD

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self._api_key  = cfg.get("api_key",    os.environ.get("DS3_API_KEY", ""))
        self._base_url = cfg.get("base_url",   _DEFAULT_BASE_URL)
        self._model    = cfg.get("model",       _DEFAULT_MODEL)
        self._timeout  = cfg.get("timeout_sec", _DEFAULT_TIMEOUT)

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type":  "application/json",
        }

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        if not self.is_available():
            raise RuntimeError("DS3_API_KEY is not set. Cannot call DeepSeek-V3 API.")

        try:
            import httpx  # type: ignore
        except ImportError:
            raise RuntimeError("httpx required: pip install httpx")

        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if stop_sequences:
            payload["stop"] = stop_sequences

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()

    async def agenerate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        if not self.is_available():
            raise RuntimeError("DS3_API_KEY is not set.")

        try:
            import httpx

            payload = {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            }
            if stop_sequences:
                payload["stop"] = stop_sequences

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()

            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

        except ImportError:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, lambda: self.generate(prompt, max_tokens, temperature, stop_sequences)
            )
