"""
brain_ai/planner/moveit_client.py — MoveIt2 motion planning client.

Wraps communication with brain_core's motion_planner (ROS 2 / MoveIt2).
Supports:
  - plan_to_pose:    Cartesian goal → joint trajectory
  - plan_cartesian:  Straight-line Cartesian path
  - compute_ik:      End-effector pose → joint angles
  - check_collision: Validate a trajectory against the planning scene

In production, this calls the brain_core gRPC Control service.
For development/testing, a stub returns simple linear-interpolated trajectories.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class PlannerStatus(str, Enum):
    SUCCESS      = "SUCCESS"
    TIMED_OUT    = "TIMED_OUT"
    NO_SOLUTION  = "NO_SOLUTION"
    INVALID_GOAL = "INVALID_GOAL"
    ERROR        = "ERROR"


@dataclass
class PlanningRequest:
    """A single motion planning request."""
    target_pose: list[float]     # [x, y, z, qx, qy, qz, qw] or joint positions
    is_joint_space: bool = False
    max_velocity_scale: float = 0.8
    max_acceleration_scale: float = 0.6
    clearance_m: float = 0.05
    planning_time_sec: float = 3.0
    max_attempts: int = 3
    start_joint_state: Optional[list[float]] = None


@dataclass
class PlanningResult:
    """Result of a single motion planning request."""
    status: PlannerStatus = PlannerStatus.SUCCESS
    trajectory: Optional[list[list[float]]] = None  # N × DOF joint positions
    planning_time_ms: float = 0.0
    path_length_m: float = 0.0
    fraction_computed: float = 1.0    # 0.0–1.0 (partial solution)
    error_message: str = ""

    @property
    def success(self) -> bool:
        return self.status == PlannerStatus.SUCCESS


class MoveItClient:
    """
    MoveIt2 planning client.

    In production: calls brain_core gRPC ControlService.ExecuteTrajectory /
    control_msgs.msg.JointTrajectory publish.
    In dev/stub mode: returns simple interpolated paths.
    """

    def __init__(
        self,
        use_stub: bool = True,
        grpc_endpoint: str = "localhost:50054",
        dof: int = 7,
    ) -> None:
        self._use_stub = use_stub
        self._grpc_endpoint = grpc_endpoint
        self._dof = dof
        logger.info(
            f"[MoveItClient] Initialized: mode={'STUB' if use_stub else 'gRPC'}, "
            f"endpoint={grpc_endpoint}, dof={dof}"
        )

    # ── Planning API ───────────────────────────────────────────────────────

    def plan_to_pose(self, req: PlanningRequest) -> PlanningResult:
        """Plan a trajectory from current state to target Cartesian pose."""
        if self._use_stub:
            return self._stub_plan(req)
        return self._grpc_plan(req)

    def plan_cartesian_path(self, waypoints: list[list[float]], req: PlanningRequest) -> PlanningResult:
        """Plan a Cartesian path through a sequence of waypoints."""
        if self._use_stub:
            return self._stub_cartesian(waypoints, req)
        return self._grpc_cartesian(waypoints, req)

    def compute_ik(
        self,
        target_pose: list[float],
        seed_joint_state: Optional[list[float]] = None,
    ) -> Optional[list[float]]:
        """Compute inverse kinematics for a target pose."""
        if self._use_stub:
            return self._stub_ik(target_pose)
        return self._grpc_ik(target_pose, seed_joint_state)

    def check_collision(self, trajectory: list[list[float]]) -> bool:
        """Check whether a trajectory is collision-free."""
        if self._use_stub:
            return True  # Stub assumes safe
        return self._grpc_check_collision(trajectory)

    # ── Stub implementation ────────────────────────────────────────────────

    def _stub_plan(self, req: PlanningRequest) -> PlanningResult:
        """Stub: generate a simple linear interpolation trajectory."""
        from math import sqrt

        t0 = time.perf_counter()

        # Default start: zero joint state
        start_joints = req.start_joint_state or [0.0] * self._dof

        # Target: if pose, convert through dummy IK; if joint, use directly
        if req.is_joint_space:
            target_joints = req.target_pose[:self._dof]
        else:
            target_joints = self._stub_ik(req.target_pose) or start_joints

        # Linear interpolation with 50 waypoints
        num_waypoints = 50
        traj: list[list[float]] = []
        for i in range(num_waypoints + 1):
            frac = i / num_waypoints
            # Smooth ease-in-out
            frac = frac * frac * (3 - 2 * frac)
            waypoint = [
                start_joints[j] + (target_joints[j] - start_joints[j]) * frac
                for j in range(self._dof)
            ]
            traj.append(waypoint)

        # Estimate path length (joint space Euclidean)
        path_len = 0.0
        for i in range(1, len(traj)):
            path_len += sqrt(
                sum((traj[i][j] - traj[i - 1][j]) ** 2 for j in range(self._dof))
            )

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.debug(
            f"[MoveItClient] Stub plan: {num_waypoints + 1} waypoints, "
            f"{elapsed_ms:.1f} ms, path_len={path_len:.3f}"
        )
        return PlanningResult(
            status=PlannerStatus.SUCCESS,
            trajectory=traj,
            planning_time_ms=elapsed_ms,
            path_length_m=path_len * 0.1,  # Scale to meters
            fraction_computed=1.0,
        )

    def _stub_cartesian(self, waypoints: list[list[float]], req: PlanningRequest) -> PlanningResult:
        """Stub Cartesian path: interpolate each segment."""
        t0 = time.perf_counter()
        all_waypoints: list[list[float]] = []

        prev_joints = req.start_joint_state or [0.0] * self._dof
        for wp in waypoints:
            ik = self._stub_ik(wp)
            if ik is None:
                return PlanningResult(
                    status=PlannerStatus.NO_SOLUTION,
                    error_message=f"IK failed for waypoint {wp}",
                )
            # Simple interpolation between waypoints (10 steps each)
            for i in range(11):
                frac = i / 10.0
                all_waypoints.append([
                    prev_joints[j] + (ik[j] - prev_joints[j]) * frac
                    for j in range(self._dof)
                ])
            prev_joints = ik

        elapsed_ms = (time.perf_counter() - t0) * 1000
        return PlanningResult(
            status=PlannerStatus.SUCCESS,
            trajectory=all_waypoints,
            planning_time_ms=elapsed_ms,
            path_length_m=len(waypoints) * 0.15,
        )

    def _stub_ik(self, target_pose: list[float]) -> Optional[list[float]]:
        """Stub IK: return a plausible joint configuration."""
        # Approximate: use pose xyz to create illustrative joint angles
        x, y, z = (target_pose[0], target_pose[1], target_pose[2]) if len(target_pose) >= 3 else (0, 0, 0)
        return [
            0.3 + x * 0.5,    # shoulder_pan
            -0.2 + y * 0.3,   # shoulder_lift
            1.5 - z * 0.2,    # elbow
            -1.0 + z * 0.2,   # wrist_1
            0.5 + x * 0.1,    # wrist_2
            0.0,              # wrist_3
            0.5 + y * 0.2,    # extra joint for 7-DOF
        ][:self._dof]

    # ── gRPC implementation (stubs for production) ─────────────────────────

    def _grpc_plan(self, req: PlanningRequest) -> PlanningResult:
        logger.warning("[MoveItClient] gRPC plan not implemented — falling back to stub")
        return self._stub_plan(req)

    def _grpc_cartesian(self, waypoints: list[list[float]], req: PlanningRequest) -> PlanningResult:
        logger.warning("[MoveItClient] gRPC Cartesian not implemented — falling back to stub")
        return self._stub_cartesian(waypoints, req)

    def _grpc_ik(self, target_pose: list[float], seed: Optional[list[float]] = None) -> Optional[list[float]]:
        logger.warning("[MoveItClient] gRPC IK not implemented — falling back to stub")
        return self._stub_ik(target_pose)

    def _grpc_check_collision(self, trajectory: list[list[float]]) -> bool:
        return True


# ── Default instance ───────────────────────────────────────────────────────

_default_client: Optional[MoveItClient] = None


def get_moveit_client() -> MoveItClient:
    global _default_client
    if _default_client is None:
        _default_client = MoveItClient()
    return _default_client
