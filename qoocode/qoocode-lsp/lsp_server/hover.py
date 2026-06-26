"""Hover engine — provides documentation on hover for qoobot-sdk APIs."""

import logging
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    Hover,
    HoverParams,
    MarkupContent,
    MarkupKind,
    Position,
)

logger = logging.getLogger("qoocode-lsp.hover")

HOVER_DOCS: dict[str, str] = {
    "QooSkill": """### QooSkill
**Base class for all robot skills.**

QooSkill provides a standard lifecycle for robot skills:

| Method | Description |
|--------|-------------|
| `setup()` | Called once when skill is loaded |
| `loop()` | Main loop — called repeatedly |
| `teardown()` | Called when skill is unloaded |

**Example:**
```python
class PickAndPlace(QooSkill):
    async def setup(self):
        self.arm = await self.get_actuator("arm")
    
    async def loop(self):
        target = await self.perceive()
        await self.arm.move_to(target)
        await self.gripper.close()
```
""",
    "SkillConfig": """### SkillConfig
Configuration for a QooSkill.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Skill identifier |
| `version` | `str` | Semantic version |
| `priority` | `int` | Execution priority (0-255) |
| `timeout_ms` | `int` | Loop timeout in milliseconds |
""",
    "Image": """### Image
Camera image perception data.

| Field | Type | Description |
|-------|------|-------------|
| `data` | `np.ndarray` | Image pixel data (HxWxC) |
| `width` | `int` | Image width in pixels |
| `height` | `int` | Image height in pixels |
| `channels` | `int` | Color channels (1, 3, or 4) |
| `encoding` | `str` | Encoding (rgb8, bgr8, mono8) |
| `timestamp` | `float` | Capture timestamp (seconds) |
""",
    "PointCloud": """### PointCloud
LiDAR point cloud data.

| Field | Type | Description |
|-------|------|-------------|
| `points` | `np.ndarray` | Nx3 array of (x, y, z) |
| `intensities` | `np.ndarray` | N array of intensity values |
| `timestamp` | `float` | Capture timestamp |
""",
    "JointStates": """### JointStates
Robot joint state feedback.

| Field | Type | Description |
|-------|------|-------------|
| `names` | `list[str]` | Joint names |
| `positions` | `np.ndarray` | Joint positions (rad) |
| `velocities` | `np.ndarray` | Joint velocities (rad/s) |
| `efforts` | `np.ndarray` | Joint efforts (Nm) |
| `timestamp` | `float` | State timestamp |
""",
    "JointCommand": """### JointCommand
Joint-level control command.

| Field | Type | Description |
|-------|------|-------------|
| `joint_names` | `list[str]` | Target joint names |
| `positions` | `list[float]` | Target positions (rad) |
| `velocities` | `list[float]` | Target velocities (rad/s) |
| `efforts` | `list[float]` | Target efforts (Nm) |
""",
    "EndEffectorTarget": """### EndEffectorTarget
Cartesian end-effector target.

| Field | Type | Description |
|-------|------|-------------|
| `position` | `tuple[float,float,float]` | Target (x, y, z) in meters |
| `orientation` | `tuple[float,float,float,float]` | Target quaternion (x, y, z, w) |
""",
    "BrainOSClient": """### BrainOSClient
Client for communicating with the BrainOS runtime.

```python
client = BrainOSClient(host="localhost", port=9090)
await client.connect()
await client.send_perception(image_data)
cmd = await client.receive_control()
```
""",
    "ROS2Bridge": """### ROS2Bridge
Bridge for ROS 2 DDS communication.

```python
bridge = ROS2Bridge(node_name="my_skill")
await bridge.connect()
bridge.subscribe("/camera/rgb", on_image)
await bridge.publish("/joint_cmd", cmd)
```
""",
}


class QooHoverEngine:
    """Provides hover documentation for qoobot-sdk symbols."""

    def hover(self, ls: LanguageServer, params: HoverParams) -> Optional[Hover]:
        doc = ls.workspace.get_text_document(params.text_document.uri)
        if doc is None:
            return None

        # Get the word at the hover position
        line = doc.lines[params.position.line] if params.position.line < len(doc.lines) else ""
        word = self._get_word_at_position(line, params.position.character)

        if word and word in HOVER_DOCS:
            return Hover(
                contents=MarkupContent(
                    kind=MarkupKind.Markdown,
                    value=HOVER_DOCS[word],
                )
            )

        return None

    def _get_word_at_position(self, line: str, col: int) -> Optional[str]:
        """Extract the word at the given column position."""
        if col >= len(line):
            return None

        # Find word boundaries
        start = col
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        end = col
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        if start < end:
            return line[start:end]

        return None
