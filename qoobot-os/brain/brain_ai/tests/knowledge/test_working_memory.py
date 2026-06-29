"""工作记忆测试"""
import pytest
import time


class TestWorkingMemory:
    """测试 WorkingMemory 核心功能"""
    
    def test_creation(self):
        """创建工作记忆实例"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        assert wm is not None
        assert hasattr(wm, 'set')
        assert hasattr(wm, 'get')

    def test_set_and_get(self):
        """基本读写"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        wm.set("test_key", "test_value")
        value = wm.get("test_key")
        assert value == "test_value"

    def test_get_nonexistent(self):
        """读取不存在的键"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        value = wm.get("nonexistent_key")
        assert value is None

    def test_set_overwrite(self):
        """覆盖写入"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        wm.set("key", "v1")
        wm.set("key", "v2")
        assert wm.get("key") == "v2"

    def test_task_context(self):
        """任务上下文存储"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        wm.set("current_task", "pick_cube")
        wm.set("scene_graph", {"objects": ["cube", "cup"]})
        assert wm.get("current_task") == "pick_cube"
        assert wm.get("scene_graph")["objects"] == ["cube", "cup"]

    def test_clear(self):
        """清空记忆"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        wm.set("key", "value")
        if hasattr(wm, 'clear'):
            wm.clear()
            assert wm.get("key") is None

    def test_get_all(self):
        """获取所有键值"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        wm.set("a", 1)
        wm.set("b", 2)
        if hasattr(wm, 'get_all'):
            all_data = wm.get_all()
            assert "a" in all_data
            assert "b" in all_data

    def test_thread_safety_basic(self):
        """基本线程安全（单线程验证）"""
        from brain_ai.knowledge.working_memory import WorkingMemory
        wm = WorkingMemory()
        for i in range(100):
            wm.set(f"key_{i}", i)
        for i in range(100):
            assert wm.get(f"key_{i}") == i
