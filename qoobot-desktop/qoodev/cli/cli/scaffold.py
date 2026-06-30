"""
Project scaffolding engine.

Generates project directories from built-in templates:
- skill: A QooBot skill project (Python)
- service: A QooBot system service project (C++/Python)
- model: A QooBot AI model project (Python)
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from jinja2 import Environment, BaseLoader

from cli.cli.templates import get_template

# Minimal Jinja2 environment for template rendering
_jinja_env = Environment(loader=BaseLoader())


class ProjectScaffold:
    """Creates new QooBot projects from templates."""

    def __init__(
        self,
        name: str,
        template: str,
        target_path: Path,
        python_version: str = "3.11",
    ):
        self.name = name
        self.template = template
        self.target_path = target_path
        self.python_version = python_version
        self._created: List[Path] = []

    def create(self) -> List[Path]:
        """Create the project from the selected template.

        Returns:
            List of created file paths.
        """
        template_module = get_template(self.template)
        files = template_module.generate(
            name=self.name,
            target_path=self.target_path,
            python_version=self.python_version,
        )
        self._created = files
        return files
