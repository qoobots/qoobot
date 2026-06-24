"""
brain_ai/llm_agent/task_decomposer.py — Intent → Task tree decomposition.

Sprint 1: Stub implementation.
Sprint 2+: LLM-backed with task_decomposition.j2 template.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from brain_ai.domain.entities import Intent, Task, TaskStatus

logger = logging.getLogger(__name__)


class TaskDecomposer:
    """Decomposes an Intent into a hierarchical Task tree."""

    def __init__(self):
        logger.info("[TaskDecomposer] Initialized.")

    def decompose(self, intent: Intent, max_depth: int = 3) -> Task:
        """Decompose intent into task tree.

        Args:
            intent: the parsed intent
            max_depth: maximum nesting depth

        Returns:
            Root Task with subtasks
        """
        logger.info(f"[TaskDecomposer] Decomposing intent: {intent.action}")

        task_id = f"task-{uuid.uuid4().hex[:8]}"
        root = Task(
            id=task_id,
            intent=intent,
            status=TaskStatus.PLANNING,
            created_at=datetime.now(),
        )

        # Stub: predefined decomposition based on action type
        decompositions = {
            "pick": [
                ("navigate_to", intent.target),
                ("detect", intent.target),
                ("pick", intent.target),
            ],
            "place": [
                ("navigate_to", intent.target),
                ("place", intent.target),
            ],
            "navigate": [
                ("navigate_to", intent.target),
            ],
            "detect": [
                ("observe", intent.target),
                ("detect", intent.target),
            ],
        }

        steps = decompositions.get(intent.action, [("unknown", intent.target)])

        for i, (action, target) in enumerate(steps):
            sub_intent = Intent(action=action, target=target, confidence=intent.confidence)
            sub_task = Task(
                id=f"{task_id}-sub-{i+1}",
                intent=sub_intent,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
            )
            root.subtasks.append(sub_task)

        logger.info(f"[TaskDecomposer] Created task tree with {len(root.subtasks)} subtasks")
        return root
