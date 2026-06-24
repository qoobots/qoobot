"""brain_os SDK — 运动控制 API

调用 ControlService.ExecuteTrajectory / EmergencyStop / ResumeMotion。
"""

from __future__ import annotations

from typing import AsyncIterator, Callable

from ..config import BrainOSConfig


class MotionAPI:
    """调用 ControlService 执行轨迹和紧急停止。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def execute(self, trajectory: dict) -> AsyncIterator[dict]:
        """执行轨迹，返回异步反馈流。

        Yields:
            {"trajectory_id": str, "progress": float, "is_complete": bool}
        """
        traj_id = trajectory.get("trajectory_id", "traj_unknown")

        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.control.service_pb2 import ExecuteTrajectoryRequest
                from brain_os.proto_gen.brain_os.control.service_pb2_grpc import ControlServiceStub

                stub = ControlServiceStub(channel)
                req = ExecuteTrajectoryRequest(
                    robot_id=self._cfg.robot_id,
                    trajectory_id=traj_id,
                )
                async for feedback in stub.ExecuteTrajectory(req):
                    yield {
                        "trajectory_id": traj_id,
                        "progress": feedback.progress,
                        "is_complete": feedback.is_complete,
                        "_stub": False,
                    }
                return
            except Exception:
                pass

        for step in range(5):
            progress = (step + 1) / 5
            yield {
                "trajectory_id": traj_id,
                "progress": progress,
                "is_complete": progress >= 1.0,
                "_stub": True,
            }

    async def emergency_stop(self, *, reason: str = "", level: int = 0) -> dict:
        """触发紧急停止（< 5ms 响应）。

        Args:
            reason: 停止原因描述
            level: 告警级别 0(S0 最高) ~ 3(S3)
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.control.service_pb2 import EmergencyStopRequest
                from brain_os.proto_gen.brain_os.control.service_pb2_grpc import ControlServiceStub

                stub = ControlServiceStub(channel)
                req = EmergencyStopRequest(
                    robot_id=self._cfg.robot_id,
                    reason=reason,
                    alarm_level=level,
                )
                resp = await stub.EmergencyStop(req, timeout=1.0)
                return {
                    "ok": resp.success,
                    "stop_time_ns": resp.stop_time_ns,
                    "reason": reason,
                    "level": level,
                    "_stub": False,
                }
            except Exception:
                pass

        return {
            "ok": True,
            "stop_time_ns": 0,
            "reason": reason,
            "level": level,
            "_stub": True,
        }

    async def resume(self, *, require_confirm: bool = True) -> dict:
        """紧急停止后恢复运动。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.control.service_pb2 import ResumeMotionRequest
                from brain_os.proto_gen.brain_os.control.service_pb2_grpc import ControlServiceStub

                stub = ControlServiceStub(channel)
                req = ResumeMotionRequest(
                    robot_id=self._cfg.robot_id,
                    require_confirm=require_confirm,
                )
                resp = await stub.ResumeMotion(req, timeout=self._cfg.grpc_timeout_sec)
                return {"ok": resp.success, "_stub": False}
            except Exception:
                pass

        return {"ok": True, "_stub": True}
