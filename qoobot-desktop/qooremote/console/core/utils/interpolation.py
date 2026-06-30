"""插值与平滑工具 — 遥操作指令平滑、数据插值"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field


def lerp(a: float, b: float, t: float) -> float:
    """线性插值"""
    return a + (b - a) * max(0.0, min(1.0, t))


def exponential_moving_average(
    current: float, target: float, smoothing_factor: float
) -> float:
    """指数移动平均 (EMA) 平滑

    Args:
        current: 当前平滑值
        target: 目标值
        smoothing_factor: 平滑因子 (0.0-1.0)，越大越快响应
    """
    return current + (target - current) * smoothing_factor


def clamp(value: float, min_val: float, max_val: float) -> float:
    """值限幅"""
    return max(min_val, min(max_val, value))


def deadzone(value: float, threshold: float) -> float:
    """摇杆死区处理

    将 [-threshold, threshold] 范围内的值归零，
    并重新映射到 [0, 1]。

    Args:
        value: 输入值 (-1.0 到 1.0)
        threshold: 死区阈值 (0.0 到 1.0)
    """
    if abs(value) < threshold:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) - threshold) / (1.0 - threshold)


@dataclass
class Smoother:
    """通用信号平滑器

    结合 EMA 和死区处理，适用于遥操作指令平滑。
    """
    smoothing_factor: float = 0.3
    deadzone_threshold: float = 0.05
    _current: float = 0.0

    def update(self, raw_value: float) -> float:
        """输入原始值，返回平滑后的值"""
        processed = deadzone(raw_value, self.deadzone_threshold)
        self._current = exponential_moving_average(
            self._current, processed, self.smoothing_factor
        )
        return self._current

    def reset(self) -> None:
        self._current = 0.0


@dataclass
class MovingAverage:
    """滑动窗口平均"""
    window_size: int = 5
    _window: deque[float] = field(default_factory=deque)

    def update(self, value: float) -> float:
        self._window.append(value)
        if len(self._window) > self.window_size:
            self._window.popleft()
        return sum(self._window) / len(self._window)

    def reset(self) -> None:
        self._window.clear()
