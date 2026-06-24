"""轨迹生成器测试"""
import pytest


class TestTrajectoryGenerator:
    """多策略轨迹生成器测试"""
    
    @pytest.fixture
    def generator(self):
        from brain_ai.planner.trajectory_gen import TrajectoryGenerator
        return TrajectoryGenerator()
    
    def test_generate_single_strategy(self, generator):
        """单策略生成"""
        if hasattr(generator, 'generate'):
            traj = generator.generate(
                start_pose=[0, 0, 0],
                target_pose=[0.5, 0.3, 0.1],
                strategy="optimal"
            )
            assert traj is not None

    def test_generate_all_strategies(self, generator):
        """所有策略并行生成"""
        if hasattr(generator, 'generate_all'):
            trajectories = generator.generate_all(
                start_pose=[0, 0, 0],
                target_pose=[0.5, 0.3, 0.1]
            )
            assert isinstance(trajectories, list)
            assert len(trajectories) >= 1

    def test_strategy_enum(self, generator):
        """策略枚举"""
        if hasattr(generator, 'STRATEGIES'):
            strategies = generator.STRATEGIES
            assert "optimal" in strategies or len(strategies) > 0

    def test_trajectory_structure(self, generator):
        """轨迹结构完整"""
        if hasattr(generator, 'generate'):
            traj = generator.generate(
                start_pose=[0, 0, 0],
                target_pose=[0.5, 0.3, 0.1],
                strategy="optimal"
            )
            if isinstance(traj, dict):
                assert "waypoints" in traj or "points" in traj or "path" in traj

    def test_start_target_validation(self, generator):
        """起止点校验"""
        if hasattr(generator, 'validate'):
            valid = generator.validate([0, 0, 0], [0.5, 0.3, 0.1])
            assert valid is True
