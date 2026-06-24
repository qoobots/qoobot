"""brain_os SDK — 场景图 + 定位 API

调用 PerceptionService.GetSceneGraph / GetLocalization。
"""

from __future__ import annotations

from typing import Callable, Optional

from ..config import BrainOSConfig


class SceneAPI:
    """调用 PerceptionService 获取场景图和定位信息。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def get(self, *, include_summary: bool = False) -> dict:
        """获取当前场景图。

        Returns:
            {"objects": [...], "relations": [...], "summary": str | None}
        """
        # 尝试 gRPC 调用
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.perception.service_pb2 import GetSceneGraphRequest
                from brain_os.proto_gen.brain_os.perception.service_pb2_grpc import PerceptionServiceStub

                stub = PerceptionServiceStub(channel)
                req = GetSceneGraphRequest(
                    robot_id=self._cfg.robot_id,
                    include_summary=include_summary,
                )
                resp = await stub.GetSceneGraph(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "objects": [self._object_to_dict(o) for o in resp.objects],
                    "relations": [self._relation_to_dict(r) for r in resp.relations],
                    "summary": resp.summary if include_summary else "",
                    "_stub": False,
                }
            except Exception:
                pass  # 退回到 mock

        return {
            "objects": [
                {"object_id": "obj_01", "class_label": "cup", "confidence": 0.93, "pose": None},
                {"object_id": "obj_02", "class_label": "table", "confidence": 0.99, "pose": None},
            ],
            "relations": [
                {"subject_id": "obj_01", "object_id": "obj_02", "relation": "ON"}
            ],
            "summary": "桌上有一个杯子" if include_summary else "",
            "_stub": True,
        }

    async def get_localization(self) -> dict:
        """获取机器人当前位姿（SLAM 输出）。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.perception.service_pb2 import GetLocalizationRequest
                from brain_os.proto_gen.brain_os.perception.service_pb2_grpc import PerceptionServiceStub

                stub = PerceptionServiceStub(channel)
                req = GetLocalizationRequest(robot_id=self._cfg.robot_id)
                resp = await stub.GetLocalization(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "pose": {
                        "position": {"x": resp.pose.position.x, "y": resp.pose.position.y, "z": resp.pose.position.z},
                        "orientation": {"x": resp.pose.orientation.x, "y": resp.pose.orientation.y,
                                        "z": resp.pose.orientation.z, "w": resp.pose.orientation.w},
                    },
                    "covariance": list(resp.covariance) if hasattr(resp, "covariance") else [],
                    "_stub": False,
                }
            except Exception:
                pass

        return {
            "pose": {
                "position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
            },
            "_stub": True,
        }

    @staticmethod
    def _object_to_dict(obj) -> dict:
        return {
            "object_id": getattr(obj, "object_id", ""),
            "class_label": getattr(obj, "class_label", ""),
            "confidence": getattr(obj, "confidence", 0.0),
        }

    @staticmethod
    def _relation_to_dict(rel) -> dict:
        return {
            "subject_id": getattr(rel, "subject_id", ""),
            "object_id": getattr(rel, "object_id", ""),
            "relation": getattr(rel, "relation", ""),
        }
