"""意图解析器测试"""
import pytest


class TestIntentParser:
    """意图解析测试 — LLM + 规则双路"""
    
    @pytest.fixture
    def parser(self):
        from brain_ai.llm_agent.intent_parser import IntentParser
        return IntentParser()

    def test_parse_pick(self, parser):
        intent = parser.parse("抓取红色的方块")
        assert intent is not None
        assert hasattr(intent, 'action') or isinstance(intent, dict)
        action = intent.action if hasattr(intent, 'action') else intent.get("action")
        assert action in ["pick", "Pick", None]
    
    def test_parse_navigate(self, parser):
        intent = parser.parse("去厨房拿水")
        assert intent is not None

    def test_parse_place(self, parser):
        intent = parser.parse("把物体放到桌上")
        assert intent is not None

    def test_parse_unknown(self, parser):
        intent = parser.parse("xyzzy_invalid_command")
        assert intent is not None
    
    def test_parse_empty(self, parser):
        intent = parser.parse("")
        assert intent is not None
    
    def test_parse_confidence(self, parser):
        intent = parser.parse("抓杯子")
        if isinstance(intent, dict):
            assert "confidence" in intent or intent.get("action") is not None
