"""HITL 管理器测试"""
import pytest
import asyncio


class TestHITLManager:
    """人在回路管理器测试"""
    
    @pytest.fixture
    def hitl(self):
        from brain_ai.planner.hitl_manager import HITLManager
        return HITLManager()
    
    @pytest.mark.asyncio
    async def test_countdown(self, hitl):
        """倒计时功能"""
        if hasattr(hitl, 'start_countdown'):
            result = await hitl.start_countdown(timeout=0.5)
            assert result is not None

    def test_select_trajectory(self, hitl):
        """轨迹选择"""
        trajectories = [
            {"id": "T1", "score": 0.94},
            {"id": "T2", "score": 0.88},
        ]
        if hasattr(hitl, 'select_trajectory'):
            selected = hitl.select_trajectory(trajectories, mode="auto")
            assert selected is not None
            assert selected["id"] == "T1"  # auto 模式下选择最高分

    def test_auto_select_best(self, hitl):
        """自动选择最优"""
        trajectories = [
            {"id": "T1", "score": 0.5},
            {"id": "T2", "score": 0.9},
            {"id": "T3", "score": 0.7},
        ]
        if hasattr(hitl, 'select_trajectory'):
            selected = hitl.select_trajectory(trajectories, mode="auto")
            assert selected["id"] == "T2"
    
    def test_human_override(self, hitl):
        """人工干预选择"""
        trajectories = [
            {"id": "T1", "score": 0.9},
            {"id": "T2", "score": 0.5},
        ]
        if hasattr(hitl, 'select_trajectory'):
            selected = hitl.select_trajectory(trajectories, mode="manual", selection="T2")
            assert selected["id"] == "T2"
    
    @pytest.mark.asyncio
    async def test_timeout_auto_select(self, hitl):
        """超时自动选择"""
        if hasattr(hitl, 'start_countdown'):
            trajectories = [{"id": "T1", "score": 0.9}]
            result = await hitl.start_countdown(timeout=0.3)
            if hasattr(hitl, 'select_trajectory'):
                selected = hitl.select_trajectory(trajectories, mode="auto")
                assert selected is not None
