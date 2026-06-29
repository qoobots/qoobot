"""
brain_ai/llm_agent/function_calling.py — Structured output / function-call parser.

Parses LLM JSON output into strongly-typed domain objects.
Handles common failure modes: malformed JSON, missing fields, extra fields.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ─── Schemas ────────────────────────────────────────────────────────

INTENT_SCHEMA = {
    "action":      str,
    "target":      str,
    "source":      (str, type(None)),
    "constraints": list,
    "confidence":  float,
}

SUBTASK_SCHEMA = {
    "skill_name":   str,
    "parameters":   dict,
    "preconditions":  list,
    "postconditions": list,
    "estimated_duration_sec": float,
}


# ─── Extractor ──────────────────────────────────────────────────────

class FunctionCallParser:
    """
    Parses structured JSON out of LLM responses.

    LLMs sometimes wrap JSON in markdown fences or add explanation text.
    This parser handles those cases robustly.
    """

    # ── JSON extraction ───────────────────────────────────────

    @staticmethod
    def extract_json(text: str) -> Optional[Any]:
        """
        Extract the first valid JSON object or array from *text*.
        Handles ```json ... ``` fences, plain JSON, or JSON embedded in prose.
        """
        # 1. Try direct parse first
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Extract from markdown fence
        fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text, re.IGNORECASE)
        if fence_match:
            try:
                return json.loads(fence_match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Find largest {...} or [...] substring
        for pat in (r"\{[\s\S]+\}", r"\[[\s\S]+\]"):
            match = re.search(pat, text)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass

        logger.warning("FunctionCallParser: Could not extract JSON from LLM response.")
        return None

    # ── Intent parsing ────────────────────────────────────────

    def parse_intent(self, llm_output: str) -> dict:
        """
        Parse LLM output into an intent dict.

        Expected JSON:
        {
          "action": "pick",
          "target": "red_cup",
          "source": null,
          "constraints": ["carefully"],
          "confidence": 0.95
        }
        """
        data = self.extract_json(llm_output)
        if not isinstance(data, dict):
            logger.error(f"Intent parse failed: {llm_output[:100]!r}")
            return self._default_intent()

        return {
            "action":      str(data.get("action",      "unknown")),
            "target":      str(data.get("target",      "unknown")),
            "source":      data.get("source",           None),
            "constraints": list(data.get("constraints", [])),
            "confidence":  float(data.get("confidence", 0.0)),
        }

    def parse_subtasks(self, llm_output: str) -> list[dict]:
        """
        Parse LLM output into a list of subtask dicts.

        Expected JSON:
        [
          {"skill_name": "detect_object", "parameters": {"label": "red_cup"}, ...},
          {"skill_name": "pick_object",   "parameters": {"object_id": "..."}, ...}
        ]
        """
        data = self.extract_json(llm_output)
        if isinstance(data, dict) and "subtasks" in data:
            data = data["subtasks"]
        if not isinstance(data, list):
            logger.error(f"Subtask parse failed: {llm_output[:100]!r}")
            return []

        result = []
        for item in data:
            if not isinstance(item, dict):
                continue
            result.append({
                "skill_name":   str(item.get("skill_name",   "")),
                "parameters":   dict(item.get("parameters",  {})),
                "preconditions":  list(item.get("preconditions",  [])),
                "postconditions": list(item.get("postconditions", [])),
                "estimated_duration_sec": float(item.get("estimated_duration_sec", 5.0)),
            })
        return result

    def parse_bt_xml(self, llm_output: str) -> str:
        """Extract behavior tree XML from LLM output."""
        # Check for XML fence
        xml_match = re.search(r"```(?:xml)?\s*([\s\S]+?)\s*```", llm_output, re.IGNORECASE)
        if xml_match:
            return xml_match.group(1).strip()

        # Look for <BehaviorTree ... >
        bt_match = re.search(r"(<BehaviorTree[\s\S]+</BehaviorTree>)", llm_output)
        if bt_match:
            return bt_match.group(1).strip()

        logger.warning("Could not extract BT XML from LLM output.")
        return "<BehaviorTree/>"

    # ── Helpers ───────────────────────────────────────────────

    @staticmethod
    def _default_intent() -> dict:
        return {
            "action":      "unknown",
            "target":      "unknown",
            "source":      None,
            "constraints": [],
            "confidence":  0.0,
        }
