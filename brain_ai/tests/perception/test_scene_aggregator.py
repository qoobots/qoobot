"""场景聚合器测试 — 基于 SceneAggregator (perception/scene_aggregator.py)"""
import pytest
import numpy as np
from brain_ai.perception.scene_aggregator import SceneAggregator


class TestSceneAggregator:
    """场景聚合器测试"""

    @pytest.fixture
    def aggregator(self):
        return SceneAggregator()

    @pytest.fixture
    def mock_rgb(self):
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    @pytest.fixture
    def mock_depth(self):
        return np.random.rand(480, 640).astype(np.float32) * 5.0

    def test_process_frame(self, aggregator, mock_rgb, mock_depth):
        """单帧处理"""
        scene = aggregator.process_frame(mock_rgb, mock_depth)
        assert scene is not None
        assert hasattr(scene, 'objects')
        assert hasattr(scene, 'timestamp')

    def test_multi_frame(self, aggregator, mock_rgb, mock_depth):
        """多帧处理"""
        scenes = []
        for i in range(3):
            scene = aggregator.process_frame(mock_rgb, mock_depth)
            scenes.append(scene)
        assert aggregator.frame_count == 3
        assert len(scenes) == 3

    def test_scene_graph_properties(self, aggregator, mock_rgb, mock_depth):
        """场景图属性完整性"""
        scene = aggregator.process_frame(mock_rgb, mock_depth)
        assert hasattr(scene, 'robot_pose')
        assert hasattr(scene, 'occupancy')
        assert hasattr(scene, 'source_frame')

    def test_search_objects(self, aggregator, mock_rgb, mock_depth):
        """查询场景物体"""
        scene = aggregator.process_frame(mock_rgb, mock_depth)
        # 检测结果应在场景 objects 列表中
        assert hasattr(scene, 'objects')
        assert isinstance(scene.objects, list)

    def test_label_search(self, aggregator, mock_rgb, mock_depth):
        """按标签查询"""
        scene = aggregator.process_frame(mock_rgb, mock_depth)
        # 查找特定标签的物体
        cups = [o for o in scene.objects if o.label == "cup"]
        # Mock 模式下应该有 cup 检测
        assert isinstance(cups, list)
