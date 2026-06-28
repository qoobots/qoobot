"""
brain_ai/vla_agent/action_decoder.py — VLA 输出 → Action Chunk 解码。

将 VLA 模型输出的离散 token 序列解码为连续动作空间的动作块。
支持两种解码模式:
  - Token → Action: 从模型 logits 直接映射到动作空间
  - Discretized → Continuous: 将离散化动作 bin 恢复为连续值

参考: OpenVLA 的 action tokenizer 设计。

P3 优先级 — 当前为 stub/mock 实现。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class DecodeMode(str, Enum):
    """动作解码模式."""
    TOKEN_TO_ACTION = "token_to_action"           # 从离散 token 解码
    CONTINUOUS      = "continuous"                 # 连续回归（不需要离散化）
    MOCK            = "mock"                       # Mock 回退


@dataclass
class ActionSpace:
    """动作空间定义（归一化边界）."""
    pos_min: np.ndarray = field(default_factory=lambda: np.array([-0.5, -0.5, 0.0], dtype=np.float32))
    pos_max: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.5, 0.8], dtype=np.float32))
    rot_min: np.ndarray = field(default_factory=lambda: np.array([-3.14, -3.14, -3.14], dtype=np.float32))
    rot_max: np.ndarray = field(default_factory=lambda: np.array([3.14, 3.14, 3.14], dtype=np.float32))
    gripper_min: float = 0.0
    gripper_max: float = 1.0
    num_bins: int = 256   # 每个维度的离散化 bin 数量


@dataclass
class DecodedAction:
    """解码后的单个动作."""
    position: np.ndarray   # (3,) x, y, z (米)
    rotation: np.ndarray   # (3,) roll, pitch, yaw (弧度)
    gripper: float         # [0, 1]
    confidence: float = 1.0

    def as_array(self) -> np.ndarray:
        """返回 (7,) numpy 数组."""
        return np.concatenate([self.position, self.rotation, [self.gripper]]).astype(np.float32)

    def as_dict(self) -> dict:
        return {
            "position": self.position.tolist(),
            "rotation": self.rotation.tolist(),
            "gripper": self.gripper,
            "confidence": self.confidence,
        }


class ActionDecoder:
    """VLA 动作解码器。

    将模型输出的 token/logits 解码为连续动作空间的动作。

    Usage::

        decoder = ActionDecoder()
        action = decoder.decode(model_output_logits)
        # 或从 token 序列解码
        actions = decoder.decode_tokens(token_sequence)
    """

    def __init__(
        self,
        action_space: Optional[ActionSpace] = None,
        mode: DecodeMode = DecodeMode.MOCK,
    ):
        """
        Args:
            action_space: 动作空间定义（归一化边界）
            mode: 解码模式
        """
        self._action_space = action_space or ActionSpace()
        self._mode = mode
        self._bin_widths = (
            (self._action_space.pos_max - self._action_space.pos_min) /
            (self._action_space.num_bins - 1)
        )
        self._rot_bin_widths = (
            (self._action_space.rot_max - self._action_space.rot_min) /
            (self._action_space.num_bins - 1)
        )
        logger.info("[ActionDecoder] Initialized: mode=%s, bins=%d", mode.value, self._action_space.num_bins)

    def decode(self, model_output: np.ndarray) -> DecodedAction:
        """从模型连续输出解码为动作。

        Args:
            model_output: (7,) 或 (1, 7) 形状的归一化输出 [0, 1]

        Returns:
            DecodedAction 反归一化后的动作
        """
        arr = model_output.flatten()[:7]

        if self._mode == DecodeMode.MOCK:
            # Mock: 直接使用归一化值作为去归一化结果（模拟）
            position = arr[:3].astype(np.float32)
            rotation = arr[3:6].astype(np.float32)
            gripper = float(np.clip(arr[6], 0.0, 1.0))
        else:
            # 真实解码: 从 [0, 1] 反归一化到物理范围
            position = (
                arr[:3] * (self._action_space.pos_max - self._action_space.pos_min)
                + self._action_space.pos_min
            ).astype(np.float32)
            rotation = (
                arr[3:6] * (self._action_space.rot_max - self._action_space.rot_min)
                + self._action_space.rot_min
            ).astype(np.float32)
            gripper = float(np.clip(arr[6], 0.0, 1.0))

        action = DecodedAction(
            position=position,
            rotation=rotation,
            gripper=gripper,
            confidence=0.9,
        )
        logger.debug("[ActionDecoder] Decoded action: pos=%s, rot=%s, grip=%.2f",
                      position, rotation, gripper)
        return action

    def decode_tokens(self, token_ids: list[int]) -> list[DecodedAction]:
        """从离散 token 序列解码为动作序列。

        每个动作维度用 num_bins 个 token 表示。
        7 维动作 × 256 bins = 需要 7 个 token（每个 token 值在 [0, 255]）。

        Args:
            token_ids: 离散化 token ID 列表

        Returns:
            解码后的动作列表
        """
        n_actions = len(token_ids) // 7
        actions = []

        for i in range(n_actions):
            chunk = token_ids[i * 7:(i + 1) * 7]

            # 从 bin index 恢复到归一化值 [0, 1]
            norm = np.array(chunk, dtype=np.float32) / (self._action_space.num_bins - 1)

            # 反归一化
            pos = norm[:3] * (self._action_space.pos_max - self._action_space.pos_min) + self._action_space.pos_min
            rot = norm[3:6] * (self._action_space.rot_max - self._action_space.rot_min) + self._action_space.rot_min
            grip = float(norm[6])

            actions.append(DecodedAction(
                position=pos.astype(np.float32),
                rotation=rot.astype(np.float32),
                gripper=grip,
            ))

        logger.info("[ActionDecoder] Decoded %d actions from %d tokens", n_actions, len(token_ids))
        return actions

    def encode_action(self, action: DecodedAction) -> list[int]:
        """将连续动作编码为离散 token 序列（用于训练标签）。

        Args:
            action: 连续动作

        Returns:
            离散 token ID 列表（7 个 token）
        """
        full = action.as_array()

        # 归一化到 [0, 1]
        norm_pos = (full[:3] - self._action_space.pos_min) / (self._action_space.pos_max - self._action_space.pos_min)
        norm_rot = (full[3:6] - self._action_space.rot_min) / (self._action_space.rot_max - self._action_space.rot_min)
        norm_grip = np.clip(full[6], 0.0, 1.0)

        norm = np.concatenate([norm_pos, norm_rot, [norm_grip]])

        # 离散化
        token_ids = np.round(norm * (self._action_space.num_bins - 1)).astype(int).tolist()
        return token_ids

    def decode_batch(self, model_outputs: np.ndarray) -> list[DecodedAction]:
        """批量解码。

        Args:
            model_outputs: (batch, 7) 形状

        Returns:
            解码后的动作列表
        """
        return [self.decode(model_outputs[i]) for i in range(model_outputs.shape[0])]

    @property
    def mode(self) -> DecodeMode:
        return self._mode

    def set_mode(self, mode: DecodeMode) -> None:
        logger.info("[ActionDecoder] Mode changed: %s → %s", self._mode.value, mode.value)
        self._mode = mode

    def __repr__(self) -> str:
        return f"ActionDecoder(mode={self._mode.value}, bins={self._action_space.num_bins})"
