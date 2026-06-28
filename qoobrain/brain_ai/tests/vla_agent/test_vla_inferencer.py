"""VLA 推理器测试 — 基于 VLAInferencer (vla_agent/vla_inferencer.py)"""
import pytest
import numpy as np
from brain_ai.vla_agent.vla_inferencer import (
    VLAInferencer, VLAInferenceMode, VLAInferenceResult,
)
from brain_ai.vla_agent.model_loader import ModelBackend


class TestVLAInferencer:
    """VLA 主推理器测试"""

    @pytest.fixture
    def inferencer(self):
        return VLAInferencer(mode=VLAInferenceMode.MOCK)

    @pytest.fixture
    def mock_image(self):
        """模拟 RGB 图像 (480, 640, 3)"""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    @pytest.fixture
    def mock_pose(self):
        """当前末端执行器位姿"""
        return np.array([0.5, 0.3, 0.2, 0.0, 0.0, 0.0, 0.5], dtype=np.float32)

    def test_mock_infer(self, inferencer, mock_image):
        """Mock 推理返回有效结果"""
        result = inferencer.infer(
            image=mock_image,
            instruction="把红色杯子放到桌子上",
        )
        assert isinstance(result, VLAInferenceResult)
        assert result.mode == VLAInferenceMode.MOCK
        assert len(result.decoded_actions) > 0
        assert result.inference_ms > 0

    def test_mock_infer_with_pose(self, inferencer, mock_image, mock_pose):
        """带当前位姿的推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="把红色杯子放到桌子上",
            current_pose=mock_pose,
        )
        assert isinstance(result, VLAInferenceResult)
        assert len(result.decoded_actions) > 0

    def test_pick_instruction(self, inferencer, mock_image):
        """'抓' 指令推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="抓起那个红色方块",
        )
        assert result is not None
        # 抓取时夹爪应接近闭合
        actions = result.decoded_actions
        assert any(a.gripper > 0.5 for a in actions)

    def test_place_instruction(self, inferencer, mock_image):
        """'放' 指令推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="把杯子放到桌上",
        )
        assert result is not None
        actions = result.decoded_actions
        assert any(a.gripper < 0.5 for a in actions)

    def test_push_instruction(self, inferencer, mock_image):
        """'推' 指令推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="把箱子推过去",
        )
        assert result is not None
        actions = result.decoded_actions
        # 推动时夹爪应闭合
        assert any(a.gripper > 0.9 for a in actions)

    def test_left_instruction(self, inferencer, mock_image):
        """'左' 方向推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="往左移动一点",
        )
        assert result is not None
        actions = result.decoded_actions
        # 左侧移动 y 应为正
        assert any(a.as_array()[1] > 0.0 for a in actions)

    def test_right_instruction(self, inferencer, mock_image):
        """'右' 方向推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="向右移动",
        )
        assert result is not None
        actions = result.decoded_actions
        assert any(a.as_array()[1] < 0.0 for a in actions)

    def test_up_instruction(self, inferencer, mock_image):
        """'上' 方向推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="往上方移动",
        )
        assert result is not None
        actions = result.decoded_actions
        assert any(a.as_array()[2] > 0.0 for a in actions)

    def test_down_instruction(self, inferencer, mock_image):
        """'下' 方向推理"""
        result = inferencer.infer(
            image=mock_image,
            instruction="往下移动",
        )
        assert result is not None
        actions = result.decoded_actions
        assert any(a.as_array()[2] < 0.0 for a in actions)

    def test_unknown_instruction(self, inferencer, mock_image):
        """未知指令应有默认动作"""
        result = inferencer.infer(
            image=mock_image,
            instruction="abcd1234",
        )
        assert result is not None
        assert len(result.decoded_actions) > 0

    def test_result_metadata(self, inferencer, mock_image):
        """结果包含元数据"""
        result = inferencer.infer(
            image=mock_image,
            instruction="测试指令",
        )
        assert "instruction" in result.metadata
        assert "image_shape" in result.metadata
        assert result.metadata["instruction"] == "测试指令"

    def test_set_mode(self, inferencer):
        """切换推理模式"""
        assert inferencer.mode == VLAInferenceMode.MOCK
        inferencer.set_mode(VLAInferenceMode.ACTION_ONLY)
        assert inferencer.mode == VLAInferenceMode.ACTION_ONLY

    def test_action_only_mode(self, mock_pose):
        """仅动作推理模式"""
        inferencer = VLAInferencer(mode=VLAInferenceMode.ACTION_ONLY)
        result = inferencer.infer(
            image=np.zeros((64, 64, 3), dtype=np.uint8),
            instruction="test",
            current_pose=mock_pose,
        )
        assert result is not None
        assert len(result.decoded_actions) > 0

    def test_end_to_end_mode_fallback(self, inferencer, mock_image):
        """端到端模式在无模型时回退到 mock"""
        inferencer.set_mode(VLAInferenceMode.END_TO_END)
        result = inferencer.infer(
            image=mock_image,
            instruction="端到端测试",
        )
        assert result is not None
        assert len(result.decoded_actions) > 0

    def test_action_dimensions(self, inferencer, mock_image):
        """动作维度验证"""
        result = inferencer.infer(
            image=mock_image,
            instruction="test",
        )
        for action in result.decoded_actions:
            arr = action.as_array()
            assert arr.shape == (7,)

    def test_horizon_length(self, inferencer, mock_image):
        """预测视界长度"""
        result = inferencer.infer(
            image=mock_image,
            instruction="test",
        )
        chunks = result.action_chunks
        assert chunks.horizon > 0
        assert len(chunks.chunks) <= chunks.horizon


class TestVLAInferenceResult:
    """VLAInferenceResult 数据结构测试"""

    def test_default_fields(self):
        result = VLAInferenceResult(
            action_chunks=None,
            decoded_actions=[],
        )
        assert result.inference_ms == 0.0
        assert result.model_name == "brain-vla"
        assert result.mode == VLAInferenceMode.MOCK
