"""行为树生成器测试 — 基于 BTGenerator (llm_agent/bt_generator.py)"""
import pytest
from brain_ai.domain.entities import Intent, Task, TaskStatus
from brain_ai.llm_agent.bt_generator import BTGenerator


class TestBTGenerator:
    """行为树 XML 生成测试"""

    @pytest.fixture
    def generator(self):
        return BTGenerator()

    def _make_task(self, subtask_actions):
        """创建带子任务的 Task 对象"""
        task = Task(id="task-001", intent=Intent(action="run", target="test"), status=TaskStatus.PLANNING)
        for i, (action, target) in enumerate(subtask_actions):
            sub = Task(
                id=f"task-001-sub-{i+1}",
                intent=Intent(action=action, target=target),
                status=TaskStatus.PENDING,
            )
            task.subtasks.append(sub)
        return task

    def test_generate_simple_bt(self, generator):
        """生成简单行为树"""
        task = self._make_task([
            ("navigate_to", "table"),
            ("pick", "red_cup"),
            ("place", "target_zone"),
        ])
        bt_xml = generator.generate(task)
        assert bt_xml is not None
        assert "<root " in bt_xml

    def test_empty_subtasks(self, generator):
        """空子任务列表"""
        task = self._make_task([])
        bt_xml = generator.generate(task)
        assert bt_xml is not None
        assert "<root " in bt_xml

    def test_bt_structure(self, generator):
        """行为树结构完整性"""
        task = self._make_task([("navigate_to", "kitchen")])
        bt_xml = generator.generate(task)
        assert isinstance(bt_xml, str)
        assert len(bt_xml) > 0

    def test_multiple_actions(self, generator):
        """多种动作的行为树"""
        task = self._make_task([
            ("navigate_to", "table"),
            ("detect", "cup"),
            ("pick", "cup"),
            ("place", "shelf"),
            ("observe", "scene"),
        ])
        bt_xml = generator.generate(task)
        assert "NavigateTo" in bt_xml
        assert "PickObject" in bt_xml or "pick" in bt_xml.lower()
