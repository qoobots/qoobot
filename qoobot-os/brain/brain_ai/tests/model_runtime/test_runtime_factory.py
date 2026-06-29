"""模型运行时工厂测试 — 基于 RuntimeFactory (model_runtime/runtime_factory.py)"""
import pytest
from brain_ai.model_runtime.runtime_factory import RuntimeFactory, BackendType, BaseLLMBackend


class TestRuntimeFactory:
    """运行时工厂测试"""

    @pytest.fixture
    def factory(self):
        return RuntimeFactory()

    def test_priority_order(self, factory):
        """优先级顺序"""
        order = factory._priority_order
        assert len(order) == 4
        assert BackendType.DS3_CLOUD in order
        assert BackendType.TRT_LLM in order

    def test_backend_enum_values(self, factory):
        """后端枚举值"""
        assert BackendType.TRT_LLM.value == "trt_llm"
        assert BackendType.DS3_CLOUD.value == "ds3_cloud"
        assert BackendType.VLLM.value == "vllm"
        assert BackendType.LLAMA_CPP.value == "llama_cpp"

    def test_get_backend_no_available(self, factory):
        """无可用后端时抛出 RuntimeError"""
        with pytest.raises(RuntimeError):
            factory.get_backend()

    def test_backend_type_order(self, factory):
        """后端类型按优先级排序"""
        # TRT_LLM > VLLM > LLAMA_CPP > DS3_CLOUD
        assert factory._priority_order[0] == BackendType.TRT_LLM
        assert factory._priority_order[-1] == BackendType.DS3_CLOUD
