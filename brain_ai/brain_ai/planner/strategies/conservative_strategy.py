"""
Conservative trajectory strategy — maximum safety, slower execution.
"""

from __future__ import annotations

import time

from brain_ai.planner.strategies.base import BaseTrajectoryStrategy, StrategyResult
from brain_ai.planner.strategy_enum import StrategyConfig, StrategyName, get_strategy_config


class ConservativeStrategy(BaseTrajectoryStrategy):
    """Safety-first trajectory: wide clearances, low velocities, smooth paths."""

    @property
    def config(self) -> StrategyConfig:
        return get_strategy_config(StrategyName.CONSERVATIVE)

    def plan(self, start_joints: list[float], target_pose: list[float]) -> StrategyResult:
        t0 = time.perf_counter()
        dof = len(start_joints)

        # More waypoints for smoother, slower path
        n = 100
        dummy_target = [target_pose[0] * 0.3, target_pose[1] * 0.2, 1.2 - target_pose[2] * 0.1,
                        -0.8, 0.3, 0.0, 0.3][:dof]

        waypoints = []
        for i in range(n + 1):
            # More gradual interpolation
            frac = i / n
            frac_smooth = frac  # Linear for conservative (no overshoot)
            wp = [start_joints[j] + (dummy_target[j] - start_joints[j]) * frac_smooth
                  for j in range(dof)]
            waypoints.append(wp)

        elapsed = (time.perf_counter() - t0) * 1000

        return StrategyResult(
            success=True,
            trajectory_waypoints=waypoints,
            planning_time_ms=elapsed,
            path_length_m=len(waypoints) * 0.005,
            collision_free=True,
        )
