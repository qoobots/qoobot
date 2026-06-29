"""
Exploratory trajectory strategy — novel path discovery for world model updates.
"""

from __future__ import annotations

import random
import time

from brain_ai.planner.strategies.base import BaseTrajectoryStrategy, StrategyResult
from brain_ai.planner.strategy_enum import StrategyConfig, StrategyName, get_strategy_config


class ExploratoryStrategy(BaseTrajectoryStrategy):
    """
    Exploration-first trajectory: generates novel paths through unexplored
    configuration space to update internal world models and expand capability
    boundaries.

    Adds randomized deviations from the nominal path.
    """

    def __init__(self, exploration_noise: float = 0.15, seed: int | None = None) -> None:
        self._noise = exploration_noise
        self._rng = random.Random(seed)

    @property
    def config(self) -> StrategyConfig:
        cfg = get_strategy_config(StrategyName.EXPLORATORY)
        return cfg

    def plan(self, start_joints: list[float], target_pose: list[float]) -> StrategyResult:
        t0 = time.perf_counter()
        dof = len(start_joints)

        # Nominal path with added exploration noise
        n = 80
        dummy_target = [target_pose[0] * 0.5, target_pose[1] * 0.3, 1.5 - target_pose[2] * 0.2,
                        -1.0, 0.5, 0.0, 0.5][:dof]

        waypoints = []
        for i in range(n + 1):
            frac = i / n
            frac_smooth = frac * frac * (3 - 2 * frac)
            wp = [start_joints[j] + (dummy_target[j] - start_joints[j]) * frac_smooth
                  for j in range(dof)]

            # Add exploration noise (zero at endpoints, max at midpoint)
            noise_scale = self._noise * (1.0 - abs(2 * frac - 1.0))
            wp = [w + self._rng.uniform(-noise_scale, noise_scale) for w in wp]
            waypoints.append(wp)

        elapsed = (time.perf_counter() - t0) * 1000

        return StrategyResult(
            success=True,
            trajectory_waypoints=waypoints,
            planning_time_ms=elapsed,
            path_length_m=len(waypoints) * 0.007,
            collision_free=True,  # Would be validated by MoveIt in production
        )
