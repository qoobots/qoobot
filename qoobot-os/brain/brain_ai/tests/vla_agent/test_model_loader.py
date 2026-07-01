"""VLA 模型加载器测试 — 基于 ModelLoader (vla_agent/model_loader.py)"""
import pytest
from brain_ai.vla_agent.model_loader import (
    ModelLoader, ModelBackend, VLAModelInfo,
)


class TestModelLoader:
    """模型加载器测试"""

    @pytest.fixture
    def loader(self):
        return ModelLoader()

    def test_initial_state(self, loader):
        """初始状态"""
        assert loader.is_loaded is False
        assert loader.model_info is None

    def test_load_mock(self, loader):
        """加载 mock 模型"""
        info = loader.load("test-model", backend=ModelBackend.MOCK)
        assert loader.is_loaded is True
        assert isinstance(info, VLAModelInfo)
        assert info.name == "test-model"
        assert info.backend == ModelBackend.MOCK

    def test_unload(self, loader):
        """卸载模型"""
        loader.load("test-model", backend=ModelBackend.MOCK)
        assert loader.is_loaded is True
        loader.unload()
        assert loader.is_loaded is False
        assert loader.model_info is None

    def test_load_reload(self, loader):
        """重新加载"""
        loader.load("model-a", backend=ModelBackend.MOCK)
        loader.unload()
        loader.load("model-b", backend=ModelBackend.MOCK)
        assert loader.is_loaded is True
        assert loader.model_info.name == "model-b"

    def test_hot_swap_lora(self, loader):
        """热切换 LoRA"""
        loader.load("base-model", backend=ModelBackend.MOCK)
        result = loader.hot_swap_lora("/path/to/new/lora")
        assert result is True
        assert loader.model_info.lora_path == "/path/to/new/lora"

    def test_hot_swap_no_model(self, loader):
        """未加载模型时热切换失败"""
        result = loader.hot_swap_lora("/path/to/lora")
        assert result is False

    def test_load_nonexistent_model(self, loader):
        """加载不存在的模型回退到 mock"""
        info = loader.load("nonexistent-model", backend=ModelBackend.PYTORCH)
        assert info.backend == ModelBackend.MOCK
        assert "mock" in info.metadata.get("source", "")

    def test_load_trt_llm(self, loader):
        """TensorRT-LLM 后端加载（无 GPU 环境回退到 mock）"""
        info = loader.load("test-model", backend=ModelBackend.TRT_LLM)
        # 无 TRT-LLM 环境时回退到 MOCK
        assert info.backend in (ModelBackend.TRT_LLM, ModelBackend.MOCK)
        assert info.name == "test-model"

    def test_model_info_defaults(self):
        """VLAModelInfo 默认值"""
        info = VLAModelInfo()
        assert info.name == "brain-vla-chinese-lora"
        assert info.base_model == "openvla/openvla-7b"
        assert info.action_dim == 7
        assert info.action_horizon == 16
        assert info.chunk_size == 16
        assert info.max_batch_size == 1

    def test_repr(self, loader):
        """字符串表示"""
        r = repr(loader)
        assert "ModelLoader" in r
        loader.load("test", backend=ModelBackend.MOCK)
        r2 = repr(loader)
        assert "loaded=True" in r2


class TestModelBackend:
    """推理后端枚举测试"""

    def test_backend_values(self):
        assert ModelBackend.TRT_LLM.value == "trt_llm"
        assert ModelBackend.PYTORCH.value == "pytorch"
        assert ModelBackend.ONNX.value == "onnx"
        assert ModelBackend.MOCK.value == "mock"
