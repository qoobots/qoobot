"""
Strategies package — trajectory generation strategies.

Each strategy inherits from BaseTrajectoryStrategy and defines planning
parameters that are passed to MoveIt2.
"""

from brain_ai.planner.strategies.base import BaseTrajectoryStrategy
from brain_ai.planner.strategies.optimal_strategy import OptimalStrategy
from brain_ai.planner.strategies.conservative_strategy import ConservativeStrategy
from brain_ai.planner.strategies.aggressive_strategy import AggressiveStrategy
from brain_ai.planner.strategies.exploratory_strategy import ExploratoryStrategy
from brain_ai.planner.strategies.adversarial_strategy import AdversarialStrategy

from brain_ai.planner.strategy_enum import StrategyName


# Strategy registry: all available strategies keyed by name
STRATEGY_REGISTRY: dict[StrategyName, type[BaseTrajectoryStrategy]] = {
    StrategyName.OPTIMAL:      OptimalStrategy,
    StrategyName.CONSERVATIVE: ConservativeStrategy,
    StrategyName.AGGRESSIVE:   AggressiveStrategy,
    StrategyName.EXPLORATORY:  ExploratoryStrategy,
    StrategyName.ADVERSARIAL:  AdversarialStrategy,
}


def create_strategy(name: StrategyName) -> BaseTrajectoryStrategy:
    """Factory: instantiate a strategy by name."""
    cls = STRATEGY_REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Unknown strategy: {name}")
    return cls()


__all__ = [
    "BaseTrajectoryStrategy",
    "OptimalStrategy",
    "ConservativeStrategy",
    "AggressiveStrategy",
    "ExploratoryStrategy",
    "AdversarialStrategy",
    "STRATEGY_REGISTRY",
    "create_strategy",
]
