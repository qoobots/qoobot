"""
qoodev human preference labeling — multi-trajectory ranking and RLHF feedback collection.

对标：OpenAI RLHF pipeline + Anthropic Constitutional AI
提供多轨迹排序、偏好反馈收集、奖励模型训练数据导出。
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PreferenceStrength(str, Enum):
    STRONGLY_PREFER_A = "strongly_prefer_a"
    PREFER_A = "prefer_a"
    NEUTRAL = "neutral"
    PREFER_B = "prefer_b"
    STRONGLY_PREFER_B = "strongly_prefer_b"


class FeedbackDimension(str, Enum):
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    SMOOTHNESS = "smoothness"
    TASK_SUCCESS = "task_success"
    NATURALNESS = "naturalness"
    GENERAL_QUALITY = "general_quality"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TrajectorySample:
    """A single trajectory to be ranked."""
    id: str
    data: np.ndarray  # shape (T, dim)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_model: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")


@dataclass
class PairwiseComparison:
    """A single A vs B comparison with preference."""
    trajectory_a: str  # id
    trajectory_b: str
    preference: PreferenceStrength
    dimension: FeedbackDimension = FeedbackDimension.GENERAL_QUALITY
    annotator_id: str = "unknown"
    notes: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")

    @property
    def reward_signal(self) -> float:
        """Convert preference to scalar reward signal for RLHF."""
        mapping = {
            PreferenceStrength.STRONGLY_PREFER_A: -1.0,
            PreferenceStrength.PREFER_A: -0.5,
            PreferenceStrength.NEUTRAL: 0.0,
            PreferenceStrength.PREFER_B: 0.5,
            PreferenceStrength.STRONGLY_PREFER_B: 1.0,
        }
        return mapping[self.preference]


@dataclass
class RankingSession:
    """A multi-trajectory ranking session."""
    session_id: str
    task_description: str = ""
    trajectories: List[str] = field(default_factory=list)  # ordered IDs (best first)
    comparisons: List[PairwiseComparison] = field(default_factory=list)
    annotator_id: str = "unknown"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# PreferenceCollector
# ---------------------------------------------------------------------------

class PreferenceCollector:
    """Collect human preference data for RLHF training.

    Usage::

        collector = PreferenceCollector()
        collector.add_trajectory(traj_a)
        collector.add_trajectory(traj_b)
        comparison = collector.compare("traj_001", "traj_002", PreferenceStrength.PREFER_A)
        rlhf_data = collector.export_rlhf_dataset()
    """

    def __init__(self):
        self._trajectories: Dict[str, TrajectorySample] = {}
        self._comparisons: List[PairwiseComparison] = []
        self._ranking_sessions: List[RankingSession] = []
        self._dimension_scores: Dict[str, Dict[FeedbackDimension, float]] = defaultdict(dict)

    # -- trajectory management -----------------------------------------------

    def add_trajectory(self, trajectory: TrajectorySample) -> None:
        self._trajectories[trajectory.id] = trajectory

    def add_trajectories(self, trajectories: List[TrajectorySample]) -> None:
        for t in trajectories:
            self.add_trajectory(t)

    def get_trajectory(self, trajectory_id: str) -> Optional[TrajectorySample]:
        return self._trajectories.get(trajectory_id)

    def remove_trajectory(self, trajectory_id: str) -> None:
        self._trajectories.pop(trajectory_id, None)

    # -- pairwise comparison -------------------------------------------------

    def compare(
        self,
        trajectory_a_id: str,
        trajectory_b_id: str,
        preference: PreferenceStrength,
        dimension: FeedbackDimension = FeedbackDimension.GENERAL_QUALITY,
        annotator_id: str = "unknown",
        notes: str = "",
    ) -> PairwiseComparison:
        comparison = PairwiseComparison(
            trajectory_a=trajectory_a_id,
            trajectory_b=trajectory_b_id,
            preference=preference,
            dimension=dimension,
            annotator_id=annotator_id,
            notes=notes,
        )
        self._comparisons.append(comparison)
        return comparison

    def batch_compare(
        self,
        pairs: List[Tuple[str, str, PreferenceStrength]],
        dimension: FeedbackDimension = FeedbackDimension.GENERAL_QUALITY,
        annotator_id: str = "unknown",
    ) -> List[PairwiseComparison]:
        results = []
        for a_id, b_id, pref in pairs:
            results.append(self.compare(a_id, b_id, pref, dimension, annotator_id))
        return results

    # -- multi-trajectory ranking --------------------------------------------

    def rank_trajectories(
        self,
        trajectory_ids: List[str],
        task_description: str = "",
        annotator_id: str = "unknown",
    ) -> RankingSession:
        """Record a full ranking of trajectories (best → worst)."""
        session = RankingSession(
            session_id=f"rank_{len(self._ranking_sessions):04d}",
            task_description=task_description,
            trajectories=list(trajectory_ids),
            annotator_id=annotator_id,
        )

        # automatically generate pairwise comparisons from ranking
        n = len(trajectory_ids)
        for i in range(n):
            for j in range(i + 1, n):
                # trajectory_ids[i] is preferred over trajectory_ids[j]
                session.comparisons.append(PairwiseComparison(
                    trajectory_a=trajectory_ids[j],  # worse
                    trajectory_b=trajectory_ids[i],  # better
                    preference=PreferenceStrength.STRONGLY_PREFER_B,
                    annotator_id=annotator_id,
                ))

        self._comparisons.extend(session.comparisons)
        self._ranking_sessions.append(session)
        return session

    # -- dimension scoring ---------------------------------------------------

    def score_dimension(
        self,
        trajectory_id: str,
        dimension: FeedbackDimension,
        score: float,
    ) -> None:
        """Rate a trajectory on a specific feedback dimension (1–5)."""
        self._dimension_scores[trajectory_id][dimension] = max(1.0, min(5.0, score))

    # -- export --------------------------------------------------------------

    def export_rlhf_dataset(self) -> Dict[str, Any]:
        """Export data in standard RLHF format (compatible with TRL/OpenRLHF)."""
        dataset: Dict[str, List[Any]] = {
            "chosen": [],
            "rejected": [],
            "metadata": [],
        }

        for comp in self._comparisons:
            if comp.preference in (PreferenceStrength.NEUTRAL,):
                continue

            traj_a = self._trajectories.get(comp.trajectory_a)
            traj_b = self._trajectories.get(comp.trajectory_b)

            if traj_a is None or traj_b is None:
                continue

            if comp.preference in (PreferenceStrength.PREFER_B, PreferenceStrength.STRONGLY_PREFER_B):
                chosen, rejected = traj_b, traj_a
            else:
                chosen, rejected = traj_a, traj_b

            dataset["chosen"].append({
                "trajectory_id": chosen.id,
                "data": chosen.data.tolist(),
                "source_model": chosen.source_model,
            })
            dataset["rejected"].append({
                "trajectory_id": rejected.id,
                "data": rejected.data.tolist(),
                "source_model": rejected.source_model,
            })
            dataset["metadata"].append({
                "dimension": comp.dimension.value,
                "preference": comp.preference.value,
                "annotator_id": comp.annotator_id,
                "timestamp": comp.timestamp,
                "notes": comp.notes,
            })

        return dataset

    def export_ranking_data(self) -> List[Dict[str, Any]]:
        """Export ranking sessions for Elo/Bradley-Terry modeling."""
        data = []
        for session in self._ranking_sessions:
            data.append({
                "session_id": session.session_id,
                "task_description": session.task_description,
                "ranking": session.trajectories,
                "n_comparisons": len(session.comparisons),
                "annotator_id": session.annotator_id,
                "timestamp": session.timestamp,
            })
        return data

    def save(self, path: Path) -> None:
        """Persist all collected data to JSON."""
        data = {
            "trajectories": {
                tid: {
                    "id": t.id,
                    "metadata": t.metadata,
                    "source_model": t.source_model,
                    "timestamp": t.timestamp,
                    "data_shape": list(t.data.shape),
                    "data_summary": {
                        "mean": float(t.data.mean()),
                        "std": float(t.data.std()),
                        "min": float(t.data.min()),
                        "max": float(t.data.max()),
                    },
                }
                for tid, t in self._trajectories.items()
            },
            "comparisons": [
                {
                    "trajectory_a": c.trajectory_a,
                    "trajectory_b": c.trajectory_b,
                    "preference": c.preference.value,
                    "dimension": c.dimension.value,
                    "annotator_id": c.annotator_id,
                    "notes": c.notes,
                    "timestamp": c.timestamp,
                }
                for c in self._comparisons
            ],
            "ranking_sessions": [
                {
                    "session_id": s.session_id,
                    "task_description": s.task_description,
                    "trajectories": s.trajectories,
                    "annotator_id": s.annotator_id,
                    "timestamp": s.timestamp,
                }
                for s in self._ranking_sessions
            ],
            "dimension_scores": {
                tid: {dim.value: score for dim, score in scores.items()}
                for tid, scores in self._dimension_scores.items()
            },
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # -- statistics ----------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Compute annotation statistics."""
        annotator_counts: Dict[str, int] = defaultdict(int)
        dimension_counts: Dict[str, int] = defaultdict(int)
        preference_distribution: Dict[str, int] = defaultdict(int)

        for comp in self._comparisons:
            annotator_counts[comp.annotator_id] += 1
            dimension_counts[comp.dimension.value] += 1
            preference_distribution[comp.preference.value] += 1

        # inter-annotator agreement (for pairs with multiple annotations)
        pair_annotations: Dict[Tuple[str, str], List[PreferenceStrength]] = defaultdict(list)
        for comp in self._comparisons:
            pair_annotations[(comp.trajectory_a, comp.trajectory_b)].append(comp.preference)

        agreement_count = 0
        total_pairs = 0
        for prefs in pair_annotations.values():
            if len(prefs) > 1:
                total_pairs += 1
                if len(set(prefs)) == 1:
                    agreement_count += 1

        return {
            "total_comparisons": len(self._comparisons),
            "total_trajectories": len(self._trajectories),
            "total_ranking_sessions": len(self._ranking_sessions),
            "annotator_counts": dict(annotator_counts),
            "dimension_counts": dict(dimension_counts),
            "preference_distribution": preference_distribution,
            "inter_annotator_agreement": agreement_count / total_pairs if total_pairs > 0 else None,
        }


