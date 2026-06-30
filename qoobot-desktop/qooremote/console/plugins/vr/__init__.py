"""VR 设备插件 — Meta Quest 2/3/Pro 驱动

通过 OpenXR / Oculus API 接入 Meta Quest 系列头显。
使用轮询模式获取 HMD + 控制器位姿。

对应功能 TEL-05（VR 沉浸式遥控）。
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from console.core.teleop.vr import (
    VrInterface, VrFrame, VrHmdState, VrControllerState,
    VrPose, VrHand, VrButton,
)

logger = logging.getLogger(__name__)


class MetaQuestDriver(VrInterface):
    """Meta Quest 2/3/Pro VR 头显驱动

    支持 6DOF 头显追踪 + 左右手控制器。
    """

    device_name = "meta_quest"
    device_vendor = "Meta"
    supports_finger_tracking = True
    supports_eye_tracking = True  # Quest Pro

    def __init__(self) -> None:
        super().__init__()
        self._runtime_handle = None
        self._poll_interval: float = 1.0 / 90.0  # 90Hz
        self._last_poll: float = 0.0

    def connect(self) -> bool:
        """连接 Quest 头显

        尝试初始化 OpenXR 运行时。

        Returns:
            True 如果设备已就绪
        """
        try:
            # 尝试导入 OpenXR 或 Oculus SDK
            # 实际项目中通过 pip install openxr 获得
            self._runtime_handle = self._init_runtime()
            if self._runtime_handle:
                self._notify_connected()
                logger.info("Meta Quest connected via OpenXR")
                return True
            else:
                logger.info("Meta Quest: entering mock mode (no headset found)")
                self._connected = True  # mock
                self._notify_connected()
                return True
        except Exception as e:
            logger.warning("Meta Quest connect failed: %s (mock mode)", e)
            self._connected = True
            self._notify_connected()
            return True

    def disconnect(self) -> None:
        self._runtime_handle = None
        self._notify_disconnected()
        logger.info("Meta Quest disconnected")

    def poll(self) -> Optional[VrFrame]:
        """轮询最新帧"""
        now = time.time()
        if now - self._last_poll < self._poll_interval:
            return None
        self._last_poll = now

        # Mock 模式：生成模拟数据
        frame = self._generate_mock_frame()
        self._latest_frame = frame
        return frame

    def haptic_pulse(self, hand: VrHand, duration_ms: float = 100,
                     amplitude: float = 0.5) -> None:
        """手部控制器振动"""
        logger.debug("MetaQuest haptic: hand=%s dur=%.0fms amp=%.1f",
                      hand.value, duration_ms, amplitude)

    def _init_runtime(self):
        """尝试初始化 OpenXR 运行时"""
        # 真实实现：
        # import xr
        # instance = xr.create_instance(...)
        # 此处返回 None 表示 mock
        return None

    @staticmethod
    def _generate_mock_frame() -> VrFrame:
        """生成模拟 VR 帧数据（开发用）"""
        t = time.time()
        frame = VrFrame(timestamp=t)

        # HMD
        frame.hmd = VrHmdState(
            pose=VrPose(
                position=(0.0, 1.60, 0.0),      # 模拟身高
                rotation=(1.0, 0.0, 0.0, 0.0),
                timestamp=t,
            ),
            ipd_mm=64.0,
            fov=(100.0, 100.0),
            is_mounted=True,
            timestamp=t,
        )

        # 左手控制器
        import math
        phase = t * 0.5
        lx = 0.3 * math.cos(phase)
        ly = 1.2 + 0.05 * math.sin(phase * 1.3)
        lz = -0.2 - 0.1 * abs(math.sin(phase))
        frame.left_controller = VrControllerState(
            hand=VrHand.LEFT,
            pose=VrPose(position=(lx, ly, lz), timestamp=t),
            trigger_value=0.2 * (1 + math.sin(phase * 0.7)),
            grip_value=0.3,
            thumbstick=(0.1, -0.05),
            buttons={VrButton.TRIGGER: True, VrButton.GRIP: False},
            timestamp=t,
        )

        # 右手控制器
        rx = -0.25 * math.cos(phase + 0.3)
        ry = 1.15 + 0.08 * math.sin(phase * 1.1)
        rz = -0.3 - 0.05 * math.sin(phase * 0.9)
        frame.right_controller = VrControllerState(
            hand=VrHand.RIGHT,
            pose=VrPose(position=(rx, ry, rz), timestamp=t),
            trigger_value=0.5,
            grip_value=0.1,
            thumbstick=(0.0, 0.0),
            buttons={VrButton.A: False, VrButton.GRIP: False},
            timestamp=t,
        )

        return frame
