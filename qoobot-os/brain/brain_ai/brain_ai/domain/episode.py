"""
brain_ai/domain/episode.py — Episodic memory entities for experience storage.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from brain_ai.domain.task import TaskStatus


@dataclass
class Observation:
    """A single sensory observation captured during task execution."""
    step: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    scene_snapshot: dict = field(default_factory=dict)    # Serialized SceneGraph
    joint_positions: list[float] = field(default_factory=list)
    gripper_state: float = 0.0
    notes: str = ""


@dataclass
class Episode:
    """
    A complete execution episode — from task start to terminal state.
    Stored in the knowledge base for future retrieval and learning.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    robot_id: str = "robot_0"

    # Task context
    task_id: str = ""
    raw_instruction: str = ""
    skill_name: str = ""

    # Trajectory taken
    selected_strategy: str = ""
    trajectory_id: Optional[str] = None

    # Execution trace
    observations: list[Observation] = field(default_factory=list)
    behavior_tree_xml: str = ""

    # Outcome
    success: bool = False
    final_status: str = TaskStatus.PENDING.value
    error_message: str = ""

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Learning metadata
    reward: float = 0.0               # Reward signal for RL
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_sec(self) -> Optional[float]:
        if self.started_at is None or self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "robot_id": self.robot_id,
            "task_id": self.task_id,
            "raw_instruction": self.raw_instruction,
            "skill_name": self.skill_name,
            "selected_strategy": self.selected_strategy,
            "success": self.success,
            "final_status": self.final_status,
            "reward": self.reward,
            "duration_sec": self.duration_sec,
            "tags": self.tags,
            "observation_count": len(self.observations),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Episode":
        obj = cls()
        _skip = {"created_at", "started_at", "completed_at", "duration_sec", "observation_count"}
        for k, v in d.items():
            if k not in _skip and hasattr(obj, k):
                try:
                    setattr(obj, k, v)
                except AttributeError:
                    pass
        return obj
