"""Tests for skill packaging system."""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from qoodev.packager.package_format import (
    PackageBuilder,
    PackageManifest,
    PackageReader,
    PackageValidator,
    SkillCategory,
    SkillRuntime,
)


def test_manifest_creation():
    """PackageManifest can be created with required fields."""
    manifest = PackageManifest(
        name="com.test.skill",
        version="1.0.0",
        display_name="Test Skill",
        description="A test skill",
        author="Test Author",
        entry_point="src.skill:TestSkill",
    )
    assert manifest.name == "com.test.skill"
    assert manifest.version == "1.0.0"
    assert manifest.entry_point == "src.skill:TestSkill"
    assert manifest.category == SkillCategory.UTILITY
    assert manifest.runtime == SkillRuntime.PYTHON


def test_manifest_to_dict():
    """PackageManifest serializes to dict correctly."""
    manifest = PackageManifest(
        name="com.test.skill",
        version="1.0.0",
        display_name="Test Skill",
        description="A test skill",
        author="Test Author",
        entry_point="src.skill:TestSkill",
    )
    d = manifest.to_dict()
    assert d["name"] == "com.test.skill"
    assert d["version"] == "1.0.0"
    assert d["category"] == "utility"


def test_manifest_from_dict():
    """PackageManifest deserializes from dict correctly."""
    data = {
        "name": "com.example.demo",
        "version": "2.0.0",
        "display_name": "Demo",
        "description": "A demo skill",
        "category": "control",
        "runtime": "python",
        "author": "Dev",
        "entry_point": "demo:run",
    }
    manifest = PackageManifest.from_dict(data)
    assert manifest.name == "com.example.demo"
    assert manifest.version == "2.0.0"
    assert manifest.category == SkillCategory.CONTROL


def test_package_builder_creates_zip():
    """PackageBuilder creates a valid .qooskills ZIP with auto-loaded manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Create source files
        python_dir = root / "python"
        python_dir.mkdir()
        (python_dir / "__init__.py").write_text("")
        (python_dir / "skill.py").write_text("class TestSkill:\n    pass\n")

        # Create manifest.json
        manifest = {
            "name": "com.test.skill",
            "version": "1.0.0",
            "display_name": "Test Skill",
            "description": "A test skill",
            "author": "Test Author",
            "entry_point": "skill:TestSkill",
        }
        (root / "manifest.json").write_text(json.dumps(manifest))

        builder = PackageBuilder(root)
        builder.load_manifest()
        output = builder.build()

        assert output.exists()
        # Verify it's a valid ZIP
        with zipfile.ZipFile(output, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert any("skill.py" in n for n in names)


def test_package_builder_includes_manifest_content():
    """PackageBuilder includes manifest.json with correct content."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        python_dir = root / "python"
        python_dir.mkdir()
        (python_dir / "__init__.py").write_text("")
        (python_dir / "skill.py").write_text("class DemoSkill:\n    pass\n")

        manifest = {
            "name": "com.test.demo",
            "version": "2.0.0",
            "display_name": "Demo",
            "description": "Test",
            "author": "Author",
            "entry_point": "skill:DemoSkill",
        }
        (root / "manifest.json").write_text(json.dumps(manifest))

        builder = PackageBuilder(root)
        builder.load_manifest()
        output = builder.build()

        with zipfile.ZipFile(output, "r") as zf:
            manifest_data = json.loads(zf.read("manifest.json"))
            assert manifest_data["name"] == "com.test.demo"
            assert manifest_data["version"] == "2.0.0"


def test_package_reader():
    """PackageReader can read manifest and files from a package."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        python_dir = root / "python"
        python_dir.mkdir()
        (python_dir / "__init__.py").write_text("")
        (python_dir / "skill.py").write_text("class TestSkill:\n    pass\n")

        manifest = {
            "name": "com.test.reader",
            "version": "1.0.0",
            "display_name": "Reader Test",
            "description": "Testing reader",
            "author": "Tester",
            "entry_point": "skill:TestSkill",
        }
        (root / "manifest.json").write_text(json.dumps(manifest))

        builder = PackageBuilder(root)
        builder.load_manifest()
        output = builder.build()

        reader = PackageReader(output)
        read_manifest = reader.read_manifest()
        assert read_manifest.name == "com.test.reader"
        assert read_manifest.version == "1.0.0"

        files = reader.list_files()
        assert "manifest.json" in files


def test_package_validator():
    """PackageValidator checks structure and manifest."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        python_dir = root / "python"
        python_dir.mkdir()
        (python_dir / "__init__.py").write_text("")
        (python_dir / "skill.py").write_text("class TestSkill:\n    pass\n")

        manifest = {
            "name": "com.test.validate",
            "version": "1.0.0",
            "display_name": "Validator Test",
            "description": "Testing validator",
            "author": "Tester",
            "entry_point": "skill:TestSkill",
        }
        (root / "manifest.json").write_text(json.dumps(manifest))

        builder = PackageBuilder(root)
        builder.load_manifest()
        output = builder.build()

        result = PackageValidator.full_validate(output)
        assert result["errors"] == []
        assert "Manifest parse error" not in str(result["errors"])
