"""brain_os SDK — 知识检索 API

调用 KnowledgeService.SearchKnowledge / ListSkills。
"""

from __future__ import annotations

from typing import Callable, List

from ..config import BrainOSConfig


class KnowledgeSearchAPI:
    """调用 KnowledgeService 进行知识检索和技能查询。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def search_knowledge(
        self,
        query: str,
        *,
        knowledge_type: int = 0,
        top_k: int = 5,
    ) -> List[dict]:
        """检索知识条目。

        Returns:
            [{entry_id, type, content, confidence}, ...]
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.knowledge.service_pb2 import SearchKnowledgeRequest
                from brain_os.proto_gen.brain_os.knowledge.service_pb2_grpc import KnowledgeServiceStub

                stub = KnowledgeServiceStub(channel)
                req = SearchKnowledgeRequest(
                    robot_id=self._cfg.robot_id,
                    query=query,
                    knowledge_type=knowledge_type,
                    top_k=top_k,
                )
                resp = await stub.SearchKnowledge(req, timeout=self._cfg.grpc_timeout_sec)
                return [
                    {
                        "entry_id": e.entry_id,
                        "type": str(e.type),
                        "content": e.content,
                        "confidence": e.confidence,
                        "_stub": False,
                    }
                    for e in resp.entries
                ]
            except Exception:
                pass

        return [
            {
                "entry_id": "ke_01",
                "type": "FACT",
                "content": f"与 '{query}' 相关的知识条目",
                "confidence": 0.88,
                "_stub": True,
            }
        ]

    async def list_skills(self, tag_filter: str = "") -> List[dict]:
        """列出已注册的技能。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.knowledge.service_pb2 import ListSkillsRequest
                from brain_os.proto_gen.brain_os.knowledge.service_pb2_grpc import KnowledgeServiceStub

                stub = KnowledgeServiceStub(channel)
                req = ListSkillsRequest(
                    robot_id=self._cfg.robot_id,
                    tag_filter=tag_filter,
                )
                resp = await stub.ListSkills(req, timeout=self._cfg.grpc_timeout_sec)
                return [
                    {
                        "skill_id": s.skill_id,
                        "name": s.name,
                        "description": s.description,
                        "_stub": False,
                    }
                    for s in resp.skills
                ]
            except Exception:
                pass

        return [
            {"skill_id": "sk_01", "name": "NavigateTo", "description": "导航到指定位置", "_stub": True},
            {"skill_id": "sk_02", "name": "Pick", "description": "抓取目标物体", "_stub": True},
            {"skill_id": "sk_03", "name": "Place", "description": "放置物体到目标位置", "_stub": True},
            {"skill_id": "sk_04", "name": "Inspect", "description": "检查/观察目标", "_stub": True},
        ]
