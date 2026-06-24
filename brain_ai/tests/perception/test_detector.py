"""感知检测器测试"""
import pytest


class TestYOLODetector:
    """YOLOv11 检测器测试"""
    
    @pytest.fixture
    def detector(self):
        from brain_ai.perception.detector import YOLODetector
        return YOLODetector()
    
    def test_detect_mock(self, detector):
        """Mock 模式检测"""
        results = detector.detect(frame_id="test_001")
        assert isinstance(results, list)

    def test_detect_empty_frame(self, detector):
        """空帧检测"""
        results = detector.detect(frame_id="")
        assert results is not None

    def test_detector_registry(self, detector):
        """检测器注册表"""
        if hasattr(detector, 'registry'):
            reg = detector.registry
            assert reg is not None
    
    def test_score_threshold(self, detector):
        """置信度阈值"""
        results = detector.detect(frame_id="test", confidence_threshold=0.5)
        if len(results) > 0:
            for r in results:
                if hasattr(r, 'confidence'):
                    assert r.confidence >= 0.5
