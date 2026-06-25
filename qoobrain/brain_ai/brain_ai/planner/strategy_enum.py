"""
brain_ai/planner/strategy_enum.py — Trajectory generation strategy configuration.

Each strategy defines the parameters passed to MoveIt2 for motion planning:
  - velocity / acceleration scaling
  - safety margin (clearance)
  - planning time budget
  - whether to allow replanning mid-trajectory
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class StrategyName(str, Enum):
    OPTIMAL      = "OPTIMAL"       # Shortest + fastest
    CONSERVATIVE = "CONSERVATIVE"  # Maximum safety margins
    AGGRESSIVE   = "AGGRESSIVE"    # Speed-optimized, tight margins
    EXPLORATORY  = "EXPLORATORY"   # Novel path discovery
    ADVERSARIAL  = "ADVERSARIAL"   # Worst-case stress testing


@dataclass
class StrategyConfig:
    """Per-strategy MoveIt2 planning parameters."""
    name: StrategyName
    label: str                      # Human-readable label
    color_hint: str                 # Ghost trail color in 3D viz
    description: str

    # Motion planning knobs
    max_velocity_scale: float       # 0.0–1.0, fraction of joint limits
    max_acceleration_scale: float   # 0.0–1.0
    clearance_m: float              # Minimum obstacle clearance (m)
    planning_time_sec: float        # Max planning time budget
    max_planning_attempts: int      # Retries with different seeds
    allow_replan: bool              # Allow mid-trajectory replanning
    smoothness_weight: float        # 0.0 (no smoothing) → 1.0 (max smoothing)

    # Scoring
    base_score_boost: float         # Base score modifier for this strategy


# ── Built-in strategy presets ──────────────────────────────────────────────

STRATEGY_PRESETS: dict[StrategyName, StrategyConfig] = {
    StrategyName.OPTIMAL: StrategyConfig(
        name=StrategyName.OPTIMAL,
        label="最优路径",
        color_hint="#00ccff",
        description="综合评分最优：平衡速度与安全",
        max_velocity_scale=0.8,
        max_acceleration_scale=0.6,
        clearance_m=0.05,
        planning_time_sec=3.0,
        max_planning_attempts=3,
        allow_replan=True,
        smoothness_weight=0.5,
        base_score_boost=0.0,
    ),
    StrategyName.CONSERVATIVE: StrategyConfig(
        name=StrategyName.CONSERVATIVE,
        label="安全优先",
        color_hint="#00ff88",
        description="宽安全边界：适合高价值或脆弱操作",
        max_velocity_scale=0.3,
        max_acceleration_scale=0.2,
        clearance_m=0.15,
        planning_time_sec=5.0,
        max_planning_attempts=5,
        allow_replan=True,
        smoothness_weight=0.8,
        base_score_boost=-0.1,
    ),
    StrategyName.AGGRESSIVE: StrategyConfig(
        name=StrategyName.AGGRESSIVE,
        label="快速执行",
        color_hint="#ff6600",
        description="速度优先：更快的周期时间，更紧的安全边界",
        max_velocity_scale=1.0,
        max_acceleration_scale=0.9,
        clearance_m=0.02,
        planning_time_sec=1.5,
        max_planning_attempts=2,
        allow_replan=False,
        smoothness_weight=0.2,
        base_score_boost=0.05,
    ),
    StrategyName.EXPLORATORY: StrategyConfig(
        name=StrategyName.EXPLORATORY,
        label="探索路径",
        color_hint="#ff00ff",
        description="尝试新路径：用于更新内部世界模型和扩展能力边界的探索性运动",
        max_velocity_scale=0.5,
        max_acceleration_scale=0.3,
        clearance_m=0.10,
        planning_time_sec=8.0,
        max_planning_attempts=10,
        allow_replan=True,
        smoothness_weight=0.3,
        base_score_boost=-0.2,
    ),
    StrategyName.ADVERSARIAL: StrategyConfig(
        name=StrategyName.ADVERSARIAL,
        label="压力测试",
        color_hint="#ff0000",
        description="最坏情况：极端边界条件下生成轨迹，用于安全验证",
        max_velocity_scale=1.0,
        max_acceleration_scale=1.0,
        clearance_m=0.005,
        planning_time_sec=10.0,
        max_planning_attempts=20,
        allow_replan=False,
        smoothness_weight=0.0,
        base_score_boost=-0.5,
    ),
}


def get_strategy_config(name: StrategyName | str) -> StrategyConfig:
    """Look up a strategy config by name (case-insensitive)."""
    if isinstance(name, str):
        name = StrategyName(name.upper())
    if name not in STRATEGY_PRESETS:
        raise KeyError(
            f"Unknown strategy {name!r}. Available: "
            f"{[s.value for s in StrategyName]}"
        )
    return STRATEGY_PRESETS[name]
