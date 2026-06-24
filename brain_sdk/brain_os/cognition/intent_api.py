"""brain_os SDK — 意图解析 API

调用 CognitionService.ParseIntent / Clarify。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..config import BrainOSConfig


class IntentAPI:
    """调用 CognitionService 解析自然语言指令为意图结构。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def parse(
        self,
        utterance: str,
        *,
        language: str = "zh-CN",
        context: Optional[List[Dict[str, Any]]] = None,
    ) -> dict:
        """解析自然语言指令，返回意图结构。

        Args:
            utterance: 原始指令文本
            language: 语言代码
            context: 多轮对话上下文
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.cognition.service_pb2 import ParseIntentRequest
                from brain_os.proto_gen.brain_os.cognition.service_pb2_grpc import CognitionServiceStub

                stub = CognitionServiceStub(channel)
                req = ParseIntentRequest(
                    robot_id=self._cfg.robot_id,
                    utterance=utterance,
                    language=language,
                )
                resp = await stub.ParseIntent(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "type": str(getattr(resp.intent, "type", "UNKNOWN")),
                    "raw_text": utterance,
                    "confidence": getattr(resp.intent, "confidence", 0.0),
                    "params": dict(getattr(resp.intent, "params", {})),
                    "_stub": False,
                }
            except Exception:
                pass

        return {
            "type": "PICK",
            "raw_text": utterance,
            "confidence": 0.95,
            "params": {},
            "language": language,
            "_stub": True,
        }

    async def clarify(self, question: str, answer: str, original_intent: dict) -> dict:
        """多轮澄清：根据用户回答精炼意图。"""
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.cognition.service_pb2 import ClarifyRequest
                from brain_os.proto_gen.brain_os.cognition.service_pb2_grpc import CognitionServiceStub

                stub = CognitionServiceStub(channel)
                req = ClarifyRequest(
                    robot_id=self._cfg.robot_id,
                    question=question,
                    answer=answer,
                )
                resp = await stub.Clarify(req, timeout=self._cfg.grpc_timeout_sec)
                return {"type": str(resp.intent.type), "confidence": resp.intent.confidence, "_stub": False}
            except Exception:
                pass

        return {**original_intent, "_clarified": True, "_stub": True}
