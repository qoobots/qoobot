"""轨迹评分器测试 — 基于 TrajectoryScorer (planner/scorer.py)"""
import pytest
from brain_ai.domain.motion import Trajectory, TrajectoryStrategy, Waypoint
from brain_ai.domain.scene import Pose6D
from brain_ai.planner.scorer import TrajectoryScorer, ScoringWeights


class TestTrajectoryScorer:
    """六维加权评分引擎测试"""

    @pytest.fixture
    def scorer(self):
        return TrajectoryScorer()

    def _make_traj(self, tid="T1", path_len=1.0, duration=2.0,
                   collision_free=True, manipulability=0.8, effort=10.0,
                   strategy=TrajectoryStrategy.OPTIMAL):
        """创建 Trajectory 对象用于测试"""
        wp = Waypoint(pose=Pose6D(), time_from_start_sec=0.0)
        return Trajectory(
            id=tid,
            strategy=strategy,
            waypoints=[wp, wp],  # min 2 for smoothness
            path_length_m=path_len,
            duration_sec=duration,
            collision_free=collision_free,
            manipulability=manipulability,
            joint_effort_rms=effort,
        )

    def test_score_single(self, scorer):
        """单条轨迹评分"""
        traj = self._make_traj()
        result = scorer.score(traj)
        assert result is not None
        assert 0.0 <= result.composite <= 1.0

    def test_score_ranking(self, scorer):
        """多条轨迹排名"""
        trajs = [
            self._make_traj("T1", path_len=0.8, duration=1.5, manipulability=0.9, effort=5.0),
            self._make_traj("T2", path_len=1.5, duration=3.0, manipulability=0.5, effort=15.0),
            self._make_traj("T3", path_len=1.0, duration=2.0, manipulability=0.7, effort=10.0),
        ]
        ranked = scorer.rank(trajs)
        assert len(ranked) == 3
        # 最优轨迹（短路径+高灵巧度）应排前面
        assert ranked[0].score >= ranked[-1].score

    def test_collision_penalty(self, scorer):
        """碰撞惩罚"""
        traj_safe = self._make_traj("T_safe", collision_free=True)
        traj_risky = self._make_traj("T_risky", collision_free=False)
        result_safe = scorer.score(traj_safe)
        result_risky = scorer.score(traj_risky)
        assert result_safe.collision_safety_score == 1.0
        assert result_risky.collision_safety_score == 0.0
        assert result_safe.composite >= result_risky.composite

    def test_weights_configurable(self):
        """权重可配置"""
        weights = ScoringWeights(
            path_length=0.2, duration=0.1, collision_safety=0.5,
            manipulability=0.1, joint_effort=0.05, smoothness=0.05,
        )
        scorer = TrajectoryScorer(weights=weights)
        traj = self._make_traj()
        result = scorer.score(traj)
        assert 0.0 <= result.composite <= 1.0
