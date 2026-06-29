"""
qoodev Documentation Site Generator.

Generates a complete documentation site using MkDocs with Material theme,
including API reference, tutorials, and guides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, List
import json


class DocSiteGenerator:
    """Generates MkDocs-based documentation site for qoodev.

    Produces:
    - mkdocs.yml configuration
    - API reference (auto-generated from docstrings)
    - Tutorial series (beginner to advanced)
    - Architecture and design docs
    - CLI command reference
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.docs_dir = self.project_root / "docs_site"
        self.api_dir = self.docs_dir / "api"
        self.tutorials_dir = self.docs_dir / "tutorials"
        self.guides_dir = self.docs_dir / "guides"

    def generate(self) -> Path:
        """Generate the full documentation site structure."""
        self._create_directories()
        self._generate_mkdocs_config()
        self._generate_index()
        self._generate_api_reference()
        self._generate_tutorials()
        self._generate_guides()
        self._generate_cli_reference()
        return self.docs_dir

    def _create_directories(self) -> None:
        for d in [self.docs_dir, self.api_dir, self.tutorials_dir, self.guides_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def _generate_mkdocs_config(self) -> None:
        config = {
            "site_name": "qoodev",
            "site_description": "Developer Toolchain for QooBot Humanoid Robot",
            "site_author": "QooBot Team",
            "theme": {
                "name": "material",
                "features": [
                    "navigation.tabs",
                    "navigation.sections",
                    "navigation.expand",
                    "search.suggest",
                    "search.highlight",
                    "content.code.copy",
                    "content.code.annotate",
                ],
                "palette": [
                    {"media": "(prefers-color-scheme: light)", "scheme": "default", "primary": "indigo", "accent": "indigo"},
                    {"media": "(prefers-color-scheme: dark)", "scheme": "slate", "primary": "indigo", "accent": "indigo"},
                ],
            },
            "markdown_extensions": [
                "pymdownx.highlight",
                "pymdownx.superfences",
                "pymdownx.inlinehilite",
                "pymdownx.tabbed",
                "pymdownx.details",
                "admonition",
                "toc",
            ],
            "plugins": ["search", "mkdocstrings"],
            "nav": [
                {"Home": "index.md"},
                {"Getting Started": [
                    {"Quick Start": "tutorials/quickstart.md"},
                    {"Installation": "tutorials/installation.md"},
                    {"Your First Skill": "tutorials/first-skill.md"},
                ]},
                {"Tutorials": [
                    {"Navigation Skill": "tutorials/navigation.md"},
                    {"Grasping Skill": "tutorials/grasping.md"},
                    {"Voice Control": "tutorials/voice-control.md"},
                    {"Obstacle Avoidance": "tutorials/obstacle-avoidance.md"},
                    {"Home Service": "tutorials/home-service.md"},
                ]},
                {"Guides": [
                    {"Project Structure": "guides/project-structure.md"},
                    {"CLI Reference": "guides/cli-reference.md"},
                    {"Simulation": "guides/simulation.md"},
                    {"Debugging": "guides/debugging.md"},
                    {"Packaging & CI/CD": "guides/packaging.md"},
                ]},
                {"API Reference": [
                    {"qoobot-sdk": "api/sdk.md"},
                    {"CLI": "api/cli.md"},
                    {"Examples": "api/examples.md"},
                ]},
            ],
        }

        config_path = self.docs_dir / "mkdocs.yml"
        config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _generate_index(self) -> None:
        index = """# qoodev

**Developer Toolchain for QooBot Humanoid Robot**

qoodev is the complete developer tools platform for building skills on the QooBot humanoid robot.
From project scaffolding to production deployment, qoodev provides everything you need.

## Key Features

| Feature | Description |
|---------|-------------|
| CLI Tools | `qoo init`, `qoo build`, `qoo run`, `qoo test`, `qoo sim` |
| VS Code Plugin | Syntax highlighting, IntelliSense, behavior tree editor |
| Simulation | Isaac Sim / MuJoCo integration, sensor simulation |
| Debugging | Real-time logs, sensor visualization, remote breakpoints |
| Packaging | `.qooskills` format with dependency management and signing |
| CI/CD | GitHub Actions templates for automated testing and release |

## Quick Links

- [Quick Start Guide](tutorials/quickstart.md)
- [Installation](tutorials/installation.md)
- [CLI Reference](guides/cli-reference.md)
- [API Reference](api/sdk.md)

## Architecture

```
qoo init  →  qoo build  →  qoo sim  →  qoo run  →  qoo test  →  qoo package  →  qoostore
   |            |            |           |            |              |
  项目创建     代码构建     仿真环境    运行调试     单元测试      技能打包      市场发布
```

## Version

Current: **v1.0.0 GA**
"""
        (self.docs_dir / "index.md").write_text(index, encoding="utf-8")

    def _generate_api_reference(self) -> None:
        sdk_api = """# qoobot-sdk API Reference

## QooSkill Base Class

All skills inherit from `QooSkill`.

```python
from qoobot_sdk import QooSkill

class MySkill(QooSkill):
    def on_configure(self, config: dict) -> None: ...
    def on_start(self) -> None: ...
    def on_step(self, observations: dict) -> dict: ...
    def on_stop(self) -> None: ...
    def on_reset(self) -> None: ...
```

### Lifecycle Methods

| Method | Description |
|--------|-------------|
| `on_configure(config)` | Called once when the skill is configured |
| `on_start()` | Called when the skill starts executing |
| `on_step(obs)` | Called every control cycle; returns action dict |
| `on_stop()` | Called when the skill is stopped |
| `on_reset()` | Called to reset skill state |

## Perception API

```python
from qoobot_sdk.perception import (
    Camera, DepthCamera, Lidar, IMU, Microphone,
    get_camera, get_lidar, get_imu,
)
```

## Control API

```python
from qoobot_sdk.control import (
    JointController, Gripper, MobileBase,
    set_joint_position, set_joint_velocity, set_joint_torque,
)
```

## Communication API

```python
from qoobot_sdk.communication import (
    Publisher, Subscriber, ServiceClient,
    create_publisher, create_subscriber, call_service,
)
```
"""
        (self.api_dir / "sdk.md").write_text(sdk_api, encoding="utf-8")

        cli_api = """# CLI Reference

## Command Overview

| Command | Description |
|---------|-------------|
| `qoo init <name>` | Create a new project |
| `qoo build` | Build the project |
| `qoo run` | Run in simulation |
| `qoo test` | Run tests |
| `qoo doctor` | Environment diagnostics |
| `qoo sim` | Simulation management |
| `qoo package` | Skill packaging |
| `qoo record` | Data recording/replay |
| `qoo debug` | Remote debugging |
| `qoo ci` | CI/CD integration |

## Global Options

| Option | Description |
|--------|-------------|
| `--version, -V` | Show version |
| `--help` | Show help |

## qoo init

```bash
qoo init my-skill              # Create skill project
qoo init my-service --type service  # Create service project
qoo init my-model --type model      # Create model project
```

## qoo sim

```bash
qoo sim start --backend mujoco --scene home
qoo sim start --backend isaac_sim --scene factory
qoo sim start --headless           # Headless mode
qoo sim stop / pause / resume / step / monitor
```

## qoo package

```bash
qoo package build                  # Build .qooskills package
qoo package inspect <file>         # Inspect package contents
qoo package validate <file>        # Validate package
qoo package sign <file> --key <key>  # Sign package
qoo package verify <file>          # Verify signature
```

## qoo record

```bash
qoo record start --type teleop     # Record teleoperation
qoo record start --type demo       # Record skill demonstration
qoo record replay <file>           # Replay recording
qoo record export <file> --format jsonl  # Export data
```

## qoo debug

```bash
qoo debug attach --host <host> --port <port>
qoo debug server --port 9876
qoo debug breakpoint --file <file> --line <line>
qoo debug backtrace
```
"""
        (self.api_dir / "cli.md").write_text(cli_api, encoding="utf-8")

        examples_api = """# Example Skills API

## NavigationSkill

Autonomous navigation with A* path planning and obstacle avoidance.

```python
from qoodev.examples import NavigationSkill

nav = NavigationSkill(NavigationConfig(max_linear_speed=0.5))
nav.set_goal(3.0, 2.0, 0.0)
cmd = nav.step(lidar_scan, current_pose)
```

## GraspingSkill

Vision-based object grasping with force feedback.

```python
from qoodev.examples import GraspingSkill

grasp = GraspingSkill(GraspConfig())
grasp.detect_objects(rgb, depth)
result = grasp.grasp("mug")
```

## VoiceControlSkill

Speech recognition and intent parsing.

```python
from qoodev.examples import VoiceControlSkill

voice = VoiceControlSkill(VoiceConfig())
voice.register_handler(IntentType.MOVE, move_handler)
intent = voice.process_text("go to the kitchen")
```

## ObstacleAvoidanceSkill

DWA-based reactive obstacle avoidance.

```python
from qoodev.examples import ObstacleAvoidanceSkill

oa = ObstacleAvoidanceSkill(AvoidanceConfig())
cmd = oa.compute_command(lidar_scan, pose, target_vel)
```

## HomeServiceSkill

Composite skill combining navigation, grasping, and voice control.

```python
from qoodev.examples import HomeServiceSkill

service = HomeServiceSkill(ServiceConfig())
task = ServiceTask(task_id="1", command="bring mug", target_object="mug")
result = service.execute_task(task)
```
"""
        (self.api_dir / "examples.md").write_text(examples_api, encoding="utf-8")

    def _generate_tutorials(self) -> None:
        tutorials = {
            "quickstart.md": """# Quick Start

## Prerequisites

- Python 3.11+
- pip
- (Optional) MuJoCo for simulation

## Install

```bash
pip install qoodev
```

## Create Your First Project

```bash
qoo init hello-world
cd hello-world
```

## Build and Run

```bash
qoo build
qoo run
```

## Next Steps

- [Your First Skill](first-skill.md)
- [Navigation Tutorial](navigation.md)
""",
            "installation.md": """# Installation

## pip Install

```bash
pip install qoodev
```

## Development Install

```bash
git clone https://github.com/qoobot/qoodev.git
cd qoodev
pip install -e ".[dev]"
```

## VS Code Extension

Install from VS Code Marketplace: search "qoodev"

## Verify Installation

```bash
qoo doctor
qoo version
```
""",
            "first-skill.md": """# Your First Skill

Create a basic QooBot skill that moves the robot forward.

```python
# src/my_skill.py
from qoobot_sdk import QooSkill

class MoveForwardSkill(QooSkill):
    def on_step(self, observations):
        return {"linear_x": 0.3, "angular_z": 0.0}
```

Build and run:

```bash
qoo build
qoo sim start --backend mujoco --headless
qoo run
```
""",
        }

        for name, content in tutorials.items():
            (self.tutorials_dir / name).write_text(content, encoding="utf-8")

    def _generate_guides(self) -> None:
        guides = {
            "project-structure.md": """# Project Structure

```
my-skill/
├── qoo.toml          # Project configuration
├── src/              # Source code
│   └── skill.py      # Main skill file
├── tests/            # Unit tests
│   └── test_skill.py
├── models/           # ML models (optional)
├── resources/        # Assets, configs
└── build/            # Build output (gitignored)
```
""",
            "cli-reference.md": """# CLI Reference

See [API Reference > CLI](../api/cli.md) for full command documentation.
""",
            "simulation.md": """# Simulation Guide

## Starting Simulation

```bash
# MuJoCo (default, lightweight)
qoo sim start --backend mujoco --scene home

# Isaac Sim (high-fidelity, requires NVIDIA GPU)
qoo sim start --backend isaac_sim --scene factory

# Headless mode (for CI/CD)
qoo sim start --headless
```

## Available Scenes

- `home` — Living room + kitchen
- `factory` — Industrial workspace
- `empty` — Empty ground plane

## Monitoring

```bash
qoo sim monitor              # Real-time status
qoo sim step 100             # Step 100 frames
```
""",
            "debugging.md": """# Debugging Guide

## Remote Debugging

```bash
# Start debug server on robot
qoo debug server --port 9876

# Attach from development machine
qoo debug attach --host 192.168.1.100 --port 9876

# Set breakpoints
qoo debug breakpoint --file src/skill.py --line 42 --condition "x > 0.5"
```

## Data Recording

```bash
# Record teleoperation
qoo record start --type teleop --output demo.qoodata

# Replay
qoo record replay demo.qoodata --speed 1.0

# Export for analysis
qoo record export demo.qoodata --format jsonl
```
""",
            "packaging.md": """# Packaging & CI/CD

## Building a Package

```bash
qoo package build
qoo package inspect dist/my-skill-1.0.0.qooskills
```

## Code Signing

```bash
qoo package sign dist/my-skill-1.0.0.qooskills --key private.pem
qoo package verify dist/my-skill-1.0.0.qooskills
```

## CI/CD Setup

```bash
qoo ci init
# Generates .github/workflows/ci.yml and cd.yml
```
""",
        }

        for name, content in guides.items():
            (self.guides_dir / name).write_text(content, encoding="utf-8")

    def _generate_cli_reference(self) -> None:
        """CLI reference is included in API docs and guides."""
        pass
