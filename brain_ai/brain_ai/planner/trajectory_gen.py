"""
brain_ai/planner/trajectory_gen.py — Multi-strategy trajectory generator.

Generates multiple candidate trajectories for a given task using different
planning strategies (optimal, conservative, aggressive, exploratory, adversarial).

Integration points:
  - MoveItClient: calls brain_core motion planning
  - StrategyConfig: per-strategy planning parameters
  - TrajectoryScorer: scores and ranks candidates
  - SceneGraph: provides obstacle/environment context
"""

from __future__ import annotations

import logging
from typing import Optional

from brain_ai.domain.motion import (
    Trajectory,
    TrajectorySet,
    TrajectoryStrategy,
    Waypoint,
)
from brain_ai.domain.scene import Pose6D
from brain_ai.planner.moveit_client import (
    MoveItClient,
    PlanningRequest,
    PlanningResult,
    get_moveit_client,
)
from brain_ai.planner.scorer import TrajectoryScorer, get_scorer
from brain_ai.planner.strategy_enum import (
    StrategyConfig,
    StrategyName,
    get_strategy_config,
)

logger = logging.getLogger(__name__)

# Mapping from domain TrajectoryStrategy to planner StrategyName
_STRATEGY_MAP: dict[TrajectoryStrategy, StrategyName] = {
    TrajectoryStrategy.OPTIMAL:      StrategyName.OPTIMAL,
    TrajectoryStrategy.CONSERVATIVE: StrategyName.CONSERVATIVE,
    TrajectoryStrategy.AGGRESSIVE:   StrategyName.AGGRESSIVE,
    TrajectoryStrategy.EXPLORATORY:  StrategyName.EXPLORATORY,
    TrajectoryStrategy.ADVERSARIAL:  StrategyName.ADVERSARIAL,
}


