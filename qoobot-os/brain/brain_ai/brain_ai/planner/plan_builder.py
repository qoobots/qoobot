"""
brain_ai/planner/plan_builder.py — End-to-end execution plan builder.

Orchestrates the full planning workflow:
  1. Receive RobotTask + scene context
  2. Build BehaviorTree from LLM output (via BTComposer)
  3. Generate candidate trajectories (via TrajectoryGenerator)
  4. Initiate HITL selection (via HITLManager)
  5. Assemble ExecutionPlan with selected trajectory

This is the primary entry point for turning an LLM-decomposed task
into an executable plan ready for brain_core.
"""

from __future__ import annotations

import logging
from typing import Optional

from brain_ai.domain.motion import TrajectorySet
from brain_ai.domain.plan import ExecutionPlan, PlanStatus
from brain_ai.domain.task import RobotTask, TaskStatus
from brain_ai.planner.bt_composer import BTComposer, get_bt_composer
from brain_ai.planner.hitl_manager import HITLManager, HITLResult
from brain_ai.planner.scorer import TrajectoryScorer
from brain_ai.planner.trajectory_gen import TrajectoryGenerator, get_trajectory_generator

logger = logging.getLogger(__name__)


class PlanBuilder:
    """
    Complete planning pipeline: BT assembly → trajectory generation → HITL → ExecutionPlan.

    Usage:
        builder = PlanBuilder(trajectory_gen, bt_composer, hitl_manager)
        plan = builder.build(task, scene_context, bt_xml)
        if builder.needs_hitl:
            result = await builder.run_hitl(plan, timeout_sec=3.0)
            plan = builder.apply_hitl_result(plan, result)
            builder.finalize(plan)
    """

    def __init__(
        self,
        trajectory_gen: Optional[TrajectoryGenerator] = None,
        bt_composer: Optional[BTComposer] = None,
        hitl_manager: Optional[HITLManager] = None,
        scorer: Optional[TrajectoryScorer] = None,
        enable_hitl: bool = True,
    ) -> None:
        self._trajectory_gen = trajectory_gen or get_trajectory_generator()
        self._bt_composer = bt_composer or get_bt_composer()
        self._hitl_manager = hitl_manager
        self._scorer = scorer
        self._enable_hitl = enable_hitl and hitl_manager is not None

        self._current_plan: Optional[ExecutionPlan] = None
        self._current_trajectory_set: Optional[TrajectorySet] = None

        logger.info(
            f"[PlanBuilder] Initialized, HITL={'enabled' if self._enable_hitl else 'disabled'}"
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def build(
        self,
        task: RobotTask,
        scene_context: Optional[dict] = None,
        bt_xml: Optional[str] = None,
        target_pose: Optional[list[float]] = None,
        start_joint_state: Optional[list[float]] = None,
        require_hitl: bool = False,
    ) -> ExecutionPlan:
        """
        Build an ExecutionPlan from a decomposed RobotTask.

        Steps:
          1. Compose BehaviorTree from BT XML
          2. Generate candidate trajectories
          3. Create ExecutionPlan (HITL selection deferred)

        Args:
            task:               Decomposed robot task with subtasks
            scene_context:      Current scene graph
            bt_xml:             LLM-generated behavior tree XML
            target_pose:        Final end-effector pose
            start_joint_state:  Current robot joint positions
            require_hitl:       Force HITL even for single-trajectory plans

        Returns:
            ExecutionPlan ready for execution (or HITL if enabled)
        """
        plan = ExecutionPlan(
            task_id=task.id,
            status=PlanStatus.GENERATING,
        )

        # Step 1: Compose Behavior Tree
        if bt_xml:
            bt = self._bt_composer.compose(bt_xml, task_id=task.id)
            is_valid, warnings = self._bt_composer.validate(bt)
            if not is_valid and warnings:
                logger.warning(
                    f"[PlanBuilder] BT validation warnings for task {task.id}: "
                    + "; ".join(warnings[:5])
                )
            plan.behavior_tree = bt
            logger.debug(
                f"[PlanBuilder] BT composed for task {task.id}"
            )
        else:
            logger.info(
                f"[PlanBuilder] No BT XML provided for task {task.id}, "
                f"using empty behavior tree"
            )

        # Step 2: Generate trajectories
        if target_pose is not None:
            self._current_trajectory_set = self._trajectory_gen.generate(
                task_id=task.id,
                target_pose=target_pose,
                start_joint_state=start_joint_state,
                hitl_timeout_sec=task.hitl_timeout_sec,
                scene_context=scene_context,
            )
            plan.trajectory_ids = [
                t.id for t in self._current_trajectory_set.trajectories
            ]

            # If only one trajectory and no HITL required, auto-select
            single_traj = len(self._current_trajectory_set.trajectories) <= 1
            if single_traj and not require_hitl:
                best = self._current_trajectory_set.best()
                if best:
                    plan.select_trajectory(best.id)
                    plan.status = PlanStatus.READY

            logger.info(
                f"[PlanBuilder] Generated {len(plan.trajectory_ids)} "
                f"trajectories for task {task.id}"
            )
        else:
            logger.info(
                f"[PlanBuilder] No target pose for task {task.id}, "
                f"skipping trajectory generation"
            )
            plan.status = PlanStatus.READY

        # Step 3: Populate metadata
        plan.estimated_duration_sec = self._estimate_duration(task)
        plan.risk_score = self._estimate_risk(task, scene_context)

        self._current_plan = plan
        return plan

    async def run_hitl(
        self,
        plan: Optional[ExecutionPlan] = None,
        timeout_sec: Optional[float] = None,
    ) -> Optional[HITLResult]:
        """
        Run HITL selection for the current plan.

        Must be called after build() when plan has multiple trajectories.
        """
        if not self._enable_hitl or self._hitl_manager is None:
            logger.info("[PlanBuilder] HITL disabled — auto-selecting best")
            return None

        plan = plan or self._current_plan
        if plan is None:
            logger.error("[PlanBuilder] No plan to run HITL for")
            return None

        ts = self._current_trajectory_set
        if ts is None or not ts.trajectories:
            logger.warning("[PlanBuilder] No trajectories for HITL")
            return None

        plan.status = PlanStatus.IDLE  # Will be set by apply_hitl_result

        result = await self._hitl_manager.start_selection(
            plan=plan,
            trajectory_set=ts,
            timeout_sec=timeout_sec,
        )
        return result

    def apply_hitl_result(
        self,
        plan: ExecutionPlan,
        result: HITLResult,
    ) -> ExecutionPlan:
        """Apply HITL selection result to the plan."""
        plan.select_trajectory(result.selected_trajectory_id)
        logger.info(
            f"[PlanBuilder] HITL result applied: trajectory "
            f"{result.selected_trajectory_id} selected "
            f"({'user' if result.selected_by_user else 'auto'})"
        )
        return plan

    def finalize(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Mark plan as ready for execution."""
        if plan.selected_trajectory_id:
            plan.status = PlanStatus.READY
        else:
            plan.status = PlanStatus.FAILED
            plan.notes += " No trajectory selected."
        return plan

    # ── Internal estimators ────────────────────────────────────────────────

    @staticmethod
    def _estimate_duration(task: RobotTask) -> float:
        """Estimate total execution duration from subtasks."""
        return sum(st.estimated_duration_sec for st in task.subtasks)

    @staticmethod
    def _estimate_risk(task: RobotTask, scene_context: Optional[dict] = None) -> float:
        """
        Estimate execution risk score (0.0 = safe, 1.0 = high risk).
        Based on task complexity, subtask count, and scene obstacles.
        """
        risk = 0.0
        # More subtasks = higher risk
        risk += min(len(task.subtasks) * 0.05, 0.3)
        # Higher priority = potentially more urgent/dangerous
        risk += task.priority.value * 0.05
        # Scene context with obstacles
        if scene_context:
            obj_count = scene_context.get("object_count", 0)
            risk += min(obj_count * 0.02, 0.2)
        return min(risk, 1.0)

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def needs_hitl(self) -> bool:
        if self._current_trajectory_set is None:
            return False
        return len(self._current_trajectory_set.trajectories) > 1

    @property
    def current_plan(self) -> Optional[ExecutionPlan]:
        return self._current_plan