# ---------------------------------------------------------------------------
# Reward model training helpers
# ---------------------------------------------------------------------------

def bradley_terry_probability(score_a: float, score_b: float) -> float:
    """Probability that A is preferred over B under Bradley-Terry model."""
    return 1.0 / (1.0 + np.exp(score_b - score_a))


def bradley_terry_loss(
    chosen_scores: np.ndarray,
    rejected_scores: np.ndarray,
) -> float:
    """Negative log-likelihood loss for Bradley-Terry preference model."""
    diff = chosen_scores - rejected_scores
    return float(-np.mean(np.log(1.0 / (1.0 + np.exp(-diff)))))


def compute_elo_ratings(
    comparisons: List[PairwiseComparison],
    initial_rating: float = 1500.0,
    k_factor: float = 32.0,
) -> Dict[str, float]:
    """Compute Elo ratings from pairwise comparisons."""
    ratings: Dict[str, float] = defaultdict(lambda: initial_rating)

    for comp in comparisons:
        ra = ratings[comp.trajectory_a]
        rb = ratings[comp.trajectory_b]

        ea = 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
        eb = 1.0 / (1.0 + 10.0 ** ((ra - rb) / 400.0))

        if comp.preference in (PreferenceStrength.PREFER_A, PreferenceStrength.STRONGLY_PREFER_A):
            sa, sb = 1.0, 0.0
        elif comp.preference in (PreferenceStrength.PREFER_B, PreferenceStrength.STRONGLY_PREFER_B):
            sa, sb = 0.0, 1.0
        else:
            sa, sb = 0.5, 0.5

        ratings[comp.trajectory_a] = ra + k_factor * (sa - ea)
        ratings[comp.trajectory_b] = rb + k_factor * (sb - eb)

    return dict(ratings)
