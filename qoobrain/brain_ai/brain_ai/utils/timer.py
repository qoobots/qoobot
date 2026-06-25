"""
brain_ai/utils/timer.py — High-resolution profiling timers.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Generator, Optional


@dataclass
class TimerStats:
    name: str
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0

    def update(self, elapsed_ms: float) -> None:
        self.count    += 1
        self.total_ms += elapsed_ms
        self.min_ms    = min(self.min_ms, elapsed_ms)
        self.max_ms    = max(self.max_ms, elapsed_ms)

    def to_dict(self) -> dict:
        return {
            "name":     self.name,
            "count":    self.count,
            "avg_ms":   round(self.avg_ms, 2),
            "min_ms":   round(self.min_ms, 2),
            "max_ms":   round(self.max_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


class Timer:
    """
    Simple lap timer with nanosecond resolution.
    """

    def __init__(self) -> None:
        self._start: Optional[float] = None
        self._laps: list[float] = []

    def start(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def lap(self) -> float:
        """Record a lap, return elapsed ms since last lap (or start)."""
        now = time.perf_counter()
        ref = self._laps[-1] if self._laps else (self._start or now)
        elapsed = (now - ref) * 1000.0
        self._laps.append(now)
        return elapsed

    def elapsed_ms(self) -> float:
        if self._start is None:
            return 0.0
        return (time.perf_counter() - self._start) * 1000.0

    def reset(self) -> None:
        self._start = None
        self._laps.clear()


class ProfilingRegistry:
    """Global profiling timer registry — tracks average latency per named operation."""

    _instance: Optional["ProfilingRegistry"] = None

    def __init__(self) -> None:
        self._stats: dict[str, TimerStats] = {}
        self._lock  = Lock()

    @classmethod
    def get(cls) -> "ProfilingRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record(self, name: str, elapsed_ms: float) -> None:
        with self._lock:
            if name not in self._stats:
                self._stats[name] = TimerStats(name)
            self._stats[name].update(elapsed_ms)

    def report(self) -> list[dict]:
        with self._lock:
            return sorted(
                [s.to_dict() for s in self._stats.values()],
                key=lambda x: x["avg_ms"],
                reverse=True,
            )

    def clear(self) -> None:
        with self._lock:
            self._stats.clear()


@contextmanager
def timed(name: str) -> Generator[None, None, None]:
    """Context manager: time a block and record to global ProfilingRegistry."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000.0
        ProfilingRegistry.get().record(name, elapsed)
