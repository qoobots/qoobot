"""
brain_ai/llm_agent/bt_generator.py — Task → BehaviorTree XML/JSON.

Sprint 1: Template-based BT generation.
Sprint 4+: LLM-backed with bt_generation.j2 template.
"""

from __future__ import annotations

import logging

from brain_ai.domain.entities import Task

logger = logging.getLogger(__name__)


class BTGenerator:
    """Generates BehaviorTree XML from a decomposed Task."""

    def __init__(self):
        logger.info("[BTGenerator] Initialized.")

    def generate(self, task: Task, format: str = "xml") -> str:
        """Generate behavior tree from task tree.

        Args:
            task: the decomposed task with subtasks
            format: "xml" or "json"

        Returns:
            Behavior tree string in the requested format
        """
        logger.info(f"[BTGenerator] Generating BT for task: {task.id}")

        nodes_xml = ""
        for sub in task.subtasks:
            node_type = self._action_to_node(sub.intent.action)
            nodes_xml += f'      <{node_type} name="{sub.id}" target="{sub.intent.target}"/>\n'

        xml = f"""<root main_tree_to_execute="MainTree">
  <BehaviorTree ID="MainTree">
    <Sequence name="{task.id}">
{nodes_xml}    </Sequence>
  </BehaviorTree>
</root>"""

        logger.info(f"[BTGenerator] Generated {len(task.subtasks)}-node BT")
        return xml

    def _action_to_node(self, action: str) -> str:
        """Map action verb to BehaviorTree node type."""
        mapping = {
            "navigate_to": "NavigateTo",
            "detect": "DetectObject",
            "pick": "PickObject",
            "place": "PlaceObject",
            "observe": "Observe",
            "wait": "Wait",
            "speak": "Speak",
            "avoid_obstacle": "AvoidObstacle",
            "hitl_confirm": "HITLConfirm",
        }
        return mapping.get(action, "Wait")
