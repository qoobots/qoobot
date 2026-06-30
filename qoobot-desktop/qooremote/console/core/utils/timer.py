"""高精度计时器 — 基于 time.monotonic 的精确计时"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Timer:
    """高精度计时器

    基于 time.monotonic()，不受系统时钟调整影响。
    """

    _start_time: float = 0.0
    _laps: list[float] = field(default_factory=list)
    _running: bool = False

    def start(self) -> Timer:
        """开始计时"""
        self._start_time = time.monotonic()
        self._running = True
        self._laps.clear()
        return self

    def stop(self) -> float:
        """停止计时，返回经过秒数"""
        if not self._running:
            return 0.0
        self._running = False
        return self.elapsed

    def lap(self, label: str = "") -> float:
        """记录一次计圈，返回自上次计圈经过的时间"""
        now = time.monotonic()
        last = self._laps[-1] if self._laps else self._start_time
        delta = now - last
        self._laps.append(now)
        return delta

    def reset(self) -> None:
        """重置计时器"""
        self._start_time = time.monotonic()
        self._laps.clear()

    @property
    def elapsed(self) -> float:
        """自 start() 以来的经过时间 (秒)"""
        if not self._running:
            return 0.0
        return time.monotonic() - self._start_time

    @property
    def elapsed_ms(self) -> int:
        """经过时间 (毫秒)"""
        return int(self.elapsed * 1000)


class RateLimiter:
    """频率限制器

    确保某个操作以指定的频率执行（如 30Hz 状态刷新）。
    """

    def __init__(self, rate_hz: float = 30.0) -> None:
        """
        Args:
            rate_hz: 目标频率 (Hz)
        """
        self._interval = 1.0 / rate_hz
        self._last_time = 0.0

    def should_run(self) -> bool:
        """检查是否应该执行操作"""
        now = time.monotonic()
        if now - self._last_time >= self._interval:
            self._last_time = now
            return True
        return False

    def wait_remaining(self) -> float:
        """返回距离下次执行还需等待的秒数"""
        now = time.monotonic()
        remaining = self._interval - (now - self._last_time)
        return max(0.0, remaining)

    def reset(self) -> None:
        self._last_time = time.monotonic()
