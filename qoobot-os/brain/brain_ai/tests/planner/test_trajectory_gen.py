"""轨迹生成器测试 — 基于 TrajectoryGenerator (planner/trajectory_gen.py)"""
import pytest
from brain_ai.domain.motion import TrajectoryStrategy, TrajectorySet
from brain_ai.domain.scene import Pose6D
from brain_ai.planner.trajectory_gen import TrajectoryGenerator


class TestTrajectoryGenerator:
    """多策略轨迹生成器测试"""

    @pytest.fixture
    def generator(self):
        return TrajectoryGenerator()

    def test_generate_trajectory_set(self, generator):
        """生成轨迹集合"""
        result = generator.generate(
            task_id="task-001",
            target_pose=[0.5, 0.3, 0.1, 0, 0, 0, 1],
        )
        assert result is not None
        assert isinstance(result, TrajectorySet)
        assert result.task_id == "task-001"

    def test_generate_with_pose6d(self, generator):
        """使用 Pose6D 作为目标"""
        from brain_ai.domain.scene import Vec3, Quaternion
        pose = Pose6D(position=Vec3(x=0.5, y=0.3, z=0.1), orientation=Quaternion())
        result = generator.generate(task_id="task-002", target_pose=pose)
        assert result is not None

    def test_trajectory_set_fields(self, generator):
        """轨迹集合字段完整性"""
        result = generator.generate(
            task_id="task-003",
            target_pose=[0.5, 0.3, 0.1, 0, 0, 0, 1],
        )
        assert hasattr(result, 'trajectories')
        assert hasattr(result, 'best_id')
        assert hasattr(result, 'task_id')
        assert len(result.trajectories) > 0
        # 排名最高的轨迹评分应该存在
        assert result.trajectories[0].score >= 0.0

    def test_generate_single_strategy(self, generator):
        """单策略生成"""
        traj = generator.generate_single(
            task_id="task-004",
            target_pose=[0.5, 0.3, 0.1, 0, 0, 0, 1],
            strategy=TrajectoryStrategy.OPTIMAL,
        )
        # generate_single returns Optional[Trajectory], may be None on Windows stub
        if traj is not None:
            assert traj.strategy == TrajectoryStrategy.OPTIMAL

    def test_available_strategies(self, generator):
        """可用策略列表"""
        assert len(generator._strategies) >= 3
        values = [s.value for s in generator._strategies]
        assert "OPTIMAL" in values
