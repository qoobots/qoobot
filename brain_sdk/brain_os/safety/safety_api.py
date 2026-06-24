"""brain_os SDK — 安全监控 API

调用 SafetyService.GetSafetySnapshot / StreamAlarms / AcknowledgeAlarm / SetVelocityScale。
"""

from __future__ import annotations

from typing import AsyncIterator, Callable

from ..config import BrainOSConfig


class SafetyAPI:
    """调用 SafetyService 进行安全监控。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def get_snapshot(self) -> dict:
        """获取当前安全状态快照。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.safety.service_pb2 import GetSafetySnapshotRequest
                from brain_os.proto_gen.brain_os.safety.service_pb2_grpc import SafetyServiceStub

                stub = SafetyServiceStub(channel)
                req = GetSafetySnapshotRequest(robot_id=self._cfg.robot_id)
                resp = await stub.GetSafetySnapshot(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "state": str(resp.state),
                    "active_alarms": [
                        {"alarm_id": a.alarm_id, "level": a.level, "message": a.message}
                        for a in resp.active_alarms
                    ],
                    "velocity_scale": resp.velocity_scale,
                    "min_obstacle_dist": resp.min_obstacle_dist,
                    "_stub": False,
                }
            except Exception:
                pass

        return {
            "state": "NORMAL",
            "active_alarms": [],
            "velocity_scale": 1.0,
            "min_obstacle_dist": 0.5,
            "_stub": True,
        }

    async def stream_alarms(self, min_level: int = 0) -> AsyncIterator[dict]:
        """订阅安全告警流。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.safety.service_pb2 import StreamAlarmsRequest
                from brain_os.proto_gen.brain_os.safety.service_pb2_grpc import SafetyServiceStub

                stub = SafetyServiceStub(channel)
                req = StreamAlarmsRequest(robot_id=self._cfg.robot_id, min_level=min_level)
                async for alarm in stub.StreamAlarms(req):
                    yield {
                        "alarm_id": alarm.alarm_id,
                        "level": alarm.level,
                        "message": alarm.message,
                        "timestamp_ms": alarm.timestamp_ms,
                        "_stub": False,
                    }
                return
            except Exception:
                pass

        # Empty mock — no alarms
        return
        yield

    async def acknowledge_alarm(self, alarm_id: str, operator: str = "") -> dict:
        """确认并清除告警。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.safety.service_pb2 import AcknowledgeAlarmRequest
                from brain_os.proto_gen.brain_os.safety.service_pb2_grpc import SafetyServiceStub

                stub = SafetyServiceStub(channel)
                req = AcknowledgeAlarmRequest(
                    robot_id=self._cfg.robot_id,
                    alarm_id=alarm_id,
                    operator=operator,
                )
                resp = await stub.AcknowledgeAlarm(req, timeout=self._cfg.grpc_timeout_sec)
                return {"ok": resp.success, "alarm_id": alarm_id, "_stub": False}
            except Exception:
                pass

        return {"ok": True, "alarm_id": alarm_id, "_stub": True}

    async def set_velocity_scale(self, scale: float, *, reason: str = "") -> dict:
        """设置速度缩放因子 ([0, 1])。"""
        scale = max(0.0, min(1.0, scale))

        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.safety.service_pb2 import SetVelocityScaleRequest
                from brain_os.proto_gen.brain_os.safety.service_pb2_grpc import SafetyServiceStub

                stub = SafetyServiceStub(channel)
                req = SetVelocityScaleRequest(
                    robot_id=self._cfg.robot_id,
                    scale=scale,
                    reason=reason,
                )
                resp = await stub.SetVelocityScale(req, timeout=self._cfg.grpc_timeout_sec)
                return {"ok": resp.success, "applied_scale": resp.applied_scale, "_stub": False}
            except Exception:
                pass

        return {"ok": True, "applied_scale": scale, "_stub": True}
