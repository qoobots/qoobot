"""
brain_ai/planner/strategies/base.py — Abstract base for trajectory strategies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from brain_ai.planner.strategy_enum import StrategyConfig, StrategyName


@dataclass
class StrategyResult:
    """Output of a strategy's planning attempt."""
    success: bool
    trajectory_waypoints: list[list[float]] | None = None
    planning_time_ms: float = 0.0
    path_length_m: float = 0.0
    collision_free: bool = False
    error_message: str = ""


class BaseTrajectoryStrategy(ABC):
    """Abstract base class for trajectory generation strategies."""

    @property
    @abstractmethod
    def config(self) -> StrategyConfig:
        """Return the strategy's parameter configuration."""
        ...

    @property
    def name(self) -> StrategyName:
        return self.config.name

    @abstractmethod
    def plan(self, start_joints: list[float], target_pose: list[float]) -> StrategyResult:
        """
        Generate a trajectory from start to target.

        Args:
            start_joints: Current joint positions [j1, j2, ..., jN]
            target_pose:  Target end-effector pose [x, y, z, qx, qy, qz, qw]

        Returns:
            StrategyResult with waypoints and metadata
        """
        ...
