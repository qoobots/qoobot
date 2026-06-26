"""Completion engine — provides intelligent code completion for qoocode projects."""

import logging
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    CompletionParams,
    CompletionList,
    CompletionItem,
    CompletionItemKind,
    InsertTextFormat,
    Position,
    Range,
)

logger = logging.getLogger("qoocode-lsp.completion")

# SDK type stubs for qoobot-sdk
QOOBOT_SDK_TYPES: dict[str, dict] = {
    "QooSkill": {
        "kind": CompletionItemKind.Class,
        "detail": "Base class for all robot skills",
        "documentation": "QooSkill provides lifecycle hooks: setup(), loop(), teardown().\n\n"
                         "```python\nclass MySkill(QooSkill):\n    async def setup(self): ...\n    async def loop(self): ...\n    async def teardown(self): ...\n```",
    },
    "SkillConfig": {
        "kind": CompletionItemKind.Class,
        "detail": "Skill configuration dataclass",
        "documentation": "Configuration for a QooSkill.\n\nFields: name, version, priority, timeout_ms",
    },
    "Image": {
        "kind": CompletionItemKind.Class,
        "detail": "RGB/RGB-D camera image",
        "documentation": "Perception data: camera image.\n\nFields: data (np.ndarray), width, height, channels, timestamp",
    },
    "PointCloud": {
        "kind": CompletionItemKind.Class,
        "detail": "LiDAR point cloud",
        "documentation": "Perception data: 3D point cloud.\n\nFields: points (np.ndarray Nx3), intensities, timestamp",
    },
    "IMUData": {
        "kind": CompletionItemKind.Class,
        "detail": "IMU sensor data",
        "documentation": "Perception data: inertial measurement.\n\nFields: accel, gyro, mag, timestamp",
    },
    "JointStates": {
        "kind": CompletionItemKind.Class,
        "detail": "Robot joint states",
        "documentation": "Perception data: joint positions/velocities/efforts.\n\nFields: names, positions, velocities, efforts, timestamp",
    },
    "JointCommand": {
        "kind": CompletionItemKind.Class,
        "detail": "Joint control command",
        "documentation": "Control: set target joint positions/velocities/efforts.",
    },
    "EndEffectorTarget": {
        "kind": CompletionItemKind.Class,
        "detail": "End-effector pose target",
        "documentation": "Control: Cartesian end-effector target (position + orientation).",
    },
    "GripperCommand": {
        "kind": CompletionItemKind.Class,
        "detail": "Gripper control command",
        "documentation": "Control: open/close gripper with position/force.",
    },
    "BrainOSClient": {
        "kind": CompletionItemKind.Class,
        "detail": "BrainOS communication client",
        "documentation": "Communication: connect to BrainOS runtime.\n\nMethods: connect(), send_perception(), receive_control(), disconnect()",
    },
    "ROS2Bridge": {
        "kind": CompletionItemKind.Class,
        "detail": "ROS 2 bridge for DDS communication",
        "documentation": "Communication: ROS 2 topic pub/sub bridge.\n\nMethods: connect(), subscribe(), publish(), disconnect()",
    },
    "QooLogger": {
        "kind": CompletionItemKind.Class,
        "detail": "Structured logger for skills",
        "documentation": "Logging: structured logging with context.\n\nMethods: info(), debug(), warning(), error()",
    },
}

