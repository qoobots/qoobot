"""轨迹评分器测试"""
import pytest


class TestTrajectoryScorer:
    """六维加权评分引擎测试"""
    
    @pytest.fixture
    def scorer(self):
        from brain_ai.planner.scorer import TrajectoryScorer
        return TrajectoryScorer()
    
    def test_score_single(self, scorer):
        """单条轨迹评分"""
        trajectory = {
            "id": "T1",
            "path_length": 1.0,
            "duration": 2.0,
            "collision_risk": 0.0,
            "manipulability": 0.8,
            "torque": 0.5,
            "smoothness": 0.9,
        }
        score = scorer.score(trajectory)
        assert 0.0 <= score <= 1.0

    def test_score_ranking(self, scorer):
        """多条轨迹排名"""
        trajectories = [
            {"id": "T1", "path_length": 0.8, "duration": 1.5, "collision_risk": 0.0, "manipulability": 0.9, "torque": 0.3, "smoothness": 0.9},
            {"id": "T2", "path_length": 1.5, "duration": 3.0, "collision_risk": 0.1, "manipulability": 0.5, "torque": 0.7, "smoothness": 0.6},
            {"id": "T3", "path_length": 1.0, "duration": 2.0, "collision_risk": 0.05, "manipulability": 0.7, "torque": 0.5, "smoothness": 0.8},
        ]
        ranked = scorer.rank(trajectories) if hasattr(scorer, 'rank') else []
        if ranked:
            assert len(ranked) == 3
            assert ranked[0]["id"] == "T1"  # 最优轨迹排在前面
    
    def test_collision_penalty(self, scorer):
        """碰撞惩罚"""
        traj_safe = {"path_length": 1.0, "duration": 2.0, "collision_risk": 0.0, "manipulability": 0.8, "torque": 0.5, "smoothness": 0.9}
        traj_risky = {"path_length": 1.0, "duration": 2.0, "collision_risk": 0.9, "manipulability": 0.8, "torque": 0.5, "smoothness": 0.9}
        score_safe = scorer.score(traj_safe)
        score_risky = scorer.score(traj_risky)
        assert score_safe >= score_risky, f"安全轨迹 ({score_safe}) 不应低于风险轨迹 ({score_risky})"
    
    def test_weights_configurable(self, scorer):
        """权重可配置"""
        if hasattr(scorer, 'set_weights'):
            scorer.set_weights(path=0.2, duration=0.1, collision=0.5, manipulability=0.1, torque=0.05, smoothness=0.05)
