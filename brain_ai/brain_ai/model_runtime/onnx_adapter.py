"""
brain_ai/model_runtime/onnx_adapter.py — ONNX Runtime adapter for perception models.

Used for running YOLOv11, FoundationPose, depth estimation, etc.
Distinct from LLM backends — this is for CV/perception ONNX graphs.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

from brain_ai.model_runtime.runtime_factory import BackendType, BaseLLMBackend

logger = logging.getLogger(__name__)


class OnnxModel:
    """Wraps a single ONNX model for inference."""

    def __init__(self, model_path: str, providers: Optional[list[str]] = None) -> None:
        self._path      = model_path
        self._session   = None
        self._providers = providers or ["CUDAExecutionProvider", "CPUExecutionProvider"]
        self._input_names: list[str] = []
        self._output_names: list[str] = []
        self._load()

    def _load(self) -> None:
        try:
            import onnxruntime as ort  # type: ignore

            opts = ort.SessionOptions()
            opts.log_severity_level = 3   # suppress verbose logs
            self._session = ort.InferenceSession(
                self._path,
                sess_options=opts,
                providers=self._providers,
            )
            self._input_names  = [i.name for i in self._session.get_inputs()]
            self._output_names = [o.name for o in self._session.get_outputs()]
            logger.info(f"ONNX model loaded: {os.path.basename(self._path)}")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"ONNX model load failed ({self._path}): {exc}")

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    def run(self, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        if self._session is None:
            raise RuntimeError(f"ONNX model not loaded: {self._path}")
        outputs = self._session.run(self._output_names, inputs)
        return dict(zip(self._output_names, outputs))

    def infer(self, *args: np.ndarray) -> list[np.ndarray]:
        """Convenience: positional inputs in order."""
        inputs = dict(zip(self._input_names, args))
        result = self.run(inputs)
        return [result[k] for k in self._output_names]


class OnnxAdapter(BaseLLMBackend):
    """
    Registry of ONNX models for the perception pipeline.

    This class does NOT implement LLM text generation —
    it provides load/get_model() for YOLOv11, FoundationPose, depth, etc.
    """

    backend_type = BackendType.ONNX

    def __init__(self, config: Optional[dict] = None) -> None:
        cfg = config or {}
        self._model_dir = cfg.get("model_dir", "/models/onnx/")
        self._models: dict[str, OnnxModel] = {}
        self._providers = cfg.get(
            "providers", ["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self._available = self._check_ort()

    @staticmethod
    def _check_ort() -> bool:
        try:
            import onnxruntime  # noqa: F401
            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        return self._available

    def load_model(self, name: str, path: Optional[str] = None) -> OnnxModel:
        """Load a named ONNX model. Uses model_dir/{name}.onnx by default."""
        if name in self._models:
            return self._models[name]
        model_path = path or os.path.join(self._model_dir, f"{name}.onnx")
        model = OnnxModel(model_path, providers=self._providers)
        self._models[name] = model
        return model

    def get_model(self, name: str) -> Optional[OnnxModel]:
        return self._models.get(name)

    # ── BaseLLMBackend stubs (not used for ONNX) ─────────────

    def generate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError("OnnxAdapter is for perception models, not text generation.")

    async def agenerate(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError
