"""感知检测器测试 — 基于 YOLODetector (perception/detector.py)"""
import pytest
import numpy as np
from brain_ai.perception.detector import YOLODetector, Detection, DetectorRegistry


class TestYOLODetector:
    """YOLOv11 检测器测试"""

    @pytest.fixture
    def detector(self):
        return YOLODetector()

    @pytest.fixture
    def mock_image(self):
        """创建模拟 RGB 图像 (H=480, W=640, C=3)"""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    def test_detect_mock(self, detector, mock_image):
        """Mock 模式检测"""
        results = detector.detect(mock_image)
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(d, Detection) for d in results)

    def test_detect_empty_frame(self, detector):
        """黑帧检测"""
        black_image = np.zeros((480, 640, 3), dtype=np.uint8)
        results = detector.detect(black_image)
        assert results is not None
        assert isinstance(results, list)

    def test_score_threshold(self, detector, mock_image):
        """置信度阈值过滤"""
        results = detector.detect(mock_image, conf_threshold=0.85)
        if len(results) > 0:
            for r in results:
                assert r.confidence >= 0.85

    def test_detection_dataclass(self, detector, mock_image):
        """Detection 数据结构"""
        results = detector.detect(mock_image)
        for r in results:
            assert hasattr(r, 'label')
            assert hasattr(r, 'confidence')
            assert hasattr(r, 'bbox_xyxy')
            assert isinstance(r.label, str)
            assert 0.0 <= r.confidence <= 1.0


class TestDetectorRegistry:
    """检测器注册表测试"""

    def test_registry(self):
        reg = DetectorRegistry.create_default()
        det = reg.get("default")
        assert det is not None
        assert isinstance(det, YOLODetector)
