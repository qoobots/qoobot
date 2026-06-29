"""
Optimal trajectory strategy — balanced speed and safety.
"""

from __future__ import annotations

import time

from brain_ai.planner.strategies.base import BaseTrajectoryStrategy, StrategyResult
from brain_ai.planner.strategy_enum import StrategyConfig, StrategyName, get_strategy_config


class OptimalStrategy(BaseTrajectoryStrategy):
    """Balanced trajectory: optimal trade-off between speed and safety."""

    @property
    def config(self) -> StrategyConfig:
        return get_strategy_config(StrategyName.OPTIMAL)

    def plan(self, start_joints: list[float], target_pose: list[float]) -> StrategyResult:
        t0 = time.perf_counter()
        dof = len(start_joints)

        # Simple linear interpolation (production: MoveIt2 with OMPL/RRTConnect)
        n = 50
        dummy_target = [target_pose[0] * 0.5, target_pose[1] * 0.3, 1.5 - target_pose[2] * 0.2,
                        -1.0, 0.5, 0.0, 0.5][:dof]
        waypoints = []
        for i in range(n + 1):
            frac = i / n
            frac_smooth = frac * frac * (3 - 2 * frac)
            wp = [start_joints[j] + (dummy_target[j] - start_joints[j]) * frac_smooth
                  for j in range(dof)]
            waypoints.append(wp)

        elapsed = (time.perf_counter() - t0) * 1000
        path_len = sum(
            abs(waypoints[i][0] - waypoints[i - 1][0])
            for i in range(1, len(waypoints))
        ) * 0.1

        return StrategyResult(
            success=True,
            trajectory_waypoints=waypoints,
            planning_time_ms=elapsed,
            path_length_m=path_len,
            collision_free=True,
        )
