"""
Project templates for qoo init.

Each template module provides a generate() function that returns
a list of created file paths.
"""

from __future__ import annotations

from typing import Protocol, List
from pathlib import Path


class TemplateGenerator(Protocol):
    """Protocol for template generators."""

    def generate(
        self, name: str, target_path: Path, python_version: str
    ) -> List[Path]: ...


def get_template(name: str) -> TemplateGenerator:
    """Get a template generator by name.

    Args:
        name: Template name (skill, service, model)

    Returns:
        Template generator instance.
    """
    if name == "skill":
        from cli.cli.templates.skill import SkillTemplate
        return SkillTemplate()
    elif name == "service":
        from cli.cli.templates.service import ServiceTemplate
        return ServiceTemplate()
    elif name == "model":
        from cli.cli.templates.model import ModelTemplate
        return ModelTemplate()
    else:
        raise ValueError(f"Unknown template: {name}")
