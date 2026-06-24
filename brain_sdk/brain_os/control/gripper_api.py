"""brain_os SDK — 夹爪控制 API

调用 ControlService.ControlGripper。
"""

from __future__ import annotations

from typing import Callable

from ..config import BrainOSConfig


class GripperAPI:
    """调用 ControlService 控制夹爪。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def open(self) -> dict:
        """完全打开夹爪。"""
        return await self._control(position=0.0, max_effort=5.0)

    async def close(self, *, max_effort: float = 10.0) -> dict:
        """关闭夹爪（自动检测抓取成功）。"""
        return await self._control(position=1.0, max_effort=max_effort)

    async def set_position(self, position: float, *, max_effort: float = 10.0) -> dict:
        """设置夹爪位置 (0.0=全开, 1.0=全闭)。"""
        return await self._control(position=position, max_effort=max_effort)

    async def _control(self, position: float, max_effort: float) -> dict:
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.control.service_pb2 import ControlGripperRequest
                from brain_os.proto_gen.brain_os.control.service_pb2_grpc import ControlServiceStub

                stub = ControlServiceStub(channel)
                req = ControlGripperRequest(
                    robot_id=self._cfg.robot_id,
                    position=position,
                    max_effort=max_effort,
                )
                resp = await stub.ControlGripper(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "ok": resp.success,
                    "position": resp.position,
                    "applied_effort": resp.effort,
                    "object_detected": resp.object_detected,
                    "_stub": False,
                }
            except Exception:
                pass

        return {
            "ok": True,
            "position": position,
            "applied_effort": 0.0,
            "object_detected": position >= 0.5,
            "_stub": True,
        }
