"""brain_os SDK — 轨迹生成 + HITL 选择 API

调用 DecisionService.GenerateTrajectories / SelectTrajectory。
"""

from __future__ import annotations

from typing import Callable, List, Optional

from ..config import BrainOSConfig


class TrajectoryAPI:
    """调用 DecisionService 进行轨迹生成和选择。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def generate(
        self,
        plan_id: str,
        target_pose: dict,
        *,
        num_candidates: int = 3,
    ) -> List[dict]:
        """生成多条候选轨迹。

        Returns:
            轨迹列表，每条包含 trajectory_id, score, description, is_recommended
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.decision.service_pb2 import GenerateTrajectoriesRequest
                from brain_os.proto_gen.brain_os.decision.service_pb2_grpc import DecisionServiceStub

                stub = DecisionServiceStub(channel)
                req = GenerateTrajectoriesRequest(
                    robot_id=self._cfg.robot_id,
                    plan_id=plan_id,
                    num_candidates=num_candidates,
                )
                resp = await stub.GenerateTrajectories(req, timeout=self._cfg.grpc_timeout_sec)
                return [
                    {
                        "trajectory_id": t.trajectory_id,
                        "score": t.score,
                        "description": t.description,
                        "is_recommended": t.is_recommended,
                        "_stub": False,
                    }
                    for t in resp.trajectories
                ]
            except Exception:
                pass

        return [
            {
                "trajectory_id": f"traj_0{i + 1}",
                "score": round(0.95 - i * 0.07, 2),
                "description": ["最短路径", "最安全路径", "最低能耗"][i],
                "is_recommended": i == 0,
                "_stub": True,
            }
            for i in range(min(num_candidates, 3))
        ]

    async def select(self, plan_id: str, trajectory_id: str = "") -> dict:
        """提交 HITL 轨迹选择。trajectory_id 为空表示接受推荐方案。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.decision.service_pb2 import SelectTrajectoryRequest
                from brain_os.proto_gen.brain_os.decision.service_pb2_grpc import DecisionServiceStub

                stub = DecisionServiceStub(channel)
                req = SelectTrajectoryRequest(
                    robot_id=self._cfg.robot_id,
                    plan_id=plan_id,
                    trajectory_id=trajectory_id or "",
                )
                resp = await stub.SelectTrajectory(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "ok": resp.success,
                    "plan_id": plan_id,
                    "selected": trajectory_id or "auto_recommended",
                    "_stub": False,
                }
            except Exception:
                pass

        return {
            "ok": True,
            "plan_id": plan_id,
            "selected": trajectory_id or "auto_recommended",
            "_stub": True,
        }
