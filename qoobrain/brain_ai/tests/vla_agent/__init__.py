"""VLA Agent 模块导入测试"""
import pytest


class TestVLAAgentImports:
    """验证 VLA Agent 模块所有公共 API 可导入"""

    def test_import_vla_inferencer(self):
        from brain_ai.vla_agent.vla_inferencer import VLAInferencer
        assert VLAInferencer is not None

    def test_import_action_decoder(self):
        from brain_ai.vla_agent.action_decoder import ActionDecoder, DecodedAction, DecodeMode
        assert ActionDecoder is not None
        assert DecodedAction is not None

    def test_import_chunk_predictor(self):
        from brain_ai.vla_agent.chunk_predictor import ChunkPredictor, ActionChunk
        assert ChunkPredictor is not None
        assert ActionChunk is not None

    def test_import_model_loader(self):
        from brain_ai.vla_agent.model_loader import ModelLoader, ModelBackend
        assert ModelLoader is not None
        assert ModelBackend is not None

    def test_import_lora_adapter(self):
        from brain_ai.vla_agent.lora_adapter import LoRAAdapter, LoRAConfig, LoRATask
        assert LoRAAdapter is not None
        assert LoRAConfig is not None

    def test_import_package(self):
        import brain_ai.vla_agent
        assert brain_ai.vla_agent is not None

    def test_all_exports(self):
        from brain_ai.vla_agent import __all__
        assert "VLAInferencer" in __all__
        assert "ActionDecoder" in __all__
        assert "ChunkPredictor" in __all__
        assert "ModelLoader" in __all__
        assert "LoRAAdapter" in __all__
