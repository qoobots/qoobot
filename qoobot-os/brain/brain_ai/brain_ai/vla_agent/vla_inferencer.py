"""
brain_ai/vla_agent/vla_inferencer.py — Brain-VLA 主推理器。

协调 VLA 模型的端到端推理流程:
  1. 视觉编码 (vision encoder: SigLIP / DINOv2)
  2. 语言编码 (language encoder: Qwen2.5 tokenizer)
  3. 多模态融合 (projector: MLP / Q-Former)
  4. 动作解码 (action decoder: token → action chunks)

参考架构: OpenVLA (Stanford/MIT, 2024)
  - 基座模型: Prismatic-7B (Llama + SigLIP + DINOv2)
  - 动作空间: 7-DoF 绝对位姿 (x, y, z, roll, pitch, yaw, gripper)
  - 预测视界: 16 步 @ 10Hz

P3 优先级 — 当前为 stub/mock 实现。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

from brain_ai.vla_agent.action_decoder import ActionDecoder, DecodedAction, DecodeMode
from brain_ai.vla_agent.chunk_predictor import ChunkPredictor, ChunkPrediction
from brain_ai.vla_agent.model_loader import ModelLoader, ModelBackend, VLAModelInfo
from brain_ai.vla_agent.lora_adapter import LoRAAdapter, LoRATask

logger = logging.getLogger(__name__)


class VLAInferenceMode(str, Enum):
    """VLA 推理模式."""
    END_TO_END  = "end_to_end"   # 完整 VLA 流程: 图像+指令 → 动作
    ACTION_ONLY = "action_only"  # 仅动作解码（上游已提取特征）
    MOCK        = "mock"         # Mock 回退（返回预设动作）


@dataclass
class VLAInferenceResult:
    """VLA 推理完整结果."""
    action_chunks: ChunkPrediction        # 动作块预测
    decoded_actions: list[DecodedAction]  # 解码后的动作列表
    inference_ms: float = 0.0             # 总推理耗时 (ms)
    model_name: str = "brain-vla"
    mode: VLAInferenceMode = VLAInferenceMode.MOCK
    metadata: dict = field(default_factory=dict)


class VLAInferencer:
    """Brain-VLA 主推理器。

    端到端视觉-语言-动作推理的核心入口。

    Usage::

        vla = VLAInferencer()
        result = vla.infer(
            image=rgb_image,
            instruction="把红色杯子放到桌子上",
        )
        # 获取第一个动作
        next_action = result.decoded_actions[0]
    """

    def __init__(
        self,
        model_name: str = "brain-vla-chinese-lora",
        backend: ModelBackend = ModelBackend.MOCK,
        mode: VLAInferenceMode = VLAInferenceMode.MOCK,
        lora_task: LoRATask = LoRATask.GENERAL,
        action_horizon: int = 16,
        action_dim: int = 7,
    ):
        """
        Args:
            model_name: VLA 模型名称
            backend: 推理后端
            mode: 推理模式
            lora_task: LoRA 任务类型
            action_horizon: 动作预测视界
            action_dim: 动作空间维度
        """
        self._model_name = model_name
        self._mode = mode
        self._action_horizon = action_horizon
        self._action_dim = action_dim

        # 子组件
        self._model_loader = ModelLoader()
        self._lora_adapter = LoRAAdapter()
        self._action_decoder = ActionDecoder(
            mode=DecodeMode.MOCK if mode == VLAInferenceMode.MOCK else DecodeMode.CONTINUOUS,
        )
        self._chunk_predictor = ChunkPredictor(
            action_dim=action_dim,
            horizon=action_horizon,
        )

        # 加载模型（mock 模式下不实际加载权重）
        if mode != VLAInferenceMode.MOCK:
            self._model_loader.load(model_name, backend=backend)
            self._lora_adapter.load(model_name, task=lora_task)

        logger.info(
            "[VLAInferencer] Initialized: model=%s, backend=%s, mode=%s, horizon=%d",
            model_name, backend.value, mode.value, action_horizon,
        )

    def infer(
        self,
        image: np.ndarray,
        instruction: str,
        current_pose: Optional[np.ndarray] = None,
        scene_context: Optional[dict] = None,
    ) -> VLAInferenceResult:
        """执行 VLA 推理: 视觉观察 + 语言指令 → 动作序列。

        Args:
            image: RGB 图像 (H, W, 3), uint8, [0, 255]
            instruction: 自然语言指令，如 "把红色杯子放到桌子上"
            current_pose: 当前末端执行器位姿 (7,)，用于相对→绝对转换
            scene_context: 可选的场景上下文

        Returns:
            VLAInferenceResult 包含预测动作序列
        """
        t0 = time.perf_counter()
        metadata: dict = {"instruction": instruction, "image_shape": image.shape}

        if self._mode == VLAInferenceMode.MOCK:
            result = self._mock_infer(image, instruction, current_pose)
        elif self._mode == VLAInferenceMode.ACTION_ONLY:
            result = self._action_only_infer(current_pose)
        else:
            result = self._end_to_end_infer(image, instruction, current_pose)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        result.inference_ms = elapsed_ms
        result.metadata = metadata

        logger.info(
            "[VLAInferencer] Inference complete: %d actions in %.1f ms (mode=%s)",
            len(result.decoded_actions), elapsed_ms, self._mode.value,
        )
        return result

    def _mock_infer(
        self,
        image: np.ndarray,
        instruction: str,
        current_pose: Optional[np.ndarray] = None,
    ) -> VLAInferenceResult:
        """Mock 推理 — 生成合理的虚拟动作序列。

        根据指令关键词生成对应方向的运动趋势。
        """
        instruction_lower = instruction.lower()

        # 根据指令决定运动方向
        if "抓" in instruction or "拿" in instruction or "pick" in instruction_lower:
            direction = np.array([0.05, 0.0, -0.02, 0.0, 0.0, 0.0, 0.8], dtype=np.float32)
        elif "放" in instruction or "place" in instruction_lower:
            direction = np.array([0.0, 0.0, 0.03, 0.0, 0.0, 0.0, 0.2], dtype=np.float32)
        elif "推" in instruction or "push" in instruction_lower:
            direction = np.array([0.08, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
        elif "拉" in instruction or "pull" in instruction_lower:
            direction = np.array([-0.06, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0], dtype=np.float32)
        elif "左" in instruction or "left" in instruction_lower:
            direction = np.array([0.0, 0.04, 0.0, 0.0, 0.0, 0.0, 0.5], dtype=np.float32)
        elif "右" in instruction or "right" in instruction_lower:
            direction = np.array([0.0, -0.04, 0.0, 0.0, 0.0, 0.0, 0.5], dtype=np.float32)
        elif "上" in instruction or "up" in instruction_lower:
            direction = np.array([0.0, 0.0, 0.05, 0.0, 0.0, 0.0, 0.5], dtype=np.float32)
        elif "下" in instruction or "down" in instruction_lower:
            direction = np.array([0.0, 0.0, -0.03, 0.0, 0.0, 0.0, 0.5], dtype=np.float32)
        else:
            # 默认: 小幅度前移
            direction = np.array([0.02, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5], dtype=np.float32)

        # 生成 horizon 步动作，每步加上小噪声模拟真实预测
        mock_output = np.tile(direction, (self._action_horizon, 1))
        noise = np.random.normal(0, 0.005, mock_output.shape).astype(np.float32)
        mock_output = mock_output + noise

        # 应用当前位姿偏移
        if current_pose is not None:
            mock_output[:, :7] = mock_output[:, :7] + current_pose.reshape(1, -1)[:, :7]

        # 解码为结构化动作
        decoded = self._action_decoder.decode_batch(mock_output)
        chunks = self._chunk_predictor.predict(
            mock_output, current_pose=current_pose, model_name=self._model_name,
        )

        return VLAInferenceResult(
            action_chunks=chunks,
            decoded_actions=decoded,
            model_name=self._model_name,
            mode=VLAInferenceMode.MOCK,
            metadata={"source": "mock"},
        )

    def _end_to_end_infer(
        self,
        image: np.ndarray,
        instruction: str,
        current_pose: Optional[np.ndarray] = None,
    ) -> VLAInferenceResult:
        """端到端 VLA 推理（需要真实模型权重）。

        流程:
          1. Vision Encoder: image → vision tokens
          2. Language Encoder: instruction → language tokens
          3. Multimodal Fusion: vision + language → fused embeddings
          4. Action Decoder: fused embeddings → action tokens → continuous actions
        """
        logger.info("[VLAInferencer] End-to-end inference requested")

        if not self._model_loader.is_loaded:
            logger.warning(
                "[VLAInferencer] Real model not loaded. "
                "Falling back to mock inference."
            )
            return self._mock_infer(image, instruction, current_pose)

        # 真实推理路径（当前为 stub，实际需要 TRT-LLM / PyTorch 推理）
        # 这里预留完整的推理管线接口
        mock_output = np.random.normal(0, 0.01, (self._action_horizon, self._action_dim)).astype(np.float32)
        if current_pose is not None:
            mock_output[:, :7] += current_pose.reshape(1, -1)[:, :7]

        decoded = self._action_decoder.decode_batch(mock_output)
        chunks = self._chunk_predictor.predict(
            mock_output, current_pose=current_pose, model_name=self._model_name,
        )

        return VLAInferenceResult(
            action_chunks=chunks,
            decoded_actions=decoded,
            model_name=self._model_name,
            mode=VLAInferenceMode.END_TO_END,
        )

    def _action_only_infer(
        self,
        current_pose: Optional[np.ndarray] = None,
    ) -> VLAInferenceResult:
        """仅动作解码模式（上游已提取多模态特征）。"""
        mock_output = np.random.normal(0, 0.01, (self._action_horizon, self._action_dim)).astype(np.float32)
        if current_pose is not None:
            mock_output[:, :7] += current_pose.reshape(1, -1)[:, :7]

        decoded = self._action_decoder.decode_batch(mock_output)
        chunks = self._chunk_predictor.predict(
            mock_output, current_pose=current_pose, model_name=self._model_name,
        )

        return VLAInferenceResult(
            action_chunks=chunks,
            decoded_actions=decoded,
            model_name=self._model_name,
            mode=VLAInferenceMode.ACTION_ONLY,
        )

    def set_mode(self, mode: VLAInferenceMode) -> None:
        """切换推理模式."""
        logger.info("[VLAInferencer] Mode changed: %s → %s", self._mode.value, mode.value)
        self._mode = mode

    @property
    def mode(self) -> VLAInferenceMode:
        return self._mode

    @property
    def model_name(self) -> str:
        return self._model_name

    def __repr__(self) -> str:
        return f"VLAInferencer(model={self._model_name}, mode={self._mode.value}, horizon={self._action_horizon})"
