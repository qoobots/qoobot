"""
Skill project template.

Creates a Python-based QooBot skill project with:
- Standard project structure
- qoo.toml configuration
- Example skill code using qoobot-sdk
- Unit test skeleton
"""

from __future__ import annotations

from pathlib import Path
from typing import List


class SkillTemplate:
    """Generates a QooBot skill project."""

    QOO_TOML = '''\
[project]
name = "{name}"
type = "skill"
version = "0.1.0"
description = "A QooBot skill"
python_version = "{python_version}"

[skill]
entry_point = "src.skill:main"
permissions = []
sensors = []
actuators = []

[dependencies]
python = [
    "qoobot-sdk>=0.1.0",
]
'''

    MAIN_SKILL = '''\
"""
{name} - QooBot Skill

A QooBot skill that runs on the Brain OS platform.
"""

from qoobot_sdk import QooSkill, SkillContext


class {class_name}(QooSkill):
    """Main skill class for {name}."""

    def __init__(self):
        super().__init__(
            name="{name}",
            version="0.1.0",
        )

    async def on_start(self, ctx: SkillContext) -> None:
        """Called when the skill starts."""
        ctx.logger.info(f"Skill {{self.name}} v{{self.version}} started")

    async def on_stop(self, ctx: SkillContext) -> None:
        """Called when the skill stops."""
        ctx.logger.info(f"Skill {{self.name}} stopped")

    async def on_tick(self, ctx: SkillContext) -> None:
        """Called on each control cycle."""
        # Main skill logic goes here
        pass


async def main():
    """Entry point for the skill."""
    skill = {class_name}()
    await skill.run()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''

    TEST_SKILL = '''\
"""Tests for {name} skill."""

import pytest
from src.skill import {class_name}


def test_skill_creation():
    """Test that the skill can be created."""
    skill = {class_name}()
    assert skill.name == "{name}"
    assert skill.version == "0.1.0"
'''

    INIT_PY = '"""Auto-generated QooBot skill project."""\n'
    SRC_INIT = '"""Skill source package."""\n'
    TESTS_INIT = '"""Test package."""\n'

    def generate(
        self, name: str, target_path: Path, python_version: str
    ) -> List[Path]:
        """Generate a skill project.

        Args:
            name: Project/skill name
            target_path: Where to create the project
            python_version: Minimum Python version

        Returns:
            List of created file paths.
        """
        class_name = self._to_class_name(name)
        created = []

        # Create directory structure
        dirs = [
            target_path,
            target_path / "src",
            target_path / "tests",
            target_path / "config",
            target_path / "data",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)

        # qoo.toml
        f = target_path / "qoo.toml"
        f.write_text(self.QOO_TOML.format(name=name, python_version=python_version))
        created.append(f)

        # __init__.py (root)
        f = target_path / "__init__.py"
        f.write_text(self.INIT_PY)
        created.append(f)

        # src/__init__.py
        f = target_path / "src" / "__init__.py"
        f.write_text(self.SRC_INIT)
        created.append(f)

        # src/skill.py
        f = target_path / "src" / "skill.py"
        f.write_text(self.MAIN_SKILL.format(name=name, class_name=class_name))
        created.append(f)

        # tests/__init__.py
        f = target_path / "tests" / "__init__.py"
        f.write_text(self.TESTS_INIT)
        created.append(f)

        # tests/test_skill.py
        f = target_path / "tests" / "test_skill.py"
        f.write_text(self.TEST_SKILL.format(name=name, class_name=class_name))
        created.append(f)

        # config/default.yaml
        f = target_path / "config" / "default.yaml"
        f.write_text(f"# Configuration for {name}\nskill:\n  name: {name}\n")
        created.append(f)

        # .gitignore
        f = target_path / ".gitignore"
        f.write_text(
            "__pycache__/\n*.pyc\n*.pyo\nbuild/\ndist/\n*.egg-info/\n"
            ".pytest_cache/\n.qoo/\n*.qooskills\n"
        )
        created.append(f)

        # README.md
        f = target_path / "README.md"
        f.write_text(
            f"# {name}\n\n"
            f"A QooBot skill project.\n\n"
            f"## Quick Start\n\n"
            f"```bash\n"
            f"qoo build\n"
            f"qoo run\n"
            f"qoo test\n"
            f"```\n"
        )
        created.append(f)

        return created

    @staticmethod
    def _to_class_name(name: str) -> str:
        """Convert kebab-case name to PascalCase class name."""
        return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))
