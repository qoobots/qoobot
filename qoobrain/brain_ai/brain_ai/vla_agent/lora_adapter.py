"""
brain_ai/vla_agent/lora_adapter.py — LoRA 适配器管理。

管理 Brain-VLA 的 LoRA (Low-Rank Adaptation) 微调适配器：
  - 中文指令微调适配器（brain-vla-chinese-lora）
  - 特定任务适配器（抓取/导航/操作）
  - 多适配器合并与切换

基于 PEFT (Parameter-Efficient Fine-Tuning) 库。

P3 优先级 — 当前为 stub/mock 实现。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LoRATask(str, Enum):
    """LoRA 适配器任务类型."""
    GENERAL      = "general"       # 通用中文指令
    PICK_PLACE   = "pick_place"    # 抓取与放置
    NAVIGATION   = "navigation"    # 导航
    MANIPULATION = "manipulation"  # 精细操作
    SOCIAL       = "social"        # 社交交互


@dataclass
class LoRAConfig:
    """LoRA 适配器配置."""
    task: LoRATask = LoRATask.GENERAL
    rank: int = 64                   # LoRA rank
    alpha: int = 128                 # LoRA alpha
    dropout: float = 0.05
    target_modules: list[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])
    weight_path: Optional[str] = None
    merged: bool = False             # 是否已合并到基座权重


class LoRAAdapter:
    """LoRA 微调适配器管理器。

    负责加载、切换、合并多个 LoRA 适配器。

    Usage::

        adapter = LoRAAdapter()
        adapter.load("brain-vla-chinese-lora", task=LoRATask.GENERAL)
        # 切换任务
        adapter.switch_to(LoRATask.PICK_PLACE)
    """

    def __init__(self, base_model_name: str = "openvla/openvla-7b"):
        """
        Args:
            base_model_name: 基座模型标识符（HuggingFace 模型 ID）
        """
        self._base_model = base_model_name
        self._active_config: Optional[LoRAConfig] = None
        self._loaded_adapters: dict[LoRATask, LoRAConfig] = {}
        logger.info("[LoRAAdapter] Initialized, base_model=%s", base_model_name)

    def load(
        self,
        adapter_name: str,
        task: LoRATask = LoRATask.GENERAL,
        config: Optional[LoRAConfig] = None,
    ) -> LoRAConfig:
        """加载 LoRA 适配器。

        Args:
            adapter_name: 适配器名称，如 "brain-vla-chinese-lora"
            task: 适配器对应的任务类型
            config: 可选的自定义 LoRA 配置

        Returns:
            加载的 LoRAConfig
        """
        logger.info("[LoRAAdapter] Loading adapter: %s (task=%s)", adapter_name, task.value)

        if config is None:
            config = LoRAConfig(
                task=task,
                weight_path=f"brain_models/vla/{adapter_name}",
            )

        # 检查本地权重是否存在
        if config.weight_path and Path(config.weight_path).exists():
            logger.info("[LoRAAdapter] Found local weights at %s", config.weight_path)
            config.merged = False
        else:
            logger.warning(
                "[LoRAAdapter] LoRA weights not found at %s. "
                "Using mock mode — no real adapter loaded.",
                config.weight_path,
            )

        self._loaded_adapters[task] = config
        self._active_config = config
        logger.info("[LoRAAdapter] Adapter loaded: %s (rank=%d, alpha=%d)",
                     task.value, config.rank, config.alpha)
        return config

    def switch_to(self, task: LoRATask) -> bool:
        """切换到指定任务的 LoRA 适配器。

        Args:
            task: 目标任务类型

        Returns:
            True 如果切换成功
        """
        if task not in self._loaded_adapters:
            logger.error("[LoRAAdapter] Adapter not loaded for task: %s", task.value)
            return False

        prev = self._active_config.task if self._active_config else None
        self._active_config = self._loaded_adapters[task]
        logger.info("[LoRAAdapter] Switched from %s to %s", prev, task.value)
        return True

    def merge_adapters(self, tasks: list[LoRATask]) -> bool:
        """合并多个 LoRA 适配器（多任务融合）。

        使用线性加权合并多个 LoRA 权重。

        Args:
            tasks: 要合并的任务列表

        Returns:
            True 如果合并成功
        """
        missing = [t for t in tasks if t not in self._loaded_adapters]
        if missing:
            logger.error("[LoRAAdapter] Cannot merge: missing adapters %s", missing)
            return False

        logger.info("[LoRAAdapter] Merging %d adapters: %s",
                     len(tasks), [t.value for t in tasks])
        # stub: 实际需要调用 PEFT merge_and_unload()
        merged_config = LoRAConfig(
            task=LoRATask.GENERAL,
            merged=True,
            metadata={"merged_from": [t.value for t in tasks]},
        )
        self._active_config = merged_config
        return True

    def unload_all(self) -> None:
        """卸载所有已加载的适配器."""
        count = len(self._loaded_adapters)
        self._loaded_adapters.clear()
        self._active_config = None
        logger.info("[LoRAAdapter] Unloaded %d adapters", count)

    @property
    def active_config(self) -> Optional[LoRAConfig]:
        """当前激活的 LoRA 配置."""
        return self._active_config

    @property
    def loaded_tasks(self) -> list[LoRATask]:
        """已加载的适配器任务列表."""
        return list(self._loaded_adapters.keys())

    def __repr__(self) -> str:
        active = self._active_config.task.value if self._active_config else "none"
        return f"LoRAAdapter(base={self._base_model}, active={active}, loaded={len(self._loaded_adapters)})"
