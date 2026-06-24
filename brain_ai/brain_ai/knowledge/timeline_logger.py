"""
brain_ai/knowledge/timeline_logger.py — Task execution timeline logger.

Records timestamped steps and generates a structured timeline for review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Optional


@dataclass
class TimelineStep:
    step_id: int
    timestamp: str
    phase: str          # "planning" | "hitl" | "executing" | "completed" | "failed"
    description: str
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "step_id":     self.step_id,
            "timestamp":   self.timestamp,
            "phase":       self.phase,
            "description": self.description,
            "duration_ms": round(self.duration_ms, 2),
            "metadata":    self.metadata,
        }


class TimelineLogger:
    """
    Logs task execution phases with timestamps.
    One TimelineLogger instance per task.
    """

    def __init__(self, task_id: str = "") -> None:
        self.task_id = task_id
        self._steps: list[TimelineStep] = []
        self._lock  = Lock()
        self._last_ts: Optional[datetime] = None
        self._counter = 0

    def log(self, phase: str, description: str, **metadata) -> TimelineStep:
        now = datetime.now()
        duration_ms = (
            (now - self._last_ts).total_seconds() * 1000
            if self._last_ts is not None else 0.0
        )
        step = TimelineStep(
            step_id=self._counter,
            timestamp=now.isoformat(),
            phase=phase,
            description=description,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        with self._lock:
            self._steps.append(step)
            self._counter += 1
        self._last_ts = now
        return step

    def steps(self) -> list[dict]:
        with self._lock:
            return [s.to_dict() for s in self._steps]

    def summary(self) -> dict:
        with self._lock:
            if not self._steps:
                return {"task_id": self.task_id, "step_count": 0}
            total_ms = sum(s.duration_ms for s in self._steps)
            phases = [s.phase for s in self._steps]
            return {
                "task_id":     self.task_id,
                "step_count":  len(self._steps),
                "total_ms":    round(total_ms, 2),
                "phases":      phases,
                "start":       self._steps[0].timestamp,
                "end":         self._steps[-1].timestamp,
            }

    def clear(self) -> None:
        with self._lock:
            self._steps.clear()
            self._counter = 0
            self._last_ts = None
