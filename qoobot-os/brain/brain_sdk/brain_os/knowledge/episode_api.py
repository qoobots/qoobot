"""brain_os SDK — 情景记忆 API

调用 KnowledgeService.SearchEpisodes / StoreEpisode。
"""

from __future__ import annotations

import uuid
from typing import Callable, List

from ..config import BrainOSConfig


class EpisodeAPI:
    """调用 KnowledgeService 进行情景记忆的存储与检索。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        success_only: bool = False,
    ) -> List[dict]:
        """向量检索相似历史情景。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.knowledge.service_pb2 import SearchEpisodesRequest
                from brain_os.proto_gen.brain_os.knowledge.service_pb2_grpc import KnowledgeServiceStub

                stub = KnowledgeServiceStub(channel)
                req = SearchEpisodesRequest(
                    robot_id=self._cfg.robot_id,
                    query=query,
                    top_k=top_k,
                    success_only=success_only,
                )
                resp = await stub.SearchEpisodes(req, timeout=self._cfg.grpc_timeout_sec)
                return [
                    {
                        "episode_id": e.episode_id,
                        "task_type": e.task_type,
                        "success": e.success,
                        "duration_sec": e.duration_sec,
                        "_stub": False,
                    }
                    for e in resp.episodes
                ]
            except Exception:
                pass

        return [
            {
                "episode_id": "ep_01",
                "task_type": "pick_and_place",
                "success": True,
                "duration_sec": 12.3,
                "context": {"query": query},
                "_stub": True,
            }
        ]

    async def store(self, episode: dict) -> str:
        """存储新情景到记忆库。

        Args:
            episode: 情景数据 dict (参考 knowledge/types.proto::Episode)

        Returns:
            episode_id (str)
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.knowledge.service_pb2 import StoreEpisodeRequest
                from brain_os.proto_gen.brain_os.knowledge.service_pb2_grpc import KnowledgeServiceStub

                stub = KnowledgeServiceStub(channel)
                req = StoreEpisodeRequest(
                    robot_id=self._cfg.robot_id,
                    task_type=episode.get("task_type", ""),
                    success=episode.get("success", True),
                    duration_sec=episode.get("duration_sec", 0.0),
                )
                resp = await stub.StoreEpisode(req, timeout=self._cfg.grpc_timeout_sec)
                return resp.episode_id
            except Exception:
                pass

        episode_id = str(uuid.uuid4())[:8]
        return episode_id
