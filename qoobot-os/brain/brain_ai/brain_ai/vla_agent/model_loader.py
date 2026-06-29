"""
brain_ai/vla_agent/model_loader.py — VLA 模型加载/卸载/热切换。

管理 Brain-VLA 模型的生命周期：
  - 从本地缓存或 HuggingFace Hub 加载 OpenVLA-7B 权重
  - 支持 TensorRT-LLM 编译加速
  - 热切换不同 LoRA 适配器（无需重载基座模型）

P3 优先级 — 当前为 stub/mock 实现。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ModelBackend(str, Enum):
    """VLA 模型推理后端."""
    TRT_LLM   = "trt_llm"       # TensorRT-LLM（Jetson Orin 最优）
    PYTORCH   = "pytorch"       # 原生 PyTorch（开发/调试）
    ONNX      = "onnx"          # ONNX Runtime（跨平台）
    MOCK      = "mock"          # Mock 回退（无 GPU 环境）


@dataclass
class VLAModelInfo:
    """VLA 模型元信息."""
    name: str = "brain-vla-chinese-lora"
    base_model: str = "openvla/openvla-7b"
    lora_path: Optional[str] = None
    backend: ModelBackend = ModelBackend.MOCK
    device: str = "cuda:0"
    max_batch_size: int = 1
    action_dim: int = 7            # 末端执行器 6DoF + 夹爪
    action_horizon: int = 16       # 预测未来 16 步动作
    chunk_size: int = 16
    metadata: dict = field(default_factory=dict)


class ModelLoader:
    """VLA 模型加载器。

    支持加载/卸载/热切换 Brain-VLA 模型权重。

    Usage::

        loader = ModelLoader()
        model_info = loader.load("brain-vla-chinese-lora")
        # ... 推理 ...
        loader.unload()
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Args:
            cache_dir: 模型缓存目录，默认使用 brain_models/vla/
        """
        self._cache_dir = Path(cache_dir) if cache_dir else Path("brain_models/vla")
        self._loaded_model: Optional[VLAModelInfo] = None
        self._is_loaded = False
        logger.info("[ModelLoader] Initialized, cache_dir=%s", self._cache_dir)

    def load(self, model_name: str, backend: ModelBackend = ModelBackend.MOCK) -> VLAModelInfo:
        """加载指定 VLA 模型。

        加载优先级:
          1. 本地缓存 (brain_models/vla/)
          2. HuggingFace Hub (openvla/openvla-7b)
          3. Mock 回退

        Args:
            model_name: 模型名称，如 "brain-vla-chinese-lora"
            backend: 推理后端

        Returns:
            VLAModelInfo 模型元信息
        """
        logger.info("[ModelLoader] Loading model: %s (backend=%s)", model_name, backend.value)

        model_path = self._cache_dir / model_name
        if model_path.exists() and backend != ModelBackend.MOCK:
            logger.info("[ModelLoader] Found cached model at %s", model_path)
            info = VLAModelInfo(
                name=model_name,
                backend=backend,
                lora_path=str(model_path),
            )
        elif backend == ModelBackend.MOCK:
            logger.info("[ModelLoader] Using mock backend (no real weights loaded)")
            info = VLAModelInfo(
                name=model_name,
                backend=ModelBackend.MOCK,
                metadata={"source": "mock", "note": "stub for dev/testing"},
            )
        else:
            logger.warning(
                "[ModelLoader] Model not found locally, would download from HuggingFace. "
                "Falling back to mock."
            )
            info = VLAModelInfo(
                name=model_name,
                backend=ModelBackend.MOCK,
                metadata={"source": "mock", "note": "real weights not downloaded"},
            )

        self._loaded_model = info
        self._is_loaded = True
        logger.info("[ModelLoader] Model loaded: %s", info.name)
        return info

    def unload(self) -> None:
        """卸载当前模型，释放 GPU/CPU 内存."""
        if self._loaded_model:
            logger.info("[ModelLoader] Unloading model: %s", self._loaded_model.name)
            self._loaded_model = None
            self._is_loaded = False

    def hot_swap_lora(self, lora_path: str) -> bool:
        """热切换 LoRA 适配器（无需重载基座模型）。

        Args:
            lora_path: 新的 LoRA 权重路径

        Returns:
            True 如果切换成功
        """
        if not self._is_loaded:
            logger.error("[ModelLoader] Cannot hot-swap: no model loaded")
            return False

        logger.info("[ModelLoader] Hot-swapping LoRA to: %s", lora_path)
        if self._loaded_model:
            self._loaded_model.lora_path = lora_path
        return True

    @property
    def is_loaded(self) -> bool:
        """模型是否已加载."""
        return self._is_loaded

    @property
    def model_info(self) -> Optional[VLAModelInfo]:
        """当前加载的模型信息."""
        return self._loaded_model

    def __repr__(self) -> str:
        status = f"loaded={self._is_loaded}, model={self._loaded_model.name}" if self._loaded_model else "idle"
        return f"ModelLoader({status})"
