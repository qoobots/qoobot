"""
brain_ai/grpc_server/cognition_service.py — CognitionService gRPC implementation.

Implements:
  - ParseIntent:            NL → Intent
  - DecomposeTask:           Intent → SubTask list
  - GenerateBehaviorTree:    Task → BT XML
  - Clarify:                 multi-turn clarification

All servicer methods use the actual proto-generated message types from
brain_ai/proto_gen/brain_os/cognition/.
"""
from __future__ import annotations

import logging
import sys
import os

import grpc

# Add proto_gen/ to sys.path for the generated imports to resolve
_PROTO_GEN = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "proto_gen")
)
if _PROTO_GEN not in sys.path:
    sys.path.insert(0, _PROTO_GEN)

from brain_os.cognition import (  # noqa: E402
    service_pb2,
    service_pb2_grpc,
)
from brain_os.cognition import types_pb2 as cognition_types
from brain_os.common import types_pb2 as common_types

logger = logging.getLogger(__name__)


class CognitionServiceServicer(service_pb2_grpc.CognitionServiceServicer):
    """gRPC servicer for CognitionService (LLM-backed, stub for Sprint 1)."""

    def __init__(self):
        super().__init__()
        logger.info("[CognitionService] Initialized (gRPC servicer).")

    # ── ParseIntent ──────────────────────────────────────────────────────

    def ParseIntent(
        self,
        request: service_pb2.ParseIntentRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.ParseIntentResponse:
        """Parse a natural-language instruction into a structured Intent."""
        logger.info(f"[CognitionService] ParseIntent: '{request.utterance[:60]}' "
                    f"lang={request.language}")

        # TODO(Sprint 2): call IntentParser LLM agent
        # Stub: return INTENT_PICK with high confidence
        intent = cognition_types.Intent(
            type=cognition_types.INTENT_PICK,
            raw_text=request.utterance,
            confidence=0.92,
            language=request.language,
        )

        return service_pb2.ParseIntentResponse(
            status=common_types.Status(code=0, message="ok"),
            intent=intent,
            candidates=[],
        )

    # ── DecomposeTask ──────────────────────────────────────────────────────

    def DecomposeTask(
        self,
        request: service_pb2.DecomposeTaskRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.DecomposeTaskResponse:
        """Decompose an Intent into an ordered list of SubTasks."""
        import google.protobuf.struct_pb2 as spb
        intent = request.intent
        logger.info(f"[CognitionService] DecomposeTask: "
                    f"type={cognition_types.IntentType.Name(intent.type)} "
                    f"text={intent.raw_text[:40]}")

        target_param = spb.Struct()
        target_param["target"] = intent.raw_text

        # TODO(Sprint 2): call TaskDecomposer LLM agent
        subtasks = [
            cognition_types.SubTask(
                task_id="sub-001",
                skill_name="LocateObject",
                parameters=target_param,
                depends_on=[],
                status=cognition_types.TASK_PENDING,
            ),
            cognition_types.SubTask(
                task_id="sub-002",
                skill_name="NavigateTo",
                parameters=target_param,
                depends_on=["sub-001"],
                status=cognition_types.TASK_PENDING,
            ),
            cognition_types.SubTask(
                task_id="sub-003",
                skill_name="PickObject",
                parameters=target_param,
                depends_on=["sub-002"],
                status=cognition_types.TASK_PENDING,
            ),
            cognition_types.SubTask(
                task_id="sub-004",
                skill_name="PlaceObject",
                parameters=target_param,
                depends_on=["sub-003"],
                status=cognition_types.TASK_PENDING,
            ),
        ]

        return service_pb2.DecomposeTaskResponse(
            status=common_types.Status(code=0, message="ok"),
            plan_id="plan-001",
            subtasks=subtasks,
            rationale="Standard pick-and-place decomposition for tabletop scenario.",
        )

    # ── GenerateBehaviorTree ──────────────────────────────────────────────

    def GenerateBehaviorTree(
        self,
        request: service_pb2.GenerateBTRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.GenerateBTResponse:
        """Generate a BehaviorTree XML from a task plan."""
        logger.info(f"[CognitionService] GenerateBT: plan_id={request.plan_id} "
                    f"({len(request.subtasks)} subtasks)")

        # TODO(Sprint 4): call BTGenerator LLM agent
        skill_names = [s.skill_name for s in request.subtasks]
        actions = "\n".join(
            f'      <{s} name="{s.lower()}" object="{{target}}"/>'
            for s in skill_names
        ) if skill_names else '      <NavigateTo name="navigate" target="unknown"/>'

        xml = (
            '<root BTCPP_format="4">'
            '  <BehaviorTree ID="MainTree">'
            '    <Sequence name="task_seq">'
            f'{actions}'
            '    </Sequence>'
            '  </BehaviorTree>'
            '</root>'
        )

        return service_pb2.GenerateBTResponse(
            status=common_types.Status(code=0, message="ok"),
            tree=cognition_types.BehaviorTree(
                tree_id=f"bt-{request.plan_id}",
                xml_str=xml,
                description=f"BT for plan {request.plan_id}",
            ),
        )

    # ── Clarify ───────────────────────────────────────────────────────────

    def Clarify(
        self,
        request: service_pb2.ClarifyRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.ClarifyResponse:
        """Multi-turn clarification: refine intent based on user answer."""
        logger.info(f"[CognitionService] Clarify: "
                    f"q='{request.question}' a='{request.user_answer}'")

        # TODO(Sprint 2): call LLM clarification agent
        refined = cognition_types.Intent(
            type=request.original_intent.type,
            raw_text=request.user_answer or request.original_intent.raw_text,
            confidence=0.95,
            language=request.original_intent.language,
        )

        return service_pb2.ClarifyResponse(
            status=common_types.Status(code=0, message="ok"),
            refined_intent=refined,
        )
