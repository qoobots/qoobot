"""HITL 管理器测试 — 基于 HITLManager (planner/hitl_manager.py)"""
import pytest
import asyncio
from brain_ai.domain.plan import ExecutionPlan
from brain_ai.domain.motion import Trajectory, TrajectorySet
from brain_ai.planner.hitl_manager import HITLManager, HITLState


class TestHITLManager:
    """人在回路管理器测试"""

    @pytest.fixture
    def hitl(self):
        return HITLManager()

    @pytest.fixture
    def sample_trajectories(self):
        """创建样例轨迹列表"""
        return [
            Trajectory(id="T1", score=0.94, path_length_m=1.0, duration_sec=2.0),
            Trajectory(id="T2", score=0.88, path_length_m=1.5, duration_sec=3.0),
        ]

    @pytest.fixture
    def trajectory_set(self, sample_trajectories):
        return TrajectorySet(
            task_id="task-001",
            trajectories=sample_trajectories,
            best_id="T1",
            hitl_timeout_sec=3.0,
        )

    @pytest.fixture
    def execution_plan(self):
        plan = ExecutionPlan(task_id="task-001", trajectory_ids=["T1", "T2"])
        plan.trajectory_ids = ["T1", "T2"]
        return plan

    def test_initial_state(self, hitl):
        """初始状态"""
        assert hitl.active_sessions == 0
        assert hitl.active_session_ids == []

    @pytest.mark.asyncio
    async def test_start_selection_timeout(self, hitl, execution_plan, trajectory_set):
        """HITL 选择超时自动选择"""
        result = await hitl.start_selection(
            plan=execution_plan,
            trajectory_set=trajectory_set,
            timeout_sec=0.1,  # 短超时确保 auto-select
        )
        assert result is not None
        assert result.state == HITLState.TIMED_OUT
        assert result.selected_trajectory_id == "T1"  # best

    def test_cancel_session(self, hitl):
        """取消不存在的会话"""
        result = hitl.cancel("nonexistent-session")
        assert result is False

    def test_select_trajectory_invalid_session(self, hitl):
        """无效会话选择失败"""
        result = hitl.select_trajectory("nonexistent", "T1")
        assert result is False

    @pytest.mark.asyncio
    async def test_hitl_result_fields(self, hitl, execution_plan, trajectory_set):
        """HITL 结果字段完整性"""
        result = await hitl.start_selection(
            plan=execution_plan,
            trajectory_set=trajectory_set,
            timeout_sec=0.1,
        )
        assert hasattr(result, 'session_id')
        assert hasattr(result, 'selected_trajectory_id')
        assert hasattr(result, 'state')
        assert hasattr(result, 'selected_by_user')
        assert hasattr(result, 'elapsed_sec')