QOOBOT_SDK_METHODS = {
    "QooSkill": [
        ("setup", "Initialize skill resources", "async def setup(self) -> None"),
        ("loop", "Main skill loop — called repeatedly", "async def loop(self) -> None"),
        ("teardown", "Clean up resources", "async def teardown(self) -> None"),
        ("on_perception", "Handle incoming perception data", "async def on_perception(self, data) -> None"),
        ("send_control", "Send control command to runtime", "async def send_control(self, cmd) -> None"),
        ("get_state", "Get current skill state", "def get_state(self) -> SkillState"),
        ("run", "Run the skill event loop", "async def run(self) -> None"),
    ],
    "BrainOSClient": [
        ("connect", "Connect to BrainOS runtime", "async def connect(self) -> None"),
        ("disconnect", "Disconnect from runtime", "async def disconnect(self) -> None"),
        ("send_perception", "Send perception data", "async def send_perception(self, data) -> None"),
        ("receive_control", "Receive control command", "async def receive_control(self) -> ControlMessage"),
    ],
    "ROS2Bridge": [
        ("connect", "Connect to ROS 2 network", "async def connect(self) -> None"),
        ("disconnect", "Disconnect from ROS 2", "async def disconnect(self) -> None"),
        ("subscribe", "Subscribe to a topic", "def subscribe(self, topic: str, callback) -> None"),
        ("publish", "Publish to a topic", "async def publish(self, topic: str, msg) -> None"),
    ],
}


class QooCompletionEngine:
    """Provides qoobot-sdk aware completions."""

    def complete(self, ls: LanguageServer, params: CompletionParams) -> Optional[CompletionList]:
        doc = ls.workspace.get_text_document(params.text_document.uri)
        if doc is None:
            return None

        line = doc.lines[params.position.line] if params.position.line < len(doc.lines) else ""
        line_prefix = line[: params.position.character]
        line_suffix = line[params.position.character :]

        items: list[CompletionItem] = []

        # Import completions
        items.extend(self._get_import_completions(line_prefix))

        # Method completions on dot
        if "." in line_prefix:
            items.extend(self._get_method_completions(line_prefix))

        # Class name completions
        items.extend(self._get_type_completions(line_prefix, doc.lines))

        return CompletionList(is_incomplete=False, items=items)

    def _get_import_completions(self, line_prefix: str) -> list[CompletionItem]:
        """Completions for import statements."""
        items: list[CompletionItem] = []

        if "from qoobot_sdk" in line_prefix or "import qoobot_sdk" in line_prefix:
            # Submodule completions
            for mod in ["skill", "perception", "control", "communication", "logging"]:
                items.append(CompletionItem(
                    label=mod,
                    kind=CompletionItemKind.Module,
                    detail=f"qoobot_sdk.{mod}",
                ))

        # Top-level SDK completions after import
        if line_prefix.strip().startswith("from qoobot_sdk") and "import" in line_prefix:
            for name, info in QOOBOT_SDK_TYPES.items():
                items.append(CompletionItem(
                    label=name,
                    kind=info["kind"],
                    detail=info["detail"],
                    documentation=info["documentation"],
                ))

        return items

    def _get_method_completions(self, line_prefix: str) -> list[CompletionItem]:
        """Method completions after dot."""
        items: list[CompletionItem] = []

        # Detect object type from variable name or context
        for obj_type, methods in QOOBOT_SDK_METHODS.items():
            # Simple heuristic: if variable name contains type name
            obj_lower = obj_type.lower()
            var_name = line_prefix.rsplit(".", 1)[0].split()[-1].strip() if line_prefix.rsplit(".", 1)[0].split() else ""

            if obj_lower in var_name.lower() or obj_lower in line_prefix.lower():
                for name, doc, sig in methods:
                    items.append(CompletionItem(
                        label=name,
                        kind=CompletionItemKind.Method,
                        detail=sig,
                        documentation=doc,
                    ))

        return items

    def _get_type_completions(self, line_prefix: str, lines: list[str]) -> list[CompletionItem]:
        """Class/type name completions."""
        items: list[CompletionItem] = []

        # Check if we're in a context that suggests SDK usage
        full_text = "\n".join(lines)
        is_qoo_project = any(
            keyword in full_text
            for keyword in ["qoobot_sdk", "QooSkill", "from qoocode", "import qoocode"]
        )

        if is_qoo_project:
            for name, info in QOOBOT_SDK_TYPES.items():
                if name.lower().startswith(line_prefix.split()[-1].lower()):
                    items.append(CompletionItem(
                        label=name,
                        kind=info["kind"],
                        detail=info["detail"],
                        documentation=info["documentation"],
                    ))

        return items