class TrajectoryGenerator:
    """
    Generate, score, and package candidate trajectories for HITL selection.

    Usage:
        gen = TrajectoryGenerator(moveit_client, scorer)
        trajectory_set = gen.generate(task_id="...", target_pose=Pose6D(...))
    """

    def __init__(
        self,
        moveit_client: Optional[MoveItClient] = None,
        scorer: Optional[TrajectoryScorer] = None,
        strategies: Optional[list[TrajectoryStrategy]] = None,
    ) -> None:
        self._moveit = moveit_client or get_moveit_client()
        self._scorer = scorer or get_scorer()
        self._strategies = strategies or [
            TrajectoryStrategy.OPTIMAL,
            TrajectoryStrategy.CONSERVATIVE,
            TrajectoryStrategy.AGGRESSIVE,
        ]
        logger.info(
            f"[TrajectoryGenerator] Initialized with strategies: "
            f"{[s.value for s in self._strategies]}"
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def generate(
        self,
        task_id: str,
        target_pose: Pose6D | list[float],
        start_joint_state: Optional[list[float]] = None,
        hitl_timeout_sec: float = 3.0,
        scene_context: Optional[dict] = None,
    ) -> TrajectorySet:
        """
        Generate a TrajectorySet with one candidate per strategy.

        Args:
            task_id:             Parent task ID
            target_pose:         Cartesian goal (Pose6D or [x,y,z,qx,qy,qz,qw])
            start_joint_state:   Current robot joint positions
            hitl_timeout_sec:    HITL selection countdown
            scene_context:       Optional scene graph for obstacle avoidance

        Returns:
            TrajectorySet with scored, ranked candidates.
        """
        # Normalize pose input
        if isinstance(target_pose, Pose6D):
            pose_list = target_pose.to_list()
        else:
            pose_list = target_pose

        trajectories: list[Trajectory] = []
        for strategy in self._strategies:
            traj = self._plan_one(
                task_id, strategy, pose_list, start_joint_state, scene_context
            )
            if traj is not None:
                trajectories.append(traj)
            else:
                logger.warning(
                    f"[TrajectoryGenerator] Strategy {strategy.value} "
                    f"returned no trajectory for task {task_id}"
                )

        if not trajectories:
            logger.error(
                f"[TrajectoryGenerator] No trajectories generated for task {task_id}! "
                f"Falling back to stub."
            )
            # Emergency fallback: generate at least one stub trajectory
            trajectories = [self._emergency_stub(task_id, pose_list)]

        # Score and rank
        strategy_bonuses = self._build_bonus_map(trajectories)
        ranked = self._scorer.rank(trajectories, strategy_bonus_map=strategy_bonuses)

        best = ranked[0] if ranked else None
        best_id = best.id if best else None

        ts = TrajectorySet(
            task_id=task_id,
            trajectories=ranked,
            best_id=best_id,
            hitl_timeout_sec=hitl_timeout_sec,
        )
        logger.info(
            f"[TrajectoryGenerator] Generated {len(ranked)} trajectories "
            f"for task {task_id}, best={best_id} (score={best.score:.3f})"
        )
        return ts

    def generate_single(
        self,
        task_id: str,
        target_pose: list[float],
        strategy: TrajectoryStrategy = TrajectoryStrategy.OPTIMAL,
        start_joint_state: Optional[list[float]] = None,
    ) -> Optional[Trajectory]:
        """Generate a single trajectory with a specific strategy."""
        return self._plan_one(task_id, strategy, target_pose, start_joint_state)

    # ── Internal ───────────────────────────────────────────────────────────

    def _plan_one(
        self,
        task_id: str,
        strategy: TrajectoryStrategy,
        target_pose: list[float],
        start_joint_state: Optional[list[float]] = None,
        scene_context: Optional[dict] = None,
    ) -> Optional[Trajectory]:
        """Plan one trajectory using the given strategy."""
        strategy_name = _STRATEGY_MAP[strategy]
        cfg = get_strategy_config(strategy_name)

        req = PlanningRequest(
            target_pose=target_pose,
            is_joint_space=False,
            max_velocity_scale=cfg.max_velocity_scale,
            max_acceleration_scale=cfg.max_acceleration_scale,
            clearance_m=cfg.clearance_m,
            planning_time_sec=cfg.planning_time_sec,
            max_attempts=cfg.max_planning_attempts,
            start_joint_state=start_joint_state,
        )

        result = self._moveit.plan_to_pose(req)
        if not result.success:
            logger.warning(
                f"[TrajectoryGenerator] Planning failed for {strategy.value}: "
                f"{result.status.value}"
            )
            return None

        # Convert planning result → domain Trajectory
        waypoints = self._result_to_waypoints(result)

        traj = Trajectory(
            strategy=strategy,
            waypoints=waypoints,
            collision_free=True,  # MoveIt guarantees if success
            duration_sec=len(waypoints) * 0.02,  # ~50 Hz waypoint rate
            path_length_m=result.path_length_m,
            color_hint=cfg.color_hint,
            label=cfg.label,
        )
        return traj

    @staticmethod
    def _result_to_waypoints(result: PlanningResult) -> list[Waypoint]:
        """Convert PlanningResult trajectory list to Waypoint objects."""
        if result.trajectory is None:
            return []

        waypoints: list[Waypoint] = []
        for i, jp in enumerate(result.trajectory):
            waypoints.append(Waypoint(
                pose=Pose6D(),   # Joint-space, no Cartesian pose
                joint_state=None,
                time_from_start_sec=i * 0.02,
                velocity_scale=1.0,
                is_blend_point=(i < len(result.trajectory) - 1),
            ))
        return waypoints

    @staticmethod
    def _build_bonus_map(trajectories: list[Trajectory]) -> dict[str, float]:
        """Build strategy → base_score_boost mapping."""
        bonus_map: dict[str, float] = {}
        for t in trajectories:
            strategy_name = _STRATEGY_MAP.get(t.strategy)
            if strategy_name:
                cfg = get_strategy_config(strategy_name)
                bonus_map[t.strategy.value] = cfg.base_score_boost
        return bonus_map

    def _emergency_stub(self, task_id: str, target_pose: list[float]) -> Trajectory:
        """Emergency fallback trajectory when all strategies fail."""
        req = PlanningRequest(target_pose=target_pose)
        result = self._moveit.plan_to_pose(req)
        waypoints = self._result_to_waypoints(result)
        cfg = get_strategy_config(StrategyName.OPTIMAL)
        return Trajectory(
            strategy=TrajectoryStrategy.OPTIMAL,
            waypoints=waypoints,
            duration_sec=len(waypoints) * 0.02,
            path_length_m=result.path_length_m,
            color_hint=cfg.color_hint,
            label="应急路径（Fallback）",
        )


# ── Default instance ───────────────────────────────────────────────────────

_default_generator: Optional[TrajectoryGenerator] = None


def get_trajectory_generator() -> TrajectoryGenerator:
    global _default_generator
    if _default_generator is None:
        _default_generator = TrajectoryGenerator()
    return _default_generator
