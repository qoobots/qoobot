"""
brain_ai/planner/bt_composer.py — Behavior Tree composer and validator.

Converts LLM-generated BT XML into a BehaviorTree domain model,
validates structure, and maps skill names against the registered skill registry.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Optional

from brain_ai.domain.plan import BehaviorTree, SkillNode

logger = logging.getLogger(__name__)

# Valid BT node types for BehaviorTree.CPP 4.x
VALID_NODE_TYPES = frozenset({
    "Sequence", "Fallback", "Parallel",
    "Action", "Condition", "Decorator",
    "ReactiveSequence", "ReactiveFallback",
    "SequenceStar", "FallbackStar",
    "IfThenElse", "WhileDoElse",
    "Inverter", "Repeat", "RetryUntilSuccessful",
    "KeepRunningUntilFailure", "Timeout",
    "ForceSuccess", "ForceFailure",
    "SubTree", "SetBlackboard", "Script",
})

# Banned skill names (safety)
BANNED_SKILLS = frozenset({"eval", "exec", "import", "__", "system"})


class BTComposer:
    """
    Compose and validate behavior trees from LLM-generated XML.

    Usage:
        composer = BTComposer(skill_registry={"pick_object", "place_object", "navigate_to"})
        bt = composer.compose(xml_str)
        if bt.root is not None:
            plan.behavior_tree = bt
    """

    def __init__(self, skill_registry: Optional[set[str]] = None) -> None:
        self._skill_registry: set[str] = set(skill_registry or [])
        logger.info(
            f"[BTComposer] Initialized with {len(self._skill_registry)} "
            f"known skills"
        )

    # ── Public API ─────────────────────────────────────────────────────────

    def compose(self, xml_str: str, task_id: str = "") -> BehaviorTree:
        """
        Parse LLM-generated BT XML into a BehaviorTree domain model.

        Args:
            xml_str: XML from LLM (may contain markdown fences or extra text)
            task_id: Parent task ID

        Returns:
            BehaviorTree with parsed root node, or empty root if invalid.
        """
        bt = BehaviorTree(task_id=task_id, xml_str=xml_str)
        clean = self._extract_xml(xml_str)
        if not clean:
            logger.warning("[BTComposer] No valid BT XML found in LLM output")
            return bt

        try:
            root_elem = ET.fromstring(clean)
            # Skip <BehaviorTree> wrapper if present
            if root_elem.tag == "BehaviorTree" and len(root_elem) == 1:
                root_elem = root_elem[0]
            bt.root = self._parse_node(root_elem)
            bt.xml_str = clean
            logger.info(
                f"[BTComposer] Composed BT for task {task_id}: "
                f"root={bt.root.node_type if bt.root else 'None'}, "
                f"skills={self._count_skills(bt.root)}"
            )
        except ET.ParseError as e:
            logger.error(f"[BTComposer] XML parse error: {e}")
        except Exception as e:
            logger.exception(f"[BTComposer] Unexpected error: {e}")

        return bt

    def register_skill(self, skill_name: str) -> None:
        """Register a known skill name."""
        if skill_name.lower() in BANNED_SKILLS:
            raise ValueError(f"Skill name {skill_name!r} is banned")
        self._skill_registry.add(skill_name)
        logger.debug(f"[BTComposer] Registered skill: {skill_name}")

    def unregister_skill(self, skill_name: str) -> None:
        self._skill_registry.discard(skill_name)

    # ── Validation ─────────────────────────────────────────────────────────

    def validate(self, bt: BehaviorTree) -> tuple[bool, list[str]]:
        """Validate a BehaviorTree and return (is_valid, warnings)."""
        warnings: list[str] = []

        if bt.root is None:
            return False, ["Empty behavior tree"]
        if not bt.root.node_type:
            return False, ["Root node has no type"]

        self._validate_node(bt.root, warnings)
        return len(warnings) == 0, warnings

    def _validate_node(self, node: SkillNode, warnings: list[str], depth: int = 0) -> None:
        if depth > 20:
            warnings.append(f"BT depth exceeds 20 at node {node.node_id}")
            return

        if node.node_type not in VALID_NODE_TYPES and not node.node_type.startswith("_"):
            warnings.append(
                f"Unknown node type '{node.node_type}' at {node.node_id}"
            )

        if node.node_type in ("Action",) and node.skill_name:
            if node.skill_name.lower() in BANNED_SKILLS:
                warnings.append(f"Banned skill '{node.skill_name}' at {node.node_id}")
            elif self._skill_registry and node.skill_name not in self._skill_registry:
                warnings.append(
                    f"Unregistered skill '{node.skill_name}' at {node.node_id}"
                )

        for child in node.children:
            self._validate_node(child, warnings, depth + 1)

    # ── Internal XML parsing ───────────────────────────────────────────────

    @staticmethod
    def _extract_xml(text: str) -> Optional[str]:
        """Extract raw XML from LLM output (may be wrapped in markdown)."""
        # Try markdown code fence: ```xml ... ```
        m = re.search(r'```(?:xml)?\s*\n?(.*?)```', text, re.DOTALL)
        if m:
            return m.group(1).strip()

        # Try raw XML
        if text.strip().startswith('<'):
            return text.strip()

        return None

    def _parse_node(self, elem: ET.Element) -> SkillNode:
        """Recursively parse an XML element into a SkillNode."""
        tag = elem.tag
        name = elem.attrib.get("name", "")
        params = {k: v for k, v in elem.attrib.items() if k != "name"}

        # Map common BT.CPP tags to our node types
        node_type = self._map_tag(tag)

        children = [self._parse_node(child) for child in elem]

        # If inner text and no children, treat as text content
        text = (elem.text or "").strip()
        if text and not children:
            params["_text"] = text

        return SkillNode(
            node_type=node_type,
            skill_name=name,
            parameters=params,
            children=children,
        )

    @staticmethod
    def _map_tag(tag: str) -> str:
        """Map BT XML tag to internal node_type."""
        # BehaviorTree.CPP uses CamelCase tags
        tag_lower = tag.lower()
        mapping = {
            "sequence": "Sequence",
            "fallback": "Fallback",
            "parallel": "Parallel",
            "reactive_sequence": "ReactiveSequence",
            "reactive_fallback": "ReactiveFallback",
            "action": "Action",
            "condition": "Condition",
            "decorator": "Decorator",
            "subtree": "SubTree",
            "inverter": "Inverter",
            "repeat": "Repeat",
            "retryuntilsuccessful": "RetryUntilSuccessful",
            "timeout": "Timeout",
            "forcesuccess": "ForceSuccess",
            "forcefailure": "ForceFailure",
            "setblackboard": "SetBlackboard",
            "script": "Script",
        }
        return mapping.get(tag_lower, tag)

    @staticmethod
    def _count_skills(node: Optional[SkillNode]) -> int:
        """Count total skill nodes in the tree."""
        if node is None:
            return 0
        count = 1 if node.skill_name else 0
        for child in node.children:
            count += BTComposer._count_skills(child)
        return count


# ── Default instance ───────────────────────────────────────────────────────

_default_composer: Optional[BTComposer] = None


def get_bt_composer() -> BTComposer:
    global _default_composer
    if _default_composer is None:
        _default_composer = BTComposer()
    return _default_composer
