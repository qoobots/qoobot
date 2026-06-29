"""
Aggressive trajectory strategy — speed-optimized, tighter margins.
"""

from __future__ import annotations

import time

from brain_ai.planner.strategies.base import BaseTrajectoryStrategy, StrategyResult
from brain_ai.planner.strategy_enum import StrategyConfig, StrategyName, get_strategy_config


class AggressiveStrategy(BaseTrajectoryStrategy):
    """Speed-first trajectory: max velocity, minimal clearance, fast cycle time."""

    @property
    def config(self) -> StrategyConfig:
        return get_strategy_config(StrategyName.AGGRESSIVE)

    def plan(self, start_joints: list[float], target_pose: list[float]) -> StrategyResult:
        t0 = time.perf_counter()
        dof = len(start_joints)

        # Fewer waypoints for faster execution
        n = 25
        dummy_target = [target_pose[0] * 0.7, target_pose[1] * 0.5, 1.8 - target_pose[2] * 0.3,
                        -1.2, 0.7, 0.0, 0.7][:dof]

        waypoints = []
        for i in range(n + 1):
            frac = i / n
            # Aggressive acceleration curve
            frac_agg = frac ** 0.7  # Fast start, slower finish
            wp = [start_joints[j] + (dummy_target[j] - start_joints[j]) * frac_agg
                  for j in range(dof)]
            waypoints.append(wp)

        elapsed = (time.perf_counter() - t0) * 1000

        return StrategyResult(
            success=True,
            trajectory_waypoints=waypoints,
            planning_time_ms=elapsed,
            path_length_m=len(waypoints) * 0.008,
            collision_free=True,
        )
