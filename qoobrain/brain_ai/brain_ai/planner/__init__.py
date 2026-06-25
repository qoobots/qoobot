"""
brain_ai/planner — Motion planning and HITL trajectory selection.

Modules:
  - moveit_client:      MoveIt2 gRPC client (stub fallback)
  - trajectory_gen:     Multi-strategy trajectory generator
  - scorer:             Multi-criteria trajectory scoring engine
  - hitl_manager:       Human-in-the-loop selection manager
  - bt_composer:        Behavior tree composer/validator
  - plan_builder:       End-to-end plan assembly pipeline
  - strategy_enum:      Strategy parameter presets
  - strategies:         Pluggable trajectory strategies
"""

from brain_ai.planner.moveit_client import MoveItClient, PlanningRequest, PlanningResult, get_moveit_client
from brain_ai.planner.trajectory_gen import TrajectoryGenerator, get_trajectory_generator
from brain_ai.planner.scorer import TrajectoryScorer, ScoringWeights, get_scorer
from brain_ai.planner.hitl_manager import HITLManager, HITLResult, HITLState
from brain_ai.planner.bt_composer import BTComposer, get_bt_composer
from brain_ai.planner.plan_builder import PlanBuilder
from brain_ai.planner.strategy_enum import StrategyConfig, StrategyName, get_strategy_config

__all__ = [
    "MoveItClient",
    "PlanningRequest",
    "PlanningResult",
    "get_moveit_client",
    "TrajectoryGenerator",
    "get_trajectory_generator",
    "TrajectoryScorer",
    "ScoringWeights",
    "get_scorer",
    "HITLManager",
    "HITLResult",
    "HITLState",
    "BTComposer",
    "get_bt_composer",
    "PlanBuilder",
    "StrategyConfig",
    "StrategyName",
    "get_strategy_config",
]
