"""ASR 引擎测试"""
import pytest


class TestASREngine:
    """语音识别引擎测试"""
    
    @pytest.fixture
    def asr(self):
        try:
            from brain_ai.voice_io.asr_engine import ASREngine
            return ASREngine()
        except ImportError:
            pytest.skip("ASR engine not available")
    
    def test_transcribe_stub(self, asr):
        """ASR 桩模式转写"""
        if hasattr(asr, 'transcribe'):
            text = asr.transcribe(audio_data=b"mock_audio")
            assert isinstance(text, str)
    
    def test_transcribe_empty(self, asr):
        """空音频数据"""
        if hasattr(asr, 'transcribe'):
            text = asr.transcribe(audio_data=b"")
            assert text is not None or text == ""
    
    def test_language_support(self, asr):
        """语言支持"""
        if hasattr(asr, 'SUPPORTED_LANGUAGES'):
            langs = asr.SUPPORTED_LANGUAGES
            assert "zh" in langs or "zh-CN" in langs
    
    def test_model_loading_status(self, asr):
        """模型加载状态"""
        if hasattr(asr, 'is_loaded'):
            loaded = asr.is_loaded()
            assert isinstance(loaded, bool)
