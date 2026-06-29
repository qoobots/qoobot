"""动作块预测器测试 — 基于 ChunkPredictor (vla_agent/chunk_predictor.py)"""
import pytest
import numpy as np
from brain_ai.vla_agent.chunk_predictor import (
    ChunkPredictor, ChunkPrediction, ActionChunk,
)


class TestChunkPredictor:
    """动作块预测器测试"""

    @pytest.fixture
    def predictor(self):
        return ChunkPredictor(action_dim=7, horizon=16)

    @pytest.fixture
    def mock_output(self):
        """模拟 VLA 模型输出 (horizon, 7)"""
        return np.random.randn(16, 7).astype(np.float32) * 0.01

    @pytest.fixture
    def current_pose(self):
        return np.array([0.5, 0.3, 0.2, 0.0, 0.0, 0.0, 0.5], dtype=np.float32)

    def test_predict_basic(self, predictor, mock_output):
        """基本预测"""
        prediction = predictor.predict(mock_output)
        assert isinstance(prediction, ChunkPrediction)
        assert len(prediction.chunks) > 0
        assert prediction.horizon > 0
        assert prediction.inference_ms >= 0

    def test_predict_with_pose(self, predictor, mock_output, current_pose):
        """带当前位姿的预测"""
        prediction = predictor.predict(mock_output, current_pose=current_pose)
        assert len(prediction.chunks) > 0
        # 预测应基于当前位姿偏移
        first_chunk = prediction.chunks[0]
        assert abs(first_chunk.x - current_pose[0]) < 1.0

    def test_predict_1d_input(self, predictor):
        """1D 输入自动 reshape"""
        output_1d = np.random.randn(7).astype(np.float32) * 0.01
        prediction = predictor.predict(output_1d)
        assert len(prediction.chunks) >= 1

    def test_predict_smaller_dim(self, predictor):
        """维度小于 7 时自动补齐"""
        output_small = np.random.randn(16, 5).astype(np.float32) * 0.01
        prediction = predictor.predict(output_small)
        assert len(prediction.chunks) > 0
        # 补齐后应为 7 维
        arr = prediction.chunks[0].as_array()
        assert len(arr) == 7

    def test_predict_shorter_horizon(self, predictor):
        """短视界输入"""
        output_short = np.random.randn(5, 7).astype(np.float32) * 0.01
        prediction = predictor.predict(output_short)
        assert len(prediction.chunks) == 5

    def test_gripper_binarization(self, predictor, mock_output):
        """夹爪二值化"""
        # 设置所有夹爪值 > 阈值
        mock_output[:, 6] = 0.8
        prediction = predictor.predict(mock_output)
        for chunk in prediction.chunks:
            assert chunk.gripper in (0.0, 1.0)

    def test_gripper_binarization_closed(self, predictor, mock_output):
        """夹爪闭合二值化"""
        mock_output[:, 6] = 0.2
        prediction = predictor.predict(mock_output)
        for chunk in prediction.chunks:
            assert chunk.gripper == 0.0

    def test_smooth(self, predictor, mock_output):
        """动作平滑"""
        prediction = predictor.predict(mock_output)
        smoothed = predictor.smooth(prediction, window=3)
        assert isinstance(smoothed, ChunkPrediction)
        assert len(smoothed.chunks) == len(prediction.chunks)

    def test_smooth_short_sequence(self, predictor):
        """短序列不崩溃"""
        output_short = np.random.randn(2, 7).astype(np.float32) * 0.01
        prediction = predictor.predict(output_short)
        smoothed = predictor.smooth(prediction, window=3)
        assert len(smoothed.chunks) == 2

    def test_interpolate(self, predictor, mock_output):
        """频率插值 10Hz → 50Hz"""
        prediction = predictor.predict(mock_output)
        interpolated = predictor.interpolate(
            prediction, target_freq=50.0, source_freq=10.0,
        )
        assert isinstance(interpolated, ChunkPrediction)
        # 5x 插值
        assert len(interpolated.chunks) == len(prediction.chunks) * 5

    def test_interpolate_noop(self, predictor, mock_output):
        """相同频率插值无变化"""
        prediction = predictor.predict(mock_output)
        interpolated = predictor.interpolate(
            prediction, target_freq=10.0, source_freq=10.0,
        )
        assert len(interpolated.chunks) == len(prediction.chunks)

    def test_action_chunk_as_array(self):
        """ActionChunk → numpy"""
        chunk = ActionChunk(x=0.5, y=0.3, z=0.2, roll=0.0, pitch=0.0, yaw=1.57, gripper=0.8)
        arr = chunk.as_array()
        assert arr.shape == (7,)
        assert arr[0] == 0.5
        assert arr[6] == 0.8

    def test_action_chunk_from_array(self):
        """numpy → ActionChunk"""
        arr = np.array([0.5, 0.3, 0.2, 0.0, 0.0, 1.57, 0.8], dtype=np.float32)
        chunk = ActionChunk.from_array(arr, confidence=0.9)
        assert chunk.x == 0.5
        assert chunk.y == 0.3
        assert chunk.confidence == 0.9

    def test_action_chunk_defaults(self):
        """默认值"""
        chunk = ActionChunk()
        assert chunk.x == 0.0
        assert chunk.gripper == 0.0
        assert chunk.confidence == 1.0
        assert chunk.timestamp > 0

    def test_scale_factor(self):
        """动作缩放因子"""
        predictor = ChunkPredictor(action_scale=0.5)
        output = np.ones((4, 7), dtype=np.float32) * 0.1
        prediction = predictor.predict(output)
        # 缩放后应为 0.05
        assert abs(prediction.chunks[0].x - 0.05) < 0.01

    def test_custom_gripper_threshold(self):
        """自定义夹爪阈值"""
        predictor = ChunkPredictor(gripper_threshold=0.3)
        output = np.ones((4, 7), dtype=np.float32) * 0.2
        prediction = predictor.predict(output)
        for chunk in prediction.chunks:
            assert chunk.gripper == 0.0  # 低于 0.3 阈值
