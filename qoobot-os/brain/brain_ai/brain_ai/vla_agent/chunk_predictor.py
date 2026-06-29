"""
brain_ai/vla_agent/chunk_predictor.py — 动作块预测器（类 π₀ 架构）。

实现动作分块预测（Action Chunking）：
  - 将 VLA 模型输出解码为未来 N 步动作序列
  - 支持时间平滑和动作插值
  - 动作空间: 末端执行器 6DoF (x, y, z, roll, pitch, yaw) + 夹爪开合

参考架构: π₀ (Physical Intelligence) 和 ACT (Action Chunking Transformer)。

P3 优先级 — 当前为 stub/mock 实现。
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ActionChunk:
    """单个动作块 — 未来一个时间步的末端执行器目标。

    动作空间: 绝对笛卡尔位姿 (x, y, z, roll, pitch, yaw) + 夹爪状态。
    位姿单位: 米 (m), 弧度 (rad)。
    """
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    gripper: float = 0.0   # 0.0 = 闭合, 1.0 = 完全张开
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0

    def as_array(self) -> np.ndarray:
        """返回 (7,) numpy 数组."""
        return np.array([
            self.x, self.y, self.z,
            self.roll, self.pitch, self.yaw,
            self.gripper,
        ], dtype=np.float32)

    @classmethod
    def from_array(cls, arr: np.ndarray, confidence: float = 1.0) -> "ActionChunk":
        """从 (7,) 数组构造."""
        arr = arr.flatten()
        return cls(
            x=float(arr[0]), y=float(arr[1]), z=float(arr[2]),
            roll=float(arr[3]), pitch=float(arr[4]), yaw=float(arr[5]),
            gripper=float(arr[6]),
            confidence=confidence,
        )


@dataclass
class ChunkPrediction:
    """一次推理输出的完整动作预测序列."""
    chunks: list[ActionChunk]      # 未来 N 步动作
    horizon: int = 16              # 预测视界长度
    inference_ms: float = 0.0      # 推理耗时 (ms)
    model_name: str = "brain-vla"


class ChunkPredictor:
    """动作块预测器。

    将 VLA 模型原始输出解码为结构化的动作序列，
    支持时间平滑和置信度过滤。

    Usage::

        predictor = ChunkPredictor(action_dim=7, horizon=16)
        prediction = predictor.predict(raw_tokens, current_pose)
        # 取第一个动作执行
        next_action = prediction.chunks[0]
    """

    def __init__(
        self,
        action_dim: int = 7,
        horizon: int = 16,
        action_scale: float = 1.0,
        gripper_threshold: float = 0.5,
    ):
        """
        Args:
            action_dim: 动作空间维度（默认 7: 6DoF + 夹爪）
            horizon: 预测视界（未来 N 步）
            action_scale: 动作缩放因子
            gripper_threshold: 夹爪开合二值化阈值
        """
        self._action_dim = action_dim
        self._horizon = horizon
        self._action_scale = action_scale
        self._gripper_threshold = gripper_threshold
        logger.info(
            "[ChunkPredictor] Initialized: dim=%d, horizon=%d, scale=%.2f",
            action_dim, horizon, action_scale,
        )

    def predict(
        self,
        raw_output: np.ndarray,
        current_pose: Optional[np.ndarray] = None,
        model_name: str = "brain-vla",
    ) -> ChunkPrediction:
        """从模型原始输出解码动作序列。

        Args:
            raw_output: VLA 模型原始输出 (horizon, action_dim)
            current_pose: 当前末端执行器位姿 (7,)，用于相对→绝对转换
            model_name: 模型名称（用于日志）

        Returns:
            ChunkPrediction 解码后的动作预测
        """
        t0 = time.perf_counter()

        # 确保输出形状正确
        if raw_output.ndim == 1:
            raw_output = raw_output.reshape(1, -1)

        n_steps = min(raw_output.shape[0], self._horizon)
        if raw_output.shape[1] < self._action_dim:
            # 补齐缺失维度
            padded = np.zeros((n_steps, self._action_dim), dtype=np.float32)
            padded[:, :raw_output.shape[1]] = raw_output[:n_steps, :]
            raw_output = padded

        # 应用动作缩放
        scaled = raw_output * self._action_scale

        # 如果提供了当前位姿，将相对动作转为绝对位姿
        if current_pose is not None:
            scaled = scaled + current_pose.reshape(1, -1)

        # 构建 ActionChunk 列表
        chunks = []
        for i in range(n_steps):
            action_arr = scaled[i]
            # 二值化夹爪
            gripper = 1.0 if action_arr[6] > self._gripper_threshold else 0.0
            chunk = ActionChunk(
                x=float(action_arr[0]), y=float(action_arr[1]), z=float(action_arr[2]),
                roll=float(action_arr[3]), pitch=float(action_arr[4]), yaw=float(action_arr[5]),
                gripper=gripper,
                confidence=0.85,  # stub 固定置信度
            )
            chunks.append(chunk)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            "[ChunkPredictor] Predicted %d chunks in %.1f ms (model=%s)",
            n_steps, elapsed_ms, model_name,
        )

        return ChunkPrediction(
            chunks=chunks,
            horizon=n_steps,
            inference_ms=elapsed_ms,
            model_name=model_name,
        )

    def smooth(
        self,
        prediction: ChunkPrediction,
        window: int = 3,
    ) -> ChunkPrediction:
        """对动作序列做时间平滑（移动平均）。

        减少帧间抖动，使运动更加流畅。

        Args:
            prediction: 原始预测
            window: 平滑窗口大小

        Returns:
            平滑后的预测
        """
        if len(prediction.chunks) < 3:
            return prediction

        arr = np.array([c.as_array() for c in prediction.chunks])

        # 简单移动平均平滑（除夹爪外）
        smoothed = arr.copy()
        half = window // 2
        for i in range(half, len(arr) - half):
            smoothed[i, :6] = arr[i - half:i + half + 1, :6].mean(axis=0)

        chunks = [ActionChunk.from_array(smoothed[i], prediction.chunks[i].confidence)
                   for i in range(len(prediction.chunks))]

        logger.info("[ChunkPredictor] Smoothed prediction (window=%d)", window)
        return ChunkPrediction(
            chunks=chunks,
            horizon=prediction.horizon,
            inference_ms=prediction.inference_ms,
            model_name=prediction.model_name,
        )

    def interpolate(
        self,
        prediction: ChunkPrediction,
        target_freq: float = 50.0,
        source_freq: float = 10.0,
    ) -> ChunkPrediction:
        """将低频预测插值到高频执行频率。

        例如: 10Hz 预测 → 50Hz 执行（机器人控制周期）

        Args:
            prediction: 原始预测
            target_freq: 目标执行频率 (Hz)
            source_freq: 原始预测频率 (Hz)

        Returns:
            插值后的预测
        """
        ratio = int(target_freq / source_freq)
        if ratio <= 1:
            return prediction

        arr = np.array([c.as_array() for c in prediction.chunks])
        t_original = np.arange(len(arr))
        t_new = np.linspace(0, len(arr) - 1, len(arr) * ratio)

        interpolated = np.zeros((len(t_new), self._action_dim), dtype=np.float32)
        for d in range(self._action_dim):
            interpolated[:, d] = np.interp(t_new, t_original, arr[:, d])

        chunks = [ActionChunk.from_array(interpolated[i]) for i in range(len(interpolated))]

        logger.info(
            "[ChunkPredictor] Interpolated %d→%d chunks (%dHz→%dHz)",
            len(prediction.chunks), len(chunks), int(source_freq), int(target_freq),
        )
        return ChunkPrediction(
            chunks=chunks,
            horizon=len(chunks),
            inference_ms=prediction.inference_ms,
            model_name=prediction.model_name,
        )

    @property
    def horizon(self) -> int:
        return self._horizon

    @property
    def action_dim(self) -> int:
        return self._action_dim

    def __repr__(self) -> str:
        return f"ChunkPredictor(dim={self._action_dim}, horizon={self._horizon})"
