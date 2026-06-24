"""
brain_ai/domain/plan.py — Execution plan data model.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PlanStatus(str, Enum):
    IDLE        = "IDLE"
    GENERATING  = "GENERATING"
    READY       = "READY"
    EXECUTING   = "EXECUTING"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"
    FAILED      = "FAILED"


@dataclass
class SkillNode:
    """A single node in a behavior tree, representing one skill call."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    node_type: str = "action"          # "action" | "sequence" | "selector" | "condition"
    skill_name: str = ""
    parameters: dict = field(default_factory=dict)
    children: list["SkillNode"] = field(default_factory=list)

    def to_xml_element(self, indent: int = 0) -> str:
        pad = "  " * indent
        params_str = " ".join(f'{k}="{v}"' for k, v in self.parameters.items())
        if self.children:
            lines = [f"{pad}<{self.node_type} name=\"{self.skill_name}\" {params_str}>"]
            for child in self.children:
                lines.append(child.to_xml_element(indent + 1))
            lines.append(f"{pad}</{self.node_type}>")
            return "\n".join(lines)
        return f"{pad}<{self.node_type} name=\"{self.skill_name}\" {params_str}/>"


@dataclass
class BehaviorTree:
    """Root of a behavior tree generated from task decomposition."""
    task_id: str = ""
    root: Optional[SkillNode] = None
    xml_str: str = ""        # Canonical XML from LLM or reconstructed from root

    def to_xml(self) -> str:
        if self.xml_str:
            return self.xml_str
        if self.root is None:
            return "<BehaviorTree/>"
        return f"<BehaviorTree>\n{self.root.to_xml_element(1)}\n</BehaviorTree>"


@dataclass
class ExecutionPlan:
    """Complete execution plan: behavior tree + candidate trajectories."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    status: PlanStatus = PlanStatus.IDLE

    behavior_tree: Optional[BehaviorTree] = None
    trajectory_ids: list[str] = field(default_factory=list)   # IDs into TrajectoryRegistry
    selected_trajectory_id: Optional[str] = None

    estimated_duration_sec: float = 0.0
    risk_score: float = 0.0              # 0.0 (safe) → 1.0 (high risk)
    notes: str = ""

    # ─── Helpers ───────────────────────────────────────────────

    def select_trajectory(self, tid: str) -> None:
        if tid not in self.trajectory_ids:
            raise ValueError(f"Trajectory {tid!r} not in plan candidates")
        self.selected_trajectory_id = tid
        self.status = PlanStatus.EXECUTING

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "status": self.status.value,
            "bt_xml": self.behavior_tree.to_xml() if self.behavior_tree else "",
            "trajectory_ids": self.trajectory_ids,
            "selected_trajectory_id": self.selected_trajectory_id,
            "estimated_duration_sec": self.estimated_duration_sec,
            "risk_score": self.risk_score,
        }
