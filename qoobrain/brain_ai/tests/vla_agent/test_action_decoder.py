"""VLA Agent 动作解码器测试 — 基于 ActionDecoder (vla_agent/action_decoder.py)"""
import pytest
import numpy as np
from brain_ai.vla_agent.action_decoder import (
    ActionDecoder, DecodedAction, ActionSpace,
    DecodeMode,
)


class TestActionDecoder:
    """VLA 动作解码器测试"""

    @pytest.fixture
    def decoder(self):
        return ActionDecoder(mode=DecodeMode.MOCK)

    @pytest.fixture
    def continuous_decoder(self):
        return ActionDecoder(mode=DecodeMode.CONTINUOUS)

    def test_decode_single_action(self, decoder):
        """解码单个动作"""
        model_output = np.array([0.5, 0.3, 0.2, 0.0, 0.0, 0.0, 0.8], dtype=np.float32)
        action = decoder.decode(model_output)
        assert isinstance(action, DecodedAction)
        assert len(action.position) == 3
        assert len(action.rotation) == 3
        assert 0.0 <= action.gripper <= 1.0

    def test_decode_batch(self, decoder):
        """批量解码"""
        model_outputs = np.random.rand(4, 7).astype(np.float32)
        actions = decoder.decode_batch(model_outputs)
        assert len(actions) == 4
        assert all(isinstance(a, DecodedAction) for a in actions)

    def test_decode_tokens(self, decoder):
        """从 token 序列解码"""
        token_ids = [128, 100, 80, 0, 0, 0, 200,  # 第 1 个动作
                      64, 150, 60, 0, 0, 0, 180]   # 第 2 个动作
        actions = decoder.decode_tokens(token_ids)
        assert len(actions) == 2
        assert all(isinstance(a, DecodedAction) for a in actions)

    def test_encode_action(self, decoder):
        """编码动作 → token"""
        action = DecodedAction(
            position=np.array([0.0, 0.0, 0.4], dtype=np.float32),
            rotation=np.array([0.0, 0.0, 0.0], dtype=np.float32),
            gripper=0.5,
        )
        tokens = decoder.encode_action(action)
        assert len(tokens) == 7
        assert all(isinstance(t, int) for t in tokens)
        assert all(0 <= t < 256 for t in tokens)

    def test_encode_decode_roundtrip(self, continuous_decoder):
        """编码→解码 往返一致性"""
        original = DecodedAction(
            position=np.array([0.1, 0.2, 0.3], dtype=np.float32),
            rotation=np.array([0.0, 0.0, 1.57], dtype=np.float32),
            gripper=0.7,
        )
        tokens = continuous_decoder.encode_action(original)
        decoded = continuous_decoder.decode_tokens(tokens)[0]
        # 离散化会有量化误差，允许一定容差
        assert abs(decoded.position[0] - original.position[0]) < 0.01
        assert abs(decoded.gripper - original.gripper) < 0.05

    def test_action_space_defaults(self, decoder):
        """默认动作空间参数"""
        space = decoder._action_space
        assert space.num_bins == 256
        assert space.pos_min.shape == (3,)
        assert space.pos_max.shape == (3,)
        assert space.gripper_min == 0.0
        assert space.gripper_max == 1.0

    def test_decoded_action_as_array(self, decoder):
        """DecodedAction → numpy 数组"""
        action = DecodedAction(
            position=np.array([0.5, 0.3, 0.1], dtype=np.float32),
            rotation=np.array([0.0, 0.0, 1.57], dtype=np.float32),
            gripper=1.0,
        )
        arr = action.as_array()
        assert arr.shape == (7,)
        assert arr[6] == 1.0

    def test_decoded_action_as_dict(self, decoder):
        """DecodedAction → dict"""
        action = DecodedAction(
            position=np.array([0.5, 0.3, 0.1], dtype=np.float32),
            rotation=np.array([0.0, 0.0, 1.57], dtype=np.float32),
            gripper=0.5,
        )
        d = action.as_dict()
        assert "position" in d
        assert "rotation" in d
        assert "gripper" in d
        assert "confidence" in d

    def test_decode_1d_input(self, decoder):
        """1D 输入自动 reshape"""
        model_output = np.array([0.5, 0.3, 0.2, 0.0, 0.0, 0.0, 0.8], dtype=np.float32)
        action = decoder.decode(model_output)
        assert isinstance(action, DecodedAction)

    def test_set_mode(self, decoder):
        """切换解码模式"""
        assert decoder.mode == DecodeMode.MOCK
        decoder.set_mode(DecodeMode.CONTINUOUS)
        assert decoder.mode == DecodeMode.CONTINUOUS

    def test_clip_gripper(self, decoder):
        """夹爪值裁剪到 [0, 1]"""
        model_output = np.array([0.5, 0.3, 0.2, 0.0, 0.0, 0.0, 1.5], dtype=np.float32)
        action = decoder.decode(model_output)
        assert 0.0 <= action.gripper <= 1.0

        model_output2 = np.array([0.5, 0.3, 0.2, 0.0, 0.0, 0.0, -0.5], dtype=np.float32)
        action2 = decoder.decode(model_output2)
        assert 0.0 <= action2.gripper <= 1.0

    def test_decode_empty_tokens(self, decoder):
        """空 token 列表"""
        actions = decoder.decode_tokens([])
        assert actions == []


class TestActionSpace:
    """动作空间测试"""

    def test_default_space(self):
        space = ActionSpace()
        assert space.num_bins == 256
        assert len(space.pos_min) == 3
        assert len(space.rot_min) == 3

    def test_custom_space(self):
        space = ActionSpace(
            pos_min=np.array([-1.0, -1.0, 0.0], dtype=np.float32),
            pos_max=np.array([1.0, 1.0, 1.0], dtype=np.float32),
            num_bins=512,
        )
        assert space.num_bins == 512
        decoder = ActionDecoder(action_space=space)
        assert decoder._action_space.num_bins == 512


class TestDecodedAction:
    """DecodedAction 数据结构测试"""

    def test_creation(self):
        action = DecodedAction(
            position=np.zeros(3, dtype=np.float32),
            rotation=np.zeros(3, dtype=np.float32),
            gripper=0.0,
        )
        assert action.as_array().shape == (7,)

    def test_confidence_default(self):
        action = DecodedAction(
            position=np.zeros(3, dtype=np.float32),
            rotation=np.zeros(3, dtype=np.float32),
            gripper=0.0,
        )
        assert action.confidence == 1.0

    def test_confidence_custom(self):
        action = DecodedAction(
            position=np.zeros(3, dtype=np.float32),
            rotation=np.zeros(3, dtype=np.float32),
            gripper=0.0,
            confidence=0.75,
        )
        assert action.confidence == 0.75
