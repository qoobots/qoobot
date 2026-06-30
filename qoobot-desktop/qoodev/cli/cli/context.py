"""
Project context detection.

Discovers QooBot project metadata from the current working directory
by looking for qoo.toml configuration files.
"""

from __future__ import annotations

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11 compatibility

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class ProjectContext:
    """Represents a QooBot project detected from the filesystem."""

    name: str
    project_type: str
    root: Path
    version: str = "0.1.0"
    python_version: str = "3.11"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_cwd(cls) -> Optional["ProjectContext"]:
        """Detect project from current working directory.

        Walks up the directory tree looking for qoo.toml.
        """
        return cls.from_path(Path.cwd())

    @classmethod
    def from_path(cls, path: Path) -> Optional["ProjectContext"]:
        """Detect project from a given path.

        Args:
            path: Starting directory to search from.

        Returns:
            ProjectContext if found, None otherwise.
        """
        for parent in [path, *path.parents]:
            config_file = parent / "qoo.toml"
            if config_file.exists():
                return cls._parse(parent, config_file)
        return None

    @classmethod
    def _parse(cls, root: Path, config_file: Path) -> "ProjectContext":
        """Parse a qoo.toml configuration file."""
        with open(config_file, "rb") as f:
            data = tomllib.load(f)

        project = data.get("project", {})
        return cls(
            name=project.get("name", root.name),
            project_type=project.get("type", "skill"),
            root=root,
            version=project.get("version", "0.1.0"),
            python_version=project.get("python_version", "3.11"),
            metadata=project.get("metadata", {}),
        )

    @property
    def src_dir(self) -> Path:
        """Source directory path."""
        return self.root / "src"

    @property
    def test_dir(self) -> Path:
        """Test directory path."""
        return self.root / "tests"

    @property
    def build_dir(self) -> Path:
        """Build output directory."""
        return self.root / "build"
