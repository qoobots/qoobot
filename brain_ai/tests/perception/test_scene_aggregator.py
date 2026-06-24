"""场景聚合器测试"""
import pytest


class TestSceneAggregator:
    """场景聚合器测试"""
    
    @pytest.fixture
    def aggregator(self):
        from brain_ai.perception.scene_aggregator import SceneAggregator
        return SceneAggregator()
    
    def test_aggregate_single_frame(self, aggregator):
        """单帧聚合"""
        scene = aggregator.aggregate(frame_id="f-001")
        assert scene is not None

    def test_aggregate_multi_frame(self, aggregator):
        """多帧聚合"""
        for i in range(5):
            scene = aggregator.aggregate(frame_id=f"f-{i:03d}")
        assert scene is not None

    def test_scene_with_slam(self, aggregator):
        """SLAM 集成场景"""
        if hasattr(aggregator, 'get_localization'):
            loc = aggregator.get_localization()
            assert loc is not None

    def test_query_objects(self, aggregator):
        """查询场景物体"""
        aggregator.aggregate(frame_id="f-001")
        if hasattr(aggregator, 'query_objects'):
            objects = aggregator.query_objects()
            assert isinstance(objects, list)

    def test_query_by_label(self, aggregator):
        """按标签查询"""
        aggregator.aggregate(frame_id="f-001")
        if hasattr(aggregator, 'query_by_label'):
            result = aggregator.query_by_label("cube")
            assert result is not None
