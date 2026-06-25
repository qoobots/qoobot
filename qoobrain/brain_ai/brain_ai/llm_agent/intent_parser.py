"""
brain_ai/llm_agent/intent_parser.py — Natural Language → Structured Intent

Uses LLM (Qwen2.5 via TensorRT-LLM or DeepSeek-V3 via API) to parse
natural language instructions into structured Intent objects.

Sprint 1: Stub implementation for connectivity testing.
Sprint 2: Full LLM-backed implementation with prompt engineering.
"""

from __future__ import annotations

import logging

from brain_ai.domain.entities import Intent

logger = logging.getLogger(__name__)


class IntentParser:
    """Parses natural language instructions into structured Intents."""

    def __init__(self, model_name: str = "qwen2.5-7b"):
        self._model_name = model_name
        logger.info(f"[IntentParser] Initialized with model: {model_name}")

    def parse(self, instruction: str, context: dict | None = None) -> Intent:
        """Parse a single natural language instruction.

        Args:
            instruction: e.g. "把红色方块放到蓝色盒子里"
            context: optional scene context for disambiguation

        Returns:
            Intent object with action, target, constraints, confidence
        """
        logger.info(f"[IntentParser] Parsing: {instruction}")
        # Stub: rule-based parsing for Sprint 1
        # Sprint 2+: call LLM with intent_recognition.j2 template

        instruction_lower = instruction.lower()

        # Simple keyword-based intent parsing
        if "抓" in instruction or "拿" in instruction or "pick" in instruction_lower:
            action = "pick"
        elif "放" in instruction or "放" in instruction or "place" in instruction_lower:
            action = "place"
        elif "走" in instruction or "去" in instruction or "导航" in instruction or "navigate" in instruction_lower:
            action = "navigate"
        elif "看" in instruction or "观察" in instruction or "detect" in instruction_lower:
            action = "detect"
        elif "停止" in instruction or "停" in instruction or "stop" in instruction_lower:
            action = "stop"
        else:
            action = "unknown"

        # Simple target extraction (stub)
        targets = {
            "红色方块": "red_cube", "蓝色方块": "blue_cube",
            "红色盒子": "red_box", "蓝色盒子": "blue_box",
            "杯子": "cup", "瓶子": "bottle",
        }
        target = "unknown"
        for cn, en in targets.items():
            if cn in instruction:
                target = en
                break

        constraints = []
        if "慢" in instruction or "小心" in instruction or "carefully" in instruction_lower:
            constraints.append("slow")
        if "快" in instruction or "迅速" in instruction or "fast" in instruction_lower:
            constraints.append("fast")

        return Intent(
            action=action,
            target=target,
            constraints=constraints,
            confidence=0.85 if target != "unknown" else 0.3,
        )
