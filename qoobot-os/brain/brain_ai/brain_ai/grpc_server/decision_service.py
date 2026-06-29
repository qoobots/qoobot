"""
brain_ai/grpc_server/decision_service.py — DecisionService gRPC implementation.

Implements:
  - ExecutePlan:          start executing a behavior tree
  - GenerateTrajectories:  generate N candidate trajectories
  - SelectTrajectory:      HITL trajectory selection callback
  - CancelPlan:            cancel current plan
  - StreamPlanStatus:      streaming plan status updates
"""
from __future__ import annotations

import logging
import time
from typing import Iterator

import grpc

from brain_ai.proto_gen.brain_os.decision import (
    service_pb2,
    service_pb2_grpc,
)
from brain_ai.proto_gen.brain_os.decision import types_pb2 as decision_types
from brain_ai.proto_gen.brain_os.common import types_pb2 as common_types

logger = logging.getLogger(__name__)


class DecisionServiceServicer(service_pb2_grpc.DecisionServiceServicer):
    """gRPC servicer for DecisionService."""

    def __init__(self):
        super().__init__()
        self._active_plans: dict[str, dict] = {}
        logger.info("[DecisionService] Initialized (gRPC servicer).")

    # ── ExecutePlan ──────────────────────────────────────────────────────

    def ExecutePlan(
        self,
        request: service_pb2.ExecutePlanRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.ExecutePlanResponse:
        """Start executing a behavior tree plan."""
        logger.info(
            f"[DecisionService] ExecutePlan: plan_id={request.plan_id} "
            f"require_hitl={request.require_hitl}"
        )

        # TODO(Sprint 4): integrate with BehaviorTree.CPP executor
        # Stub: create a plan and optionally generate HITL event
        self._active_plans[request.plan_id] = {
            "state": decision_types.PlanState.PLAN_RUNNING,
            "start_time": time.time(),
        }

        hitl_event = None
        if request.require_hitl:
            # Generate 3 candidate trajectories for HITL
            trajectories = self._stub_generate_trajectories(
                request.robot_id, request.plan_id, num_candidates=3,
            )
            hitl_event = decision_types.HITLEvent(
                event_id=f"hitl-{request.plan_id}",
                plan_id=request.plan_id,
                trajectories=trajectories,
                deadline_sec=6.0,
                auto_select_trajectory_id=trajectories[0].trajectory_id if trajectories else "",
            )

        return service_pb2.ExecutePlanResponse(
            status=common_types.Status(code=0, message="plan started"),
            plan_id=request.plan_id,
            state=decision_types.PlanState.PLAN_RUNNING,
            hitl_event=hitl_event,
        )

    # ── GenerateTrajectories ────────────────────────────────────────────

    def GenerateTrajectories(
        self,
        request: service_pb2.GenerateTrajectoriesRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.GenerateTrajectoriesResponse:
        """Generate N candidate trajectories for HITL selection."""
        n = max(1, min(request.num_candidates, 5))
        logger.info(
            f"[DecisionService] GenerateTrajectories: plan={request.plan_id} "
            f"n={n}"
        )

        trajectories = self._stub_generate_trajectories(
            request.robot_id, request.plan_id, n,
        )

        return service_pb2.GenerateTrajectoriesResponse(
            status=common_types.Status(code=0, message="ok"),
            trajectories=trajectories,
        )

    # ── SelectTrajectory (HITL callback) ─────────────────────────────

    def SelectTrajectory(
        self,
        request: service_pb2.SelectTrajectoryRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.SelectTrajectoryResponse:
        """Submit human trajectory selection (HITL)."""
        logger.info(
            f"[DecisionService] SelectTrajectory: plan={request.plan_id} "
            f"selected={request.trajectory_id or '(auto/timeout)'}"
        )

        # TODO(Sprint 5): dispatch selected trajectory to motion planner
        if request.plan_id in self._active_plans:
            self._active_plans[request.plan_id]["selected_trajectory"] = (
                request.trajectory_id or "auto"
            )

        return service_pb2.SelectTrajectoryResponse(
            status=common_types.Status(code=0, message="trajectory selected"),
        )

    # ── CancelPlan ─────────────────────────────────────────────────────

    def CancelPlan(
        self,
        request: service_pb2.CancelPlanRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.CancelPlanResponse:
        """Cancel a running plan."""
        logger.info(
            f"[DecisionService] CancelPlan: plan={request.plan_id} "
            f"reason={request.reason}"
        )
        self._active_plans.pop(request.plan_id, None)
        return service_pb2.CancelPlanResponse(
            status=common_types.Status(code=0, message="plan cancelled"),
        )

    # ── StreamPlanStatus (server-streaming) ──────────────────────────

    def StreamPlanStatus(
        self,
        request: service_pb2.StreamPlanStatusRequest,
        context: grpc.ServicerContext,
    ) -> Iterator[decision_types.PlanStatus]:
        """Stream plan execution status updates."""
        logger.info(
            f"[DecisionService] StreamPlanStatus: plan={request.plan_id}"
        )

        # Stub: stream fake status for 10 seconds then finish
        for i in range(10):
            if not context.is_active():
                break
            status = decision_types.PlanStatus(
                plan_id=request.plan_id,
                state=decision_types.PlanState.PLAN_RUNNING,
                progress=0.1 * i,
                current_action=f"step_{i}",
                message=f"Executing step {i}/10",
            )
            yield status
            time.sleep(0.5)

        # Final status
        if context.is_active():
            yield decision_types.PlanStatus(
                plan_id=request.plan_id,
                state=decision_types.PlanState.PLAN_SUCCESS,
                progress=1.0,
                current_action="done",
                message="Plan completed successfully.",
            )

    # ── Internal helpers ───────────────────────────────────────────────

    def _stub_generate_trajectories(
        self, robot_id: str, plan_id: str, num_candidates: int = 3,
    ) -> list[decision_types.Trajectory]:
        """Stub: generate fake candidate trajectories."""
        trajectories = []
        for i in range(num_candidates):
            score = 0.95 - i * 0.05
            trajectories.append(
                decision_types.Trajectory(
                    trajectory_id=f"traj-{plan_id}-{i}",
                    plan_id=plan_id,
                    rank=i + 1,
                    score=score,
                    risk_level=decision_types.RiskLevel.RISK_LOW if i == 0
                                else decision_types.RiskLevel.RISK_MEDIUM,
                    description=f"{'Recommended (safest)' if i == 0 else f'Candidate {i+1}'}",
                )
            )
        return trajectories
