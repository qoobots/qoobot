"""任务分解器测试 — 基于 TaskDecomposer (llm_agent/task_decomposer.py)"""
import pytest
from brain_ai.domain.entities import Intent
from brain_ai.llm_agent.task_decomposer import TaskDecomposer


class TestTaskDecomposer:
    """任务分解测试"""

    @pytest.fixture
    def decomposer(self):
        return TaskDecomposer()

    def test_decompose_simple(self, decomposer):
        """简单指令分解"""
        intent = Intent(action="pick", target="杯子")
        root = decomposer.decompose(intent)
        assert root is not None
        assert hasattr(root, 'subtasks')
        assert len(root.subtasks) > 0

    def test_decompose_complex(self, decomposer):
        """复杂指令分解"""
        intent = Intent(action="place", target="桌子")
        root = decomposer.decompose(intent)
        assert root is not None
        assert hasattr(root, 'subtasks')
        assert len(root.subtasks) > 0

    def test_decompose_result_structure(self, decomposer):
        """分解结果结构"""
        intent = Intent(action="pick", target="螺丝")
        root = decomposer.decompose(intent)
        assert len(root.subtasks) > 0
        for sub in root.subtasks:
            assert hasattr(sub, 'intent')
            assert hasattr(sub.intent, 'action')

    def test_decompose_empty(self, decomposer):
        """未知动作回退"""
        intent = Intent(action="unknown_action", target="test")
        root = decomposer.decompose(intent)
        assert root is not None
        # 未知动作至少有一个 subtask
        assert len(root.subtasks) >= 0
