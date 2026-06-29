"""brain_os SDK — 规划执行 API

调用 DecisionService.ExecutePlan / CancelPlan / StreamPlanStatus。
"""

from __future__ import annotations

from typing import AsyncIterator, Callable, Optional

from ..config import BrainOSConfig


class PlanAPI:
    """调用 DecisionService 执行和监控规划。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def execute(self, tree: dict, *, require_hitl: bool = True) -> dict:
        """执行行为树规划。

        Args:
            tree: BehaviorTree dict (来自 TaskAPI.generate_bt)
            require_hitl: 是否在多轨迹时触发 HITL

        Returns:
            {"plan_id": str, "state": str, "hitl_event": dict | None}
        """
        plan_id = tree.get("tree_id", "plan_unknown")

        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.decision.service_pb2 import ExecutePlanRequest
                from brain_os.proto_gen.brain_os.decision.service_pb2_grpc import DecisionServiceStub

                stub = DecisionServiceStub(channel)
                req = ExecutePlanRequest(
                    robot_id=self._cfg.robot_id,
                    tree_xml=tree.get("xml_str", ""),
                    require_hitl=require_hitl,
                )
                resp = await stub.ExecutePlan(req, timeout=self._cfg.grpc_timeout_sec)
                result = {
                    "plan_id": resp.plan_id,
                    "state": str(resp.state),
                    "hitl_event": None,
                    "_stub": False,
                }
                if resp.HasField("hitl_event"):
                    result["hitl_event"] = {
                        "plan_id": resp.plan_id,
                        "candidates": [
                            {"trajectory_id": c.trajectory_id, "score": c.score,
                             "description": c.description, "is_recommended": c.is_recommended}
                            for c in resp.hitl_event.candidates
                        ],
                        "timeout_sec": resp.hitl_event.timeout_sec,
                    }
                return result
            except Exception:
                pass

        result: dict = {
            "plan_id": plan_id,
            "state": "WAITING_HITL" if require_hitl else "EXECUTING",
            "hitl_event": None,
            "_stub": True,
        }
        if require_hitl:
            result["hitl_event"] = {
                "plan_id": plan_id,
                "candidates": [
                    {"trajectory_id": "traj_01", "score": 0.92, "description": "最短路径", "is_recommended": True},
                    {"trajectory_id": "traj_02", "score": 0.85, "description": "最安全路径", "is_recommended": False},
                    {"trajectory_id": "traj_03", "score": 0.78, "description": "最低能耗", "is_recommended": False},
                ],
                "timeout_sec": self._cfg.hitl_timeout_sec,
            }
        return result

    async def cancel(self, plan_id: str, *, reason: str = "") -> dict:
        """取消正在执行的规划。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.decision.service_pb2 import CancelPlanRequest
                from brain_os.proto_gen.brain_os.decision.service_pb2_grpc import DecisionServiceStub

                stub = DecisionServiceStub(channel)
                req = CancelPlanRequest(robot_id=self._cfg.robot_id, plan_id=plan_id, reason=reason)
                resp = await stub.CancelPlan(req, timeout=self._cfg.grpc_timeout_sec)
                return {"ok": resp.success, "plan_id": plan_id, "_stub": False}
            except Exception:
                pass

        return {"ok": True, "plan_id": plan_id, "_stub": True}

    async def stream_status(self, plan_id: str) -> AsyncIterator[dict]:
        """流式订阅规划执行状态。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.decision.service_pb2 import StreamPlanStatusRequest
                from brain_os.proto_gen.brain_os.decision.service_pb2_grpc import DecisionServiceStub

                stub = DecisionServiceStub(channel)
                req = StreamPlanStatusRequest(robot_id=self._cfg.robot_id, plan_id=plan_id)
                async for update in stub.StreamPlanStatus(req):
                    yield {
                        "plan_id": update.plan_id,
                        "state": str(update.state),
                        "progress": update.progress,
                        "message": update.message,
                        "_stub": False,
                    }
                return
            except Exception:
                pass

        for progress in [0.0, 0.25, 0.5, 0.75, 1.0]:
            yield {
                "plan_id": plan_id,
                "state": "EXECUTING" if progress < 1.0 else "SUCCEEDED",
                "progress": progress,
                "_stub": True,
            }
