"""
brain_ai/llm_agent/brain_agent.py — Main LLM Agent orchestrator.

Coordinates: intent parsing → task decomposition → BT generation → HITL → execution.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from brain_ai.llm_agent.function_calling import FunctionCallParser
from brain_ai.llm_agent.intent_parser import IntentParser
from brain_ai.llm_agent.prompt_builder import PromptBuilder
from brain_ai.llm_agent.task_decomposer import TaskDecomposer
from brain_ai.llm_agent.bt_generator import BTGenerator
from brain_ai.model_runtime.runtime_factory import RuntimeFactory

logger = logging.getLogger(__name__)


class BrainAgent:
    """
    Top-level agent that transforms natural language into an execution plan.

    Pipeline:
        instruction → IntentParser → TaskDecomposer → BTGenerator → ExecutionPlan

    Usage:
        agent = BrainAgent(runtime_factory=factory)
        plan = await agent.process("把红色杯子放到桌子右侧")
    """

    def __init__(
        self,
        runtime_factory: Optional[RuntimeFactory] = None,
        config: Optional[dict] = None,
    ) -> None:
        cfg = config or {}
        self._factory      = runtime_factory or RuntimeFactory(cfg.get("model_runtime", {}))
        self._prompt_builder = PromptBuilder()
        self._parser         = FunctionCallParser()
        self._intent_parser  = IntentParser()
        self._decomposer     = TaskDecomposer()
        self._bt_generator   = BTGenerator()

        # Event callbacks (optional, wired up by gRPC server)
        self._on_intent_ready: Optional[Callable] = None
        self._on_plan_ready:   Optional[Callable] = None

        logger.info("BrainAgent initialized.")

    # ─── Public API ────────────────────────────────────────────

    async def process(
        self,
        instruction: str,
        scene_context: Optional[dict] = None,
        hitl_callback: Optional[Callable] = None,
    ) -> dict:
        """
        Full pipeline: instruction → execution plan.

        Returns:
            {
              "intent":    { action, target, ... },
              "subtasks":  [ { skill_name, parameters, ... }, ... ],
              "bt_xml":    "<BehaviorTree>...</BehaviorTree>",
              "plan_id":   "...",
            }
        """
        logger.info(f"Processing instruction: {instruction!r}")

        # 1. Parse intent
        intent = await self._parse_intent(instruction, scene_context)
        logger.info(f"Intent: {intent}")
        if self._on_intent_ready:
            self._on_intent_ready(intent)

        # 2. Decompose into subtasks
        subtasks = await self._decompose(intent, scene_context)
        logger.info(f"Subtasks: {len(subtasks)}")

        # 3. Generate behavior tree
        bt_xml = await self._generate_bt(subtasks, scene_context)
        logger.debug(f"BT XML length: {len(bt_xml)}")

        plan = {
            "intent":   intent,
            "subtasks": subtasks,
            "bt_xml":   bt_xml,
            "plan_id":  self._make_plan_id(instruction),
        }

        if self._on_plan_ready:
            self._on_plan_ready(plan)

        return plan

    def process_sync(
        self,
        instruction: str,
        scene_context: Optional[dict] = None,
    ) -> dict:
        """Synchronous wrapper for non-async callers."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.process(instruction, scene_context))

    # ─── Pipeline steps ────────────────────────────────────────

    async def _parse_intent(
        self,
        instruction: str,
        scene_context: Optional[dict],
    ) -> dict:
        scene_summary = self._summarize_scene(scene_context)
        prompt = self._prompt_builder.intent_recognition_prompt(
            instruction=instruction,
            scene_summary=scene_summary,
        )
        try:
            llm = self._factory.get_backend()
            raw = await llm.agenerate(prompt, max_tokens=256, temperature=0.1)
            intent = self._parser.parse_intent(raw)
            if intent["confidence"] > 0.3:
                return intent
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"LLM intent parse failed, using rule-based: {exc}")

        # Fallback to rule-based parser
        rule_intent = self._intent_parser.parse(instruction)
        return {
            "action":      rule_intent.action,
            "target":      rule_intent.target,
            "source":      rule_intent.source,
            "constraints": rule_intent.constraints,
            "confidence":  rule_intent.confidence,
        }

    async def _decompose(
        self,
        intent: dict,
        scene_context: Optional[dict],
    ) -> list[dict]:
        import json
        scene_summary = self._summarize_scene(scene_context)
        prompt = self._prompt_builder.task_decomposition_prompt(
            intent_json=json.dumps(intent, ensure_ascii=False),
            scene_summary=scene_summary,
        )
        try:
            llm = self._factory.get_backend()
            raw = await llm.agenerate(prompt, max_tokens=512, temperature=0.1)
            subtasks = self._parser.parse_subtasks(raw)
            if subtasks:
                return subtasks
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"LLM decompose failed, using template: {exc}")

        # Fallback: use rule-based decomposer
        from brain_ai.domain.entities import Intent
        rule_intent = Intent(
            action=intent["action"],
            target=intent["target"],
            source=intent.get("source"),
            constraints=intent.get("constraints", []),
            confidence=intent.get("confidence", 0.5),
        )
        task = self._decomposer.decompose(rule_intent)
        return [
            {
                "skill_name": st.skill_name if hasattr(st, "skill_name") else str(st),
                "parameters": {},
                "preconditions": [],
                "postconditions": [],
                "estimated_duration_sec": 5.0,
            }
            for st in (task.subtasks if hasattr(task, "subtasks") else [])
        ]

    async def _generate_bt(
        self,
        subtasks: list[dict],
        scene_context: Optional[dict],
    ) -> str:
        import json
        scene_summary = self._summarize_scene(scene_context)
        prompt = self._prompt_builder.bt_generation_prompt(
            subtasks_json=json.dumps(subtasks, ensure_ascii=False),
            scene_summary=scene_summary,
        )
        try:
            llm = self._factory.get_backend()
            raw = await llm.agenerate(prompt, max_tokens=1024, temperature=0.05)
            bt_xml = self._parser.parse_bt_xml(raw)
            if "<BehaviorTree" in bt_xml:
                return bt_xml
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"LLM BT generation failed, using template: {exc}")

        # Fallback: template-based BT
        from brain_ai.domain.entities import Task, Intent
        dummy_intent = Intent(action="unknown", target="unknown")
        dummy_task = Task(id="t0", intent=dummy_intent)
        return self._bt_generator.generate(dummy_task)

    # ─── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _summarize_scene(scene_context: Optional[dict]) -> str:
        if not scene_context:
            return "Scene: unknown"
        objects = scene_context.get("objects", [])
        labels  = [o.get("label", "?") for o in objects[:5]]
        return f"Scene contains: {', '.join(labels) or 'no objects'}"

    @staticmethod
    def _make_plan_id(instruction: str) -> str:
        import hashlib, time
        h = hashlib.md5(f"{instruction}{time.time()}".encode()).hexdigest()[:8]
        return f"plan_{h}"
