"""
brain_ai/domain/entities.py — Core domain entities using Pydantic v2.

These are the canonical data types shared across all brain_ai modules
and communicated via gRPC with brain_core and brain_viz.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────

class SafetyLevel(str, enum.Enum):
    NORMAL    = "NORMAL"
    WARNING   = "WARNING"
    CRITICAL  = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class TaskStatus(str, enum.Enum):
    PENDING    = "PENDING"
    PLANNING   = "PLANNING"
    AWAITING_HITL = "AWAITING_HITL"
    EXECUTING  = "EXECUTING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    CANCELLED  = "CANCELLED"


class TrajectoryStrategy(str, enum.Enum):
    OPTIMAL       = "OPTIMAL"
    CONSERVATIVE  = "CONSERVATIVE"
    AGGRESSIVE    = "AGGRESSIVE"
    EXPLORATORY   = "EXPLORATORY"
    REVERSE       = "REVERSE"


# ── Intent & Task ─────────────────────────────────────────

class Intent(BaseModel):
    """Parsed intent from natural language instruction."""
    action: str = Field(..., description="Action verb, e.g. 'pick', 'place', 'navigate'")
    target: str = Field(..., description="Target object/location")
    source: Optional[str] = Field(None, description="Source location (for move tasks)")
    constraints: list[str] = Field(default_factory=list, description="E.g. 'carefully', 'fast'")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Intent recognition confidence")


class Task(BaseModel):
    """A decomposable unit of work."""
    id: str = Field(..., description="Unique task ID")
    intent: Intent
    subtasks: list[Task] = Field(default_factory=list, description="Sub-tasks for decomposition")
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)


# ── Plan ──────────────────────────────────────────────────

class Plan(BaseModel):
    """A structured execution plan derived from a task."""
    task_id: str
    behavior_tree_xml: str = Field("", description="XML representation of behavior tree")
    trajectories: list[Trajectory] = Field(default_factory=list)
    estimated_duration_sec: float = 0.0
    risk_score: float = Field(0.0, ge=0.0, le=1.0)


# ── Trajectory ────────────────────────────────────────────

class Waypoint(BaseModel):
    """Single point on a trajectory."""
    x: float; y: float; z: float
    qx: float = 0.0; qy: float = 0.0; qz: float = 0.0; qw: float = 1.0
    time_from_start_sec: float = 0.0


class Trajectory(BaseModel):
    """A complete motion trajectory with score."""
    id: str = Field(..., description="Unique trajectory ID")
    strategy: TrajectoryStrategy = TrajectoryStrategy.OPTIMAL
    waypoints: list[Waypoint] = Field(default_factory=list)
    score: float = Field(0.0, description="Quality score 0-1")
    collision_free: bool = True
    duration_sec: float = 0.0


# ── Scene Graph ───────────────────────────────────────────

class Object3D(BaseModel):
    """A detected 3D object in the scene."""
    id: str
    label: str
    centroid: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    bbox_3d: list[list[float]] = Field(default_factory=list)  # 8 corners
    confidence: float = 0.0


class SceneGraph(BaseModel):
    """Aggregated scene understanding."""
    timestamp: datetime = Field(default_factory=datetime.now)
    objects: list[Object3D] = Field(default_factory=list)
    robot_pose: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    occupancy_grid: Optional[list[list[list[int]]]] = None


# ── Robot State ───────────────────────────────────────────

class JointState(BaseModel):
    names: list[str] = Field(default_factory=list)
    positions: list[float] = Field(default_factory=list)
    velocities: list[float] = Field(default_factory=list)
    efforts: list[float] = Field(default_factory=list)


class RobotState(BaseModel):
    """Full robot state snapshot."""
    joints: JointState = Field(default_factory=JointState)
    gripper_position: float = 0.0  # 0=closed, 1=open
    safety_level: SafetyLevel = SafetyLevel.NORMAL
    emergency_stop: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


# ── Safety ────────────────────────────────────────────────

class SafetyStatus(BaseModel):
    level: SafetyLevel = SafetyLevel.NORMAL
    active_warnings: list[str] = Field(default_factory=list)
    emergency_stop_active: bool = False
    collision_risk: float = Field(0.0, ge=0.0, le=1.0)
