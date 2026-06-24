"""VLA Agent 动作解码器测试"""
import pytest


class TestActionDecoder:
    """VLA 动作解码器测试"""
    
    def test_import(self):
        """确保模块可导入"""
        try:
            from brain_ai.vla_agent import action_decoder
            assert action_decoder is not None
        except ImportError:
            pytest.skip("vla_agent module not yet implemented")

    def test_decode_action(self):
        """解码动作向量→机器人指令"""
        pass  # Phase 2 功能


class TestVLAModel:
    """VLA 模型桩"""
    
    def test_model_stub(self):
        """模型桩接口"""
        pass
