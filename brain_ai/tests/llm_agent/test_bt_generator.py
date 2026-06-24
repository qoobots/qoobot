"""行为树生成器测试"""
import pytest
from unittest.mock import MagicMock, patch


class TestBTGenerator:
    """行为树 XML 生成测试"""
    
    def test_generate_simple_bt(self):
        """生成简单行为树"""
        subtasks = [
            {"id": "S1", "action": "NavigateTo", "params": {"pose": [0.5, 0.2, 0.1]}},
            {"id": "S2", "action": "PickObject", "params": {"object_id": "obj-001"}},
            {"id": "S3", "action": "PlaceObject", "params": {"target": [0.8, 0.3, 0.15]}},
        ]
        from brain_ai.planner.bt_composer import BTComposer
        composer = BTComposer()
        bt_xml = composer.compose(subtasks)
        assert bt_xml is not None
        assert "NavigateTo" in bt_xml or "<root>" in bt_xml

    def test_empty_subtasks(self):
        """空子任务列表"""
        from brain_ai.planner.bt_composer import BTComposer
        composer = BTComposer()
        bt_xml = composer.compose([])
        assert bt_xml is not None
    
    def test_bt_structure(self):
        """行为树结构完整性"""
        subtasks = [{"id": "S1", "action": "NavigateTo"}]
        from brain_ai.planner.bt_composer import BTComposer
        composer = BTComposer()
        bt_xml = composer.compose(subtasks)
        assert isinstance(bt_xml, str)
        assert len(bt_xml) > 0
    
    def test_skill_registry(self):
        """技能注册表"""
        from brain_ai.planner.bt_composer import BTComposer
        composer = BTComposer()
        if hasattr(composer, 'skill_registry'):
            assert composer.skill_registry is not None
    
    def test_multiple_actions(self):
        """多种动作的行为树"""
        subtasks = [
            {"id": "S1", "action": "NavigateTo"},
            {"id": "S2", "action": "DetectObject"},
            {"id": "S3", "action": "PickObject"},
            {"id": "S4", "action": "PlaceObject"},
            {"id": "S5", "action": "Wait"},
        ]
        from brain_ai.planner.bt_composer import BTComposer
        composer = BTComposer()
        bt_xml = composer.compose(subtasks)
        assert "NavigateTo" in bt_xml
