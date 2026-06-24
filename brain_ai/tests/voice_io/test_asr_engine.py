"""ASR 引擎测试 — 基于 ASREngine (voice_io/asr_engine.py)"""
import pytest
from brain_ai.voice_io.asr_engine import ASREngine, ASRResult


class TestASREngine:
    """语音识别引擎测试"""

    @pytest.fixture
    def asr(self):
        return ASREngine()

    def test_transcribe_stub(self, asr):
        """ASR 桩模式转写"""
        result = asr.transcribe(audio_bytes=b"mock_audio")
        assert isinstance(result, ASRResult)
        assert hasattr(result, 'text')

    def test_transcribe_empty(self, asr):
        """空音频数据"""
        result = asr.transcribe(audio_bytes=b"")
        assert result is not None
        assert isinstance(result, ASRResult)
        assert result.text == ""  # stub mode returns empty

    def test_language_support(self, asr):
        """后端状态检查"""
        assert asr._backend in ("stub", "funasr", "whisper")

    def test_model_loading_status(self, asr):
        """模型加载状态"""
        available = asr.is_available
        assert isinstance(available, bool)

    def test_result_fields(self, asr):
        """识别结果字段完整性"""
        result = asr.transcribe(audio_bytes=b"hello")
        assert isinstance(result.text, str)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
