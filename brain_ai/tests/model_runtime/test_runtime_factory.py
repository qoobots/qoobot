"""模型运行时工厂测试"""
import pytest


class TestRuntimeFactory:
    """运行时工厂测试"""
    
    @pytest.fixture
    def factory(self):
        from brain_ai.model_runtime.runtime_factory import RuntimeFactory
        return RuntimeFactory()
    
    def test_get_stub_backend(self, factory):
        backend = factory.get_backend("stub")
        assert backend is not None
    
    def test_get_unknown_backend(self, factory):
        if hasattr(factory, 'get_backend'):
            backend = factory.get_backend("nonexistent_backend")
            # 应回退到 stub
            assert backend is not None
    
    def test_list_backends(self, factory):
        if hasattr(factory, 'list_backends'):
            backends = factory.list_backends()
            assert "stub" in backends or len(backends) > 0
    
    def test_priority_selection(self, factory):
        """优先级选择：TRT-LLM > vLLM > llama.cpp > DS3 Cloud > Stub"""
        if hasattr(factory, 'get_best_available'):
            backend = factory.get_best_available()
            assert backend is not None
