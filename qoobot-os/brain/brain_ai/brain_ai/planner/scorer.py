"""
brain_ai/planner/scorer.py — Multi-criteria trajectory scoring engine.

Scores candidate trajectories across weighted criteria:
  - Path efficiency (shorter = better)
  - Execution speed (faster = better)
  - Collision safety
  - Manipulability (kinematic dexterity)
  - Joint effort (lower torque = better)
  - Smoothness (less jerk = better)

Each criterion → 0.0–1.0, then weighted sum → composite 0.0–1.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Optional

from brain_ai.domain.motion import Trajectory


@dataclass
class ScoringWeights:
    """Configurable criterion weights (sum should ≈ 1.0)."""
    path_length:      float = 0.20
    duration:         float = 0.15
    collision_safety: float = 0.20
    manipulability:   float = 0.15
    joint_effort:     float = 0.15
    smoothness:       float = 0.10
    strategy_bonus:   float = 0.05   # From StrategyConfig.base_score_boost

    def validate(self) -> bool:
        total = sum([
            self.path_length, self.duration, self.collision_safety,
            self.manipulability, self.joint_effort, self.smoothness,
            self.strategy_bonus,
        ])
        return abs(total - 1.0) < 0.05


@dataclass
class CriterionScores:
    """Per-criterion breakdown for one trajectory."""
    path_length_score:      float = 0.0
    duration_score:         float = 0.0
    collision_safety_score: float = 0.0
    manipulability_score:   float = 0.0
    joint_effort_score:     float = 0.0
    smoothness_score:       float = 0.0
    strategy_bonus:         float = 0.0
    composite:              float = 0.0

    def to_dict(self) -> dict:
        return {
            "path_length": round(self.path_length_score, 4),
            "duration": round(self.duration_score, 4),
            "collision_safety": round(self.collision_safety_score, 4),
            "manipulability": round(self.manipulability_score, 4),
            "joint_effort": round(self.joint_effort_score, 4),
            "smoothness": round(self.smoothness_score, 4),
            "strategy_bonus": round(self.strategy_bonus, 4),
            "composite": round(self.composite, 4),
        }


class TrajectoryScorer:
    """
    Score and rank a batch of candidate trajectories.

    Usage:
        scorer = TrajectoryScorer(weights=ScoringWeights(...))
        rankings = scorer.rank(trajectories)
        best = rankings[0]  # highest composite score
    """

    def __init__(self, weights: Optional[ScoringWeights] = None) -> None:
        self.weights = weights or ScoringWeights()

    # ── Public API ─────────────────────────────────────────────────────────

    def score(self, traj: Trajectory, strategy_bonus: float = 0.0) -> CriterionScores:
        """Score a single trajectory and populate traj.score."""
        w = self.weights

        # 1. Path length: shorter = higher score
        path_score = self._linear_score(traj.path_length_m, max_val=5.0, invert=True)

        # 2. Duration: shorter = higher score
        dur_score = self._linear_score(traj.duration_sec, max_val=30.0, invert=True)

        # 3. Collision safety: collision_free → 1.0, else 0.0
        coll_score = 1.0 if traj.collision_free else 0.0

        # 4. Manipulability: higher = better (typical range 0.01–0.5)
        manip_score = min(traj.manipulability / 0.3, 1.0)

        # 5. Joint effort: lower = better (RMS torque)
        effort_score = self._linear_score(traj.joint_effort_rms, max_val=50.0, invert=True)

        # 6. Smoothness: compute from waypoint derivatives (jerk proxy)
        smooth_score = self._compute_smoothness(traj)

        # Composite
        composite = (
            w.path_length      * path_score
            + w.duration       * dur_score
            + w.collision_safety * coll_score
            + w.manipulability * manip_score
            + w.joint_effort   * effort_score
            + w.smoothness     * smooth_score
            + w.strategy_bonus * strategy_bonus
        )

        # Normalize to [0, 1]
        composite = max(0.0, min(1.0, composite))

        # Store on trajectory
        traj.score = composite

        return CriterionScores(
            path_length_score=path_score,
            duration_score=dur_score,
            collision_safety_score=coll_score,
            manipulability_score=manip_score,
            joint_effort_score=effort_score,
            smoothness_score=smooth_score,
            strategy_bonus=strategy_bonus,
            composite=composite,
        )

    def rank(self, trajectories: list[Trajectory], strategy_bonus_map: Optional[dict[str, float]] = None) -> list[Trajectory]:
        """Score and rank trajectories by composite score (descending)."""
        bonus_map = strategy_bonus_map or {}
        for t in trajectories:
            bonus = bonus_map.get(t.strategy.value, 0.0)
            self.score(t, strategy_bonus=bonus)
        return sorted(trajectories, key=lambda t: t.score, reverse=True)

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    def _linear_score(value: float, max_val: float, invert: bool = False) -> float:
        """Map value → [0, 1] with optional inversion."""
        if max_val <= 0:
            return 1.0
        v = value / max_val
        v = max(0.0, min(1.0, v))
        return 1.0 - v if invert else v

    @staticmethod
    def _compute_smoothness(traj: Trajectory) -> float:
        """
        Compute smoothness from waypoint velocity derivatives.
        Lower total acceleration (jerk proxy) → higher smoothness score.
        """
        wp = traj.waypoints
        if len(wp) < 3:
            return 1.0  # Too few points, assume smooth

        # Second-order difference of time_from_start
        total_accel = 0.0
        count = 0
        for i in range(1, len(wp) - 1):
            dt1 = wp[i].time_from_start_sec - wp[i - 1].time_from_start_sec or 0.01
            dt2 = wp[i + 1].time_from_start_sec - wp[i].time_from_start_sec or 0.01
            v1 = wp[i].velocity_scale / dt1
            v2 = wp[i + 1].velocity_scale / dt2
            total_accel += abs(v2 - v1)
            count += 1

        if count == 0:
            return 1.0

        avg_accel = total_accel / count
        # Normalize: accelerations > 10 rad/s^2 are "jittery"
        return max(0.0, 1.0 - avg_accel / 10.0)

    # ── Ranking utilities ──────────────────────────────────────────────────

    @staticmethod
    def best(trajectories: list[Trajectory]) -> Optional[Trajectory]:
        """Return highest-scoring trajectory."""
        if not trajectories:
            return None
        return max(trajectories, key=lambda t: t.score)


# ── Default instance ───────────────────────────────────────────────────────

_default_scorer: Optional[TrajectoryScorer] = None


def get_scorer() -> TrajectoryScorer:
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = TrajectoryScorer()
    return _default_scorer
