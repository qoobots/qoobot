"""
brain_ai/domain/task.py — Task lifecycle management.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING       = "PENDING"
    PLANNING      = "PLANNING"
    AWAITING_HITL = "AWAITING_HITL"
    EXECUTING     = "EXECUTING"
    COMPLETED     = "COMPLETED"
    FAILED        = "FAILED"
    CANCELLED     = "CANCELLED"


class TaskPriority(int, Enum):
    LOW    = 0
    NORMAL = 1
    HIGH   = 2
    URGENT = 3


@dataclass
class SubTask:
    """Atomic unit of execution within a task."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    skill_name: str = ""          # e.g. "pick_object", "navigate_to"
    parameters: dict[str, Any] = field(default_factory=dict)
    preconditions: list[str] = field(default_factory=list)   # e.g. ["object_detected"]
    postconditions: list[str] = field(default_factory=list)  # e.g. ["object_in_hand"]
    estimated_duration_sec: float = 5.0
    retries: int = 0
    max_retries: int = 2

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "parameters": self.parameters,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "estimated_duration_sec": self.estimated_duration_sec,
        }


@dataclass
class RobotTask:
    """Top-level task derived from user natural-language instruction."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_instruction: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    subtasks: list[SubTask] = field(default_factory=list)

    # Lifecycle timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Execution metadata
    error_message: Optional[str] = None
    selected_trajectory_id: Optional[str] = None
    hitl_timeout_sec: float = 3.0
    retry_count: int = 0

    # ─── Lifecycle helpers ─────────────────────────────────────

    def start(self) -> None:
        self.status = TaskStatus.PLANNING
        self.started_at = datetime.now()

    def await_hitl(self) -> None:
        self.status = TaskStatus.AWAITING_HITL

    def execute(self) -> None:
        self.status = TaskStatus.EXECUTING

    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, reason: str = "") -> None:
        self.status = TaskStatus.FAILED
        self.error_message = reason
        self.completed_at = datetime.now()

    def cancel(self) -> None:
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.now()

    # ─── Helpers ───────────────────────────────────────────────

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )

    @property
    def duration_sec(self) -> Optional[float]:
        if self.started_at is None:
            return None
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "raw_instruction": self.raw_instruction,
            "status": self.status.value,
            "priority": self.priority.value,
            "subtasks": [s.to_dict() for s in self.subtasks],
            "created_at": self.created_at.isoformat(),
            "error_message": self.error_message,
        }
