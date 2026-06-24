"""
brain_ai/domain/motion.py — Motion and trajectory domain models.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from brain_ai.domain.scene import Pose6D, Vec3


class TrajectoryStrategy(str, Enum):
    OPTIMAL       = "OPTIMAL"       # Shortest, fastest
    CONSERVATIVE  = "CONSERVATIVE"  # Wide safety margins
    AGGRESSIVE    = "AGGRESSIVE"    # Faster but tighter margins
    EXPLORATORY   = "EXPLORATORY"   # Novel path through unexplored space
    ADVERSARIAL   = "ADVERSARIAL"   # Stress-test worst-case


@dataclass
class JointState:
    """Robot joint state snapshot."""
    names: list[str] = field(default_factory=list)
    positions: list[float] = field(default_factory=list)    # rad
    velocities: list[float] = field(default_factory=list)   # rad/s
    efforts: list[float] = field(default_factory=list)      # Nm

    def to_dict(self) -> dict:
        return {
            "names": self.names,
            "positions": [round(p, 6) for p in self.positions],
            "velocities": [round(v, 6) for v in self.velocities],
        }


@dataclass
class Waypoint:
    """A single point on a Cartesian/joint trajectory."""
    pose: Pose6D = field(default_factory=Pose6D)
    joint_state: Optional[JointState] = None
    time_from_start_sec: float = 0.0
    velocity_scale: float = 1.0
    is_blend_point: bool = True       # Allow trajectory blending here


@dataclass
class Trajectory:
    """A candidate motion trajectory with quality metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy: TrajectoryStrategy = TrajectoryStrategy.OPTIMAL
    waypoints: list[Waypoint] = field(default_factory=list)

    # Scoring
    score: float = 0.0                # Composite score 0→1 (higher = better)
    collision_free: bool = True
    duration_sec: float = 0.0
    path_length_m: float = 0.0
    manipulability: float = 0.0       # Average Yoshikawa manipulability
    joint_effort_rms: float = 0.0

    # For HITL display
    color_hint: str = "#00ccff"       # Ghost trail color for visualization
    label: str = ""                   # Human-readable description

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "strategy": self.strategy.value,
            "score": round(self.score, 4),
            "collision_free": self.collision_free,
            "duration_sec": round(self.duration_sec, 3),
            "path_length_m": round(self.path_length_m, 4),
            "waypoint_count": len(self.waypoints),
            "color_hint": self.color_hint,
            "label": self.label,
        }


@dataclass
class TrajectorySet:
    """A set of candidate trajectories presented for HITL selection."""
    task_id: str = ""
    trajectories: list[Trajectory] = field(default_factory=list)
    best_id: Optional[str] = None          # Pre-selected best candidate
    hitl_timeout_sec: float = 3.0

    def best(self) -> Optional[Trajectory]:
        if self.best_id:
            for t in self.trajectories:
                if t.id == self.best_id:
                    return t
        if not self.trajectories:
            return None
        return max(self.trajectories, key=lambda t: t.score)

    def sorted_by_score(self) -> list[Trajectory]:
        return sorted(self.trajectories, key=lambda t: t.score, reverse=True)
