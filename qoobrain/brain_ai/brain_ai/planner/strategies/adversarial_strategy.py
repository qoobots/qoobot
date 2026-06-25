"""
Adversarial trajectory strategy — worst-case stress testing.

Generates trajectories at extreme joint limits, with random perturbations
to discover edge cases and safety boundary violations.
"""

from __future__ import annotations

import random
import time

from brain_ai.planner.strategies.base import BaseTrajectoryStrategy, StrategyResult
from brain_ai.planner.strategy_enum import StrategyConfig, StrategyName, get_strategy_config


class AdversarialStrategy(BaseTrajectoryStrategy):
    """
    Worst-case trajectory for safety testing and robustness validation.

    Pushes joints to extreme positions, introduces discontinuities,
    and tests the system's ability to handle edge cases.
    """

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    @property
    def config(self) -> StrategyConfig:
        return get_strategy_config(StrategyName.ADVERSARIAL)

    def plan(self, start_joints: list[float], target_pose: list[float]) -> StrategyResult:
        t0 = time.perf_counter()
        dof = len(start_joints)

        # Extreme target: push joints near limits
        extreme_target = [start_joints[j] * 1.5 + self._rng.uniform(-0.8, 0.8)
                         for j in range(dof)]

        # Fewer waypoints with larger steps (stress tests velocity limits)
        n = 15
        waypoints = []
        for i in range(n + 1):
            frac = i / n
            # Non-smooth interpolation to test jerk handling
            wp = [start_joints[j] + (extreme_target[j] - start_joints[j]) * frac
                  for j in range(dof)]

            # Add adversarial perturbations
            if i > 0 and i < n:
                wp = [w + self._rng.uniform(-0.1, 0.1) for w in wp]
            waypoints.append(wp)

        elapsed = (time.perf_counter() - t0) * 1000

        return StrategyResult(
            success=True,
            trajectory_waypoints=waypoints,
            planning_time_ms=elapsed,
            path_length_m=len(waypoints) * 0.015,
            collision_free=False,  # May collide in adversarial mode
        )
