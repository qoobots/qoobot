"""Tests for project context detection."""

from __future__ import annotations

import tempfile
from pathlib import Path

from qoodev.cli.context import ProjectContext


def test_no_project():
    """Context detection returns None when no qoo.toml exists."""
    with tempfile.TemporaryDirectory() as tmp:
        ctx = ProjectContext.from_path(Path(tmp))
        assert ctx is None


def test_detect_skill_project():
    """Detect a skill project from qoo.toml."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "src").mkdir()
        config = """[project]
name = "test-skill"
version = "0.2.0"
type = "skill"
"""
        (root / "qoo.toml").write_text(config)

        ctx = ProjectContext.from_path(root)
        assert ctx is not None
        assert ctx.name == "test-skill"
        assert ctx.version == "0.2.0"
        assert ctx.project_type == "skill"
        assert ctx.root == root


def test_detect_service_project():
    """Detect a service project from qoo.toml."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config = """[project]
name = "test-service"
type = "service"
"""
        (root / "qoo.toml").write_text(config)

        ctx = ProjectContext.from_path(root)
        assert ctx is not None
        assert ctx.project_type == "service"


def test_src_dir():
    """src_dir returns root/src."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        config = "[project]\nname = \"test\"\n"
        (root / "qoo.toml").write_text(config)

        ctx = ProjectContext.from_path(root)
        assert ctx is not None
        assert ctx.src_dir == root / "src"
        assert ctx.test_dir == root / "tests"
        assert ctx.build_dir == root / "build"
