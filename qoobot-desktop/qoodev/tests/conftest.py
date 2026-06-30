"""Pytest configuration for qoodev tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory with basic structure."""
    project = tmp_path / "test_project"
    project.mkdir()
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "config").mkdir()

    # Create a minimal qoo.toml
    (project / "qoo.toml").write_text("""[project]
name = "test-project"
version = "0.1.0"
type = "skill"
""")
    return project
