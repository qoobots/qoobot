"""LoRA 适配器测试 — 基于 LoRAAdapter (vla_agent/lora_adapter.py)"""
import pytest
from brain_ai.vla_agent.lora_adapter import (
    LoRAAdapter, LoRAConfig, LoRATask,
)


class TestLoRAAdapter:
    """LoRA 适配器管理器测试"""

    @pytest.fixture
    def adapter(self):
        return LoRAAdapter()

    def test_initial_state(self, adapter):
        """初始状态"""
        assert adapter.active_config is None
        assert adapter.loaded_tasks == []

    def test_load_adapter(self, adapter):
        """加载适配器"""
        config = adapter.load("brain-vla-chinese-lora", task=LoRATask.GENERAL)
        assert isinstance(config, LoRAConfig)
        assert config.task == LoRATask.GENERAL
        assert config.rank == 64
        assert config.alpha == 128
        assert adapter.active_config is not None

    def test_load_multiple_adapters(self, adapter):
        """加载多个适配器"""
        adapter.load("general-lora", task=LoRATask.GENERAL)
        adapter.load("pick-place-lora", task=LoRATask.PICK_PLACE)
        adapter.load("nav-lora", task=LoRATask.NAVIGATION)
        assert len(adapter.loaded_tasks) == 3
        assert LoRATask.GENERAL in adapter.loaded_tasks
        assert LoRATask.PICK_PLACE in adapter.loaded_tasks
        assert LoRATask.NAVIGATION in adapter.loaded_tasks

    def test_switch_to(self, adapter):
        """切换适配器"""
        adapter.load("general-lora", task=LoRATask.GENERAL)
        adapter.load("pick-lora", task=LoRATask.PICK_PLACE)
        assert adapter.active_config.task == LoRATask.PICK_PLACE  # 最后加载的

        result = adapter.switch_to(LoRATask.GENERAL)
        assert result is True
        assert adapter.active_config.task == LoRATask.GENERAL

    def test_switch_to_unloaded(self, adapter):
        """切换到未加载的适配器"""
        result = adapter.switch_to(LoRATask.NAVIGATION)
        assert result is False

    def test_merge_adapters(self, adapter):
        """合并多个适配器"""
        adapter.load("general-lora", task=LoRATask.GENERAL)
        adapter.load("pick-lora", task=LoRATask.PICK_PLACE)
        result = adapter.merge_adapters([LoRATask.GENERAL, LoRATask.PICK_PLACE])
        assert result is True
        assert adapter.active_config.merged is True

    def test_merge_missing_adapters(self, adapter):
        """合并缺失的适配器失败"""
        adapter.load("general-lora", task=LoRATask.GENERAL)
        result = adapter.merge_adapters([LoRATask.GENERAL, LoRATask.NAVIGATION])
        assert result is False

    def test_unload_all(self, adapter):
        """卸载所有适配器"""
        adapter.load("a", task=LoRATask.GENERAL)
        adapter.load("b", task=LoRATask.PICK_PLACE)
        adapter.unload_all()
        assert adapter.active_config is None
        assert adapter.loaded_tasks == []

    def test_custom_config(self, adapter):
        """自定义 LoRA 配置"""
        custom = LoRAConfig(
            task=LoRATask.MANIPULATION,
            rank=32,
            alpha=64,
            dropout=0.1,
        )
        config = adapter.load("manip-lora", task=LoRATask.MANIPULATION, config=custom)
        assert config.rank == 32
        assert config.alpha == 64
        assert config.dropout == 0.1

    def test_repr(self, adapter):
        """字符串表示"""
        r = repr(adapter)
        assert "LoRAAdapter" in r
        assert "active=none" in r

        adapter.load("test-lora", task=LoRATask.GENERAL)
        r2 = repr(adapter)
        assert "active=general" in r2


class TestLoRAConfig:
    """LoRAConfig 数据结构测试"""

    def test_default_config(self):
        config = LoRAConfig()
        assert config.task == LoRATask.GENERAL
        assert config.rank == 64
        assert config.alpha == 128
        assert config.dropout == 0.05
        assert not config.merged
        assert len(config.target_modules) == 7

    def test_task_specific_config(self):
        config = LoRAConfig(task=LoRATask.PICK_PLACE)
        assert config.task == LoRATask.PICK_PLACE


class TestLoRATask:
    """LoRATask 枚举测试"""

    def test_task_values(self):
        assert LoRATask.GENERAL.value == "general"
        assert LoRATask.PICK_PLACE.value == "pick_place"
        assert LoRATask.NAVIGATION.value == "navigation"
        assert LoRATask.MANIPULATION.value == "manipulation"
        assert LoRATask.SOCIAL.value == "social"
