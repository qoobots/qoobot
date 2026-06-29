"""
brain_ai/llm_agent/prompt_builder.py — Jinja2-based prompt builder for LLM calls.

Renders .j2 templates from brain_ai/llm_agent/prompts/ with runtime context.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


class PromptBuilder:
    """
    Loads Jinja2 prompt templates and renders them with context variables.

    Templates:
      - intent_recognition.j2   — NL instruction → structured intent
      - task_decomposition.j2   — intent → subtask list
      - bt_generation.j2        — subtasks → behavior tree XML
      - scene_understanding.j2  — scene description for context injection
      - common_sense.j2         — common-sense reasoning for edge cases
    """

    def __init__(self, templates_dir: Optional[str] = None) -> None:
        self._dir = templates_dir or _PROMPTS_DIR
        self._env = None
        self._raw: dict[str, str] = {}
        self._try_init_jinja()

    def _try_init_jinja(self) -> None:
        try:
            from jinja2 import Environment, FileSystemLoader, StrictUndefined  # type: ignore

            self._env = Environment(
                loader=FileSystemLoader(self._dir),
                undefined=StrictUndefined,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            logger.debug(f"Jinja2 prompt environment loaded from: {self._dir}")
        except ImportError:
            logger.warning("jinja2 not installed — using raw string templates.")

    def render(self, template_name: str, **context: Any) -> str:
        """
        Render a template file.

        Args:
            template_name: filename in prompts/ (e.g. "intent_recognition.j2")
            **context:      template variables

        Returns:
            Rendered prompt string
        """
        if self._env is not None:
            tpl = self._env.get_template(template_name)
            return tpl.render(**context)

        # Fallback: read raw file and do basic string substitution
        raw = self._load_raw(template_name)
        for key, value in context.items():
            raw = raw.replace(f"{{{{ {key} }}}}", str(value))
        return raw

    def _load_raw(self, name: str) -> str:
        if name not in self._raw:
            path = os.path.join(self._dir, name)
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as f:
                    self._raw[name] = f.read()
            else:
                logger.warning(f"Template not found: {path}")
                self._raw[name] = ""
        return self._raw[name]

    # ─── Convenience builders ──────────────────────────────────

    def intent_recognition_prompt(
        self,
        instruction: str,
        scene_summary: str = "",
        history: Optional[list[dict]] = None,
    ) -> str:
        return self.render(
            "intent_recognition.j2",
            instruction=instruction,
            scene_summary=scene_summary,
            history=history or [],
        )

    def task_decomposition_prompt(
        self,
        intent_json: str,
        scene_summary: str = "",
        available_skills: Optional[list[str]] = None,
    ) -> str:
        return self.render(
            "task_decomposition.j2",
            intent_json=intent_json,
            scene_summary=scene_summary,
            available_skills=available_skills or [],
        )

    def bt_generation_prompt(
        self,
        subtasks_json: str,
        scene_summary: str = "",
    ) -> str:
        return self.render(
            "bt_generation.j2",
            subtasks_json=subtasks_json,
            scene_summary=scene_summary,
        )

    def scene_understanding_prompt(self, scene_dict: dict) -> str:
        return self.render(
            "scene_understanding.j2",
            scene_json=json.dumps(scene_dict, ensure_ascii=False, indent=2),
        )
