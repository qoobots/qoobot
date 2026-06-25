"""brain_os SDK — 目标检测查询 API

调用 PerceptionService.QueryObjects。
"""

from __future__ import annotations

from typing import Callable, List

from ..config import BrainOSConfig


class ObjectAPI:
    """调用 PerceptionService 查询场景中的目标。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def query(
        self,
        *,
        class_label: str = "",
        min_confidence: float = 0.5,
        max_results: int = 10,
    ) -> List[dict]:
        """按类别检索场景中的目标。

        Args:
            class_label: 目标类别，空表示全部
            min_confidence: 置信度阈值
            max_results: 最多返回条数
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.perception.service_pb2 import QueryObjectsRequest
                from brain_os.proto_gen.brain_os.perception.service_pb2_grpc import PerceptionServiceStub

                stub = PerceptionServiceStub(channel)
                req = QueryObjectsRequest(
                    robot_id=self._cfg.robot_id,
                    class_label=class_label,
                    min_confidence=min_confidence,
                    max_results=max_results,
                )
                resp = await stub.QueryObjects(req, timeout=self._cfg.grpc_timeout_sec)
                return [
                    {
                        "object_id": obj.object_id,
                        "class_label": obj.class_label,
                        "confidence": obj.confidence,
                        "_stub": False,
                    }
                    for obj in resp.objects
                ]
            except Exception:
                pass

        stub_objects = [
            {"object_id": "obj_01", "class_label": "cup", "confidence": 0.93},
            {"object_id": "obj_02", "class_label": "bottle", "confidence": 0.87},
            {"object_id": "obj_03", "class_label": "table", "confidence": 0.99},
        ]
        filtered = [
            o
            for o in stub_objects
            if (not class_label or o["class_label"] == class_label)
            and o["confidence"] >= min_confidence
        ]
        for o in filtered:
            o["_stub"] = True
        return filtered[:max_results]
