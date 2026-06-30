# QooBot SDK

Python SDK for QooBot Humanoid Robot Development.

## Installation

```bash
pip install qoobot-sdk
```

## Quick Start

```python
from qoobot_sdk import QooSkill, SkillContext

class HelloWorld(QooSkill):
    async def on_start(self, ctx: SkillContext):
        ctx.logger.info("Hello, QooBot!")

    async def on_tick(self, ctx: SkillContext):
        # Your skill logic here
        pass

skill = HelloWorld(name="hello-world")
await skill.run()
```

## Modules

| Module | Description |
|--------|-------------|
| `qoobot_sdk.skill` | Skill base class and lifecycle management |
| `qoobot_sdk.perception` | Sensor data types (Image, PointCloud, IMU, JointStates) |
| `qoobot_sdk.control` | Robot control interfaces (joint, end-effector, gripper) |
| `qoobot_sdk.communication` | BrainOS client and ROS 2 bridge |
| `qoobot_sdk.logging` | Structured logging utilities |

## License

Apache-2.0
