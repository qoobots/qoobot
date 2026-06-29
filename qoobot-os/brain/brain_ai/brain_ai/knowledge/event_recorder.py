"""
brain_ai/knowledge/event_recorder.py — Records system events to ring buffer + optional log file.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from enum import Enum
from threading import Lock
from typing import Any, Optional

from brain_ai.knowledge.ring_buffer import RingBuffer

logger = logging.getLogger(__name__)


class EventCategory(str, Enum):
    TASK      = "task"
    SAFETY    = "safety"
    PERCEPTION= "perception"
    PLANNING  = "planning"
    EXECUTION = "execution"
    SYSTEM    = "system"
    HITL      = "hitl"


class EventRecorder:
    """
    Records structured system events to:
      1. In-memory ring buffer (fast, for real-time queries)
      2. Optional JSONL log file (persistent)
    """

    def __init__(
        self,
        buffer_size: int = 500,
        log_path: Optional[str] = None,
    ) -> None:
        self._buffer = RingBuffer[dict](buffer_size)
        self._lock   = Lock()
        self._log_path = log_path or os.environ.get("BRAIN_AI_EVENT_LOG", "")
        self._log_file = None

        if self._log_path:
            try:
                os.makedirs(os.path.dirname(self._log_path) or ".", exist_ok=True)
                self._log_file = open(self._log_path, "a", encoding="utf-8")  # noqa: SIM115
                logger.info(f"EventRecorder: logging to {self._log_path}")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"EventRecorder: cannot open log file: {exc}")

    # ─── Record ───────────────────────────────────────────────

    def record(
        self,
        category: EventCategory,
        event_type: str,
        data: Optional[dict] = None,
        level: str = "INFO",
    ) -> dict:
        event = {
            "ts":       datetime.now().isoformat(),
            "category": category.value,
            "type":     event_type,
            "level":    level,
            "data":     data or {},
        }
        self._buffer.push(event)
        if self._log_file:
            with self._lock:
                self._log_file.write(json.dumps(event, ensure_ascii=False) + "\n")
                self._log_file.flush()
        return event

    # ─── Convenience methods ──────────────────────────────────

    def task_started(self, task_id: str, instruction: str) -> None:
        self.record(EventCategory.TASK, "task_started",
                    {"task_id": task_id, "instruction": instruction})

    def task_completed(self, task_id: str, success: bool, duration_sec: float = 0.0) -> None:
        self.record(EventCategory.TASK, "task_completed",
                    {"task_id": task_id, "success": success, "duration_sec": duration_sec},
                    level="INFO" if success else "WARN")

    def safety_alert(self, alert_type: str, level: int, message: str) -> None:
        self.record(EventCategory.SAFETY, "safety_alert",
                    {"alert_type": alert_type, "level": level, "message": message},
                    level="WARN" if level > 0 else "ERROR")

    def hitl_prompt(self, task_id: str, trajectory_count: int) -> None:
        self.record(EventCategory.HITL, "hitl_prompt",
                    {"task_id": task_id, "trajectory_count": trajectory_count})

    def hitl_resolved(self, task_id: str, selected_id: str, by_user: bool) -> None:
        self.record(EventCategory.HITL, "hitl_resolved",
                    {"task_id": task_id, "selected_id": selected_id, "by_user": by_user})

    # ─── Query ────────────────────────────────────────────────

    def recent(self, n: int = 20) -> list[dict]:
        return self._buffer.peek_last(n)

    def filter(
        self,
        category: Optional[EventCategory] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        events = self._buffer.all()
        if category:
            events = [e for e in events if e["category"] == category.value]
        if event_type:
            events = [e for e in events if e["type"] == event_type]
        return events[-limit:]

    def close(self) -> None:
        if self._log_file:
            self._log_file.close()
