"""HTC Vive / Valve Index VR 驱动

通过 SteamVR / OpenVR API 接入 HTC Vive 系列头显。

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


class HtcViveDriver(VrInterface):
    """HTC Vive / Vive Pro / Valve Index 头显驱动

    通过 OpenVR (SteamVR) 接入，支持 Lighthouse 追踪生态。
    """

    device_name = "htc_vive"
    device_vendor = "HTC / Valve"
    supports_finger_tracking = True  # Valve Index 控制器支持
    supports_eye_tracking = True     # Vive Pro Eye

    def __init__(self) -> None:
        super().__init__()
        self._vr_system = None
        self._tracked_devices: dict[int, str] = {}  # device_index -> role
        self._poll_interval: float = 1.0 / 90.0
        self._last_poll: float = 0.0

    def connect(self) -> bool:
        """连接 SteamVR 运行时"""
        try:
            # 真实实现：
            # import openvr
            # openvr.init(openvr.VRApplication_Scene)
            # self._vr_system = openvr.VRSystem()
            self._vr_system = None  # mock
            self._notify_connected()
            logger.info("HTC Vive connected (mock mode)")
            return True
        except Exception as e:
            logger.warning("HTC Vive connect failed: %s (mock mode)", e)
            self._connected = True
            self._notify_connected()
            return True

    def disconnect(self) -> None:
        self._vr_system = None
        self._notify_disconnected()
        logger.info("HTC Vive disconnected")

    def poll(self) -> Optional[VrFrame]:
        now = time.time()
        if now - self._last_poll < self._poll_interval:
            return None
        self._last_poll = now

        frame = self._generate_mock_frame()
        self._latest_frame = frame
        return frame

    def haptic_pulse(self, hand: VrHand, duration_ms: float = 100,
                     amplitude: float = 0.5) -> None:
        """手部控制器振动"""
        logger.debug("HTCVive haptic: hand=%s dur=%.0fms", hand.value, duration_ms)

    @staticmethod
    def _generate_mock_frame() -> VrFrame:
        """生成模拟 VR 帧（开发用）"""
        t = time.time()
        import math

        frame = VrFrame(timestamp=t)
        frame.tracking_quality = 0.95

        # HMD — Lighthouse 追踪精度更高
        frame.hmd = VrHmdState(
            pose=VrPose(
                position=(0.0, 1.65, 0.0),
                timestamp=t,
            ),
            ipd_mm=63.5,
            fov=(110.0, 110.0),  # Vive 110° diagonal
            is_mounted=True,
            timestamp=t,
        )

        # Left (Vive Wand / Index Controller)
        frame.left_controller = VrControllerState(
            hand=VrHand.LEFT,
            pose=VrPose(
                position=(-0.4, 1.3, -0.3),
                timestamp=t,
            ),
            trigger_value=0.0,
            grip_value=0.0,
            trackpad=(0.0, 0.0),
            buttons={},
            timestamp=t,
        )

        # Right
        frame.right_controller = VrControllerState(
            hand=VrHand.RIGHT,
            pose=VrPose(
                position=(0.4, 1.3, -0.35),
                timestamp=t,
            ),
            trigger_value=0.0,
            grip_value=0.0,
            trackpad=(0.0, 0.0),
            buttons={},
            timestamp=t,
        )

        return frame
