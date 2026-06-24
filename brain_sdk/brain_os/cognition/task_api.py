"""brain_os SDK — 任务分解 + 行为树 API

调用 CognitionService.DecomposeTask / GenerateBehaviorTree。
"""

from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from ..config import BrainOSConfig


class TaskAPI:
    """调用 CognitionService 进行任务分解和行为树生成。"""

    def __init__(
        self, get_channel: Callable, get_async_channel: Callable, config: BrainOSConfig
    ) -> None:
        self._get_ch = get_channel
        self._get_ach = get_async_channel
        self._cfg = config
        self._enable_mock: bool = False

    async def decompose(
        self, intent: dict, *, scene_graph: Optional[dict] = None
    ) -> dict:
        """将意图分解为子任务序列。

        Returns:
            {"plan_id": str, "subtasks": List[dict], "rationale": str}
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.cognition.service_pb2 import DecomposeTaskRequest
                from brain_os.proto_gen.brain_os.cognition.service_pb2_grpc import CognitionServiceStub

                stub = CognitionServiceStub(channel)
                req = DecomposeTaskRequest(
                    robot_id=self._cfg.robot_id,
                    intent_type=intent.get("type", "UNKNOWN"),
                    intent_params=intent.get("params", {}),
                )
                resp = await stub.DecomposeTask(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "plan_id": resp.plan_id,
                    "subtasks": [
                        {
                            "task_id": st.task_id,
                            "skill_name": st.skill_name,
                            "parameters": dict(st.parameters),
                            "depends_on": list(st.depends_on),
                            "status": str(st.status),
                        }
                        for st in resp.subtasks
                    ],
                    "rationale": resp.rationale,
                    "_stub": False,
                }
            except Exception:
                pass

        plan_id = str(uuid.uuid4())[:8]
        return {
            "plan_id": plan_id,
            "subtasks": [
                {"task_id": "st_01", "skill_name": "NavigateTo", "parameters": {}, "depends_on": [], "status": "PENDING"},
                {"task_id": "st_02", "skill_name": "Pick", "parameters": {"target": "red_cup"}, "depends_on": ["st_01"], "status": "PENDING"},
            ],
            "rationale": f"根据意图 {intent.get('type')} 生成 2 步计划",
            "_stub": True,
        }

    async def generate_bt(self, plan_id: str, subtasks: List[dict]) -> dict:
        """将子任务序列转换为 BehaviorTree.CPP XML。

        Returns:
            {"tree_id": str, "xml_str": str}
        """
        if not self._enable_mock:
            try:
                channel = await self._get_ach()
                from brain_os.proto_gen.brain_os.cognition.service_pb2 import GenerateBehaviorTreeRequest
                from brain_os.proto_gen.brain_os.cognition.service_pb2_grpc import CognitionServiceStub

                stub = CognitionServiceStub(channel)
                req = GenerateBehaviorTreeRequest(
                    robot_id=self._cfg.robot_id,
                    plan_id=plan_id,
                    subtask_ids=[st.get("task_id", "") for st in subtasks],
                )
                resp = await stub.GenerateBehaviorTree(req, timeout=self._cfg.grpc_timeout_sec)
                return {
                    "tree_id": resp.tree_id,
                    "xml_str": resp.tree_xml,
                    "_stub": False,
                }
            except Exception:
                pass

        xml_stub = f"""<root BTCPP_format="4">
  <BehaviorTree ID="plan_{plan_id}">
    <Sequence>
      <NavigateTo target="{{target_location}}"/>
      <Pick object="{{target_object}}"/>
    </Sequence>
  </BehaviorTree>
</root>"""
        return {
            "tree_id": f"bt_{plan_id}",
            "xml_str": xml_stub,
            "_stub": True,
        }
