"""任务分解器测试"""
import pytest


class TestTaskDecomposer:
    """任务分解测试"""
    
    @pytest.fixture
    def decomposer(self):
        from brain_ai.llm_agent.task_decomposer import TaskDecomposer
        return TaskDecomposer()
    
    def test_decompose_simple(self, decomposer):
        subtasks = decomposer.decompose("抓取杯子")
        assert isinstance(subtasks, list)
    
    def test_decompose_complex(self, decomposer):
        subtasks = decomposer.decompose("去厨房拿一瓶水放到桌子上")
        assert isinstance(subtasks, list)
    
    def test_decompose_result_structure(self, decomposer):
        subtasks = decomposer.decompose("捡螺丝")
        assert len(subtasks) > 0
        for st in subtasks:
            if isinstance(st, dict):
                assert "action" in st or "id" in st
    
    def test_decompose_empty(self, decomposer):
        subtasks = decomposer.decompose("")
        assert subtasks is not None
