"""
brain_ai/model_runtime/runtime_factory.py — LLM backend factory.

Selection priority:
  1. TensorRT-LLM  (Jetson Orin GPU, fastest)
  2. vLLM          (x86 server GPU)
  3. llama.cpp     (CPU fallback)
  4. DeepSeek-V3   (cloud API, always available)
"""
from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class BackendType(str, Enum):
    TRT_LLM   = "trt_llm"
    VLLM      = "vllm"
    LLAMA_CPP = "llama_cpp"
    DS3_CLOUD = "ds3_cloud"
    ONNX      = "onnx"


class BaseLLMBackend:
    """Abstract base class for all LLM backends."""

    backend_type: BackendType = BackendType.DS3_CLOUD

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        raise NotImplementedError

    async def agenerate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.1,
        stop_sequences: Optional[list[str]] = None,
    ) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        """Health check — return True if this backend can serve requests."""
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(type={self.backend_type.value})"


class RuntimeFactory:
    """
    Factory that creates the best available LLM backend.

    Usage:
        factory = RuntimeFactory(config)
        llm = factory.get_backend()  # auto-selects best
        response = llm.generate("Pick up the red cup.")
    """

    _priority_order = [
        BackendType.TRT_LLM,
        BackendType.VLLM,
        BackendType.LLAMA_CPP,
        BackendType.DS3_CLOUD,
    ]

    def __init__(self, config: Optional[dict] = None) -> None:
        self._config = config or {}
        self._cache: dict[BackendType, BaseLLMBackend] = {}

    def _build(self, backend_type: BackendType) -> BaseLLMBackend:
        """Lazily instantiate a backend."""
        if backend_type in self._cache:
            return self._cache[backend_type]

        instance: BaseLLMBackend

        if backend_type == BackendType.TRT_LLM:
            from brain_ai.model_runtime.trt_llm_adapter import TrtLLMAdapter
            instance = TrtLLMAdapter(self._config.get("trt_llm", {}))
        elif backend_type == BackendType.VLLM:
            from brain_ai.model_runtime.vllm_client import VllmClient
            instance = VllmClient(self._config.get("vllm", {}))
        elif backend_type == BackendType.LLAMA_CPP:
            from brain_ai.model_runtime.llama_cpp_adapter import LlamaCppAdapter
            instance = LlamaCppAdapter(self._config.get("llama_cpp", {}))
        elif backend_type == BackendType.DS3_CLOUD:
            from brain_ai.model_runtime.ds3_cloud_client import DS3CloudClient  # noqa (lives in llm_agent)
            instance = DS3CloudClient(self._config.get("ds3_cloud", {}))
        elif backend_type == BackendType.ONNX:
            from brain_ai.model_runtime.onnx_adapter import OnnxAdapter
            instance = OnnxAdapter(self._config.get("onnx", {}))
        else:
            raise ValueError(f"Unknown backend: {backend_type}")

        self._cache[backend_type] = instance
        return instance

    def get_backend(self, prefer: Optional[BackendType] = None) -> BaseLLMBackend:
        """
        Return the best available backend.
        If *prefer* is given, try that first.
        Falls back through priority order automatically.
        """
        order = ([prefer] + self._priority_order) if prefer else self._priority_order

        for btype in order:
            try:
                backend = self._build(btype)
                if backend.is_available():
                    logger.info(f"Using LLM backend: {backend}")
                    return backend
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"Backend {btype.value} not available: {exc}")

        raise RuntimeError(
            "No LLM backend is available. "
            "Check model paths, GPU drivers, and DS3_API_KEY."
        )

    def get_onnx_backend(self) -> BaseLLMBackend:
        """Dedicated getter for ONNX inference (perception models)."""
        return self._build(BackendType.ONNX)
