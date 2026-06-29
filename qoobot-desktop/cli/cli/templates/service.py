"""
Service project template.

Creates a QooBot system service project (Python/C++ hybrid).
"""

from __future__ import annotations

from pathlib import Path
from typing import List


class ServiceTemplate:
    """Generates a QooBot service project."""

    QOO_TOML = '''\
[project]
name = "{name}"
type = "service"
version = "0.1.0"
description = "A QooBot system service"
python_version = "{python_version}"

[service]
entry_point = "src.service:main"
provides = []
consumes = []

[dependencies]
python = [
    "qoobot-sdk>=0.1.0",
]
'''

    MAIN_SERVICE = '''\
"""
{name} - QooBot System Service

A QooBot system service running on the Brain OS platform.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class {class_name}:
    """System service for {name}."""

    def __init__(self):
        self.name = "{name}"
        self.version = "0.1.0"
        self._running = False

    async def start(self) -> None:
        """Start the service."""
        self._running = True
        logger.info(f"Service {{self.name}} v{{self.version}} started")

    async def stop(self) -> None:
        """Stop the service."""
        self._running = False
        logger.info(f"Service {{self.name}} stopped")

    async def run(self) -> None:
        """Main service loop."""
        await self.start()
        try:
            while self._running:
                await asyncio.sleep(0.1)
        finally:
            await self.stop()


async def main():
    """Entry point for the service."""
    service = {class_name}()
    await service.run()


if __name__ == "__main__":
    asyncio.run(main())
'''

    TEST_SERVICE = '''\
"""Tests for {name} service."""

import pytest
from src.service import {class_name}


def test_service_creation():
    """Test that the service can be created."""
    service = {class_name}()
    assert service.name == "{name}"
    assert service.version == "0.1.0"
'''

    def generate(
        self, name: str, target_path: Path, python_version: str
    ) -> List[Path]:
        class_name = self._to_class_name(name)
        created = []

        dirs = [
            target_path,
            target_path / "src",
            target_path / "tests",
            target_path / "config",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)

        # qoo.toml
        f = target_path / "qoo.toml"
        f.write_text(self.QOO_TOML.format(name=name, python_version=python_version))
        created.append(f)

        # src/service.py
        f = target_path / "src" / "__init__.py"
        f.write_text('"""Service source package."""\n')
        created.append(f)

        f = target_path / "src" / "service.py"
        f.write_text(self.MAIN_SERVICE.format(name=name, class_name=class_name))
        created.append(f)

        # tests
        f = target_path / "tests" / "__init__.py"
        f.write_text('"""Test package."""\n')
        created.append(f)

        f = target_path / "tests" / "test_service.py"
        f.write_text(self.TEST_SERVICE.format(name=name, class_name=class_name))
        created.append(f)

        # .gitignore
        f = target_path / ".gitignore"
        f.write_text("__pycache__/\n*.pyc\nbuild/\ndist/\n*.egg-info/\n")
        created.append(f)

        return created

    @staticmethod
    def _to_class_name(name: str) -> str:
        return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))
