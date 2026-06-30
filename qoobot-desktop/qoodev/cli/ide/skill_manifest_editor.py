"""
Skill Manifest Editor — v1.6+

Visual editor for QooBot skill manifests (.qooskills metadata).
Provides programmatic API for creating, editing, and validating skill manifests
with metadata, permission declarations, and privacy labels.

The editor is designed to be used both as a CLI tool and as a backend for
IDE-integrated visual editors (VS Code / JetBrains).

Usage:
    from cli.ide import SkillManifestEditor

    editor = SkillManifestEditor("my_skill")
    editor.set_permissions(["camera.rgb_front", "control.right_arm"])
    editor.set_privacy_label("camera_data", "Used for object detection")
    editor.validate()
    editor.save()
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint

console = Console()


# ============================================================================
# Data Models
# ============================================================================

class SkillCategory(Enum):
    """QooBot skill categories."""
    MANIPULATION = "manipulation"
    NAVIGATION = "navigation"
    PERCEPTION = "perception"
    INTERACTION = "interaction"
    DIAGNOSTICS = "diagnostics"
    UTILITY = "utility"
    EXPERIMENTAL = "experimental"


class PrivacySensitivity(Enum):
    """Privacy data sensitivity levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PermissionLevel(Enum):
    """Permission access levels."""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class PrivacyLabel:
    """A single privacy label declaration."""
    data_type: str
    purpose: str
    sensitivity: PrivacySensitivity = PrivacySensitivity.MEDIUM
    retention_days: int = 30
    shared_with_cloud: bool = False
    user_controllable: bool = True
    justification: str = ""

    def to_dict(self) -> dict:
        return {
            "data_type": self.data_type,
            "purpose": self.purpose,
            "sensitivity": self.sensitivity.value,
            "retention_days": self.retention_days,
            "shared_with_cloud": self.shared_with_cloud,
            "user_controllable": self.user_controllable,
            "justification": self.justification,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PrivacyLabel":
        return cls(
            data_type=data.get("data_type", ""),
            purpose=data.get("purpose", ""),
            sensitivity=PrivacySensitivity(data.get("sensitivity", "medium")),
            retention_days=data.get("retention_days", 30),
            shared_with_cloud=data.get("shared_with_cloud", False),
            user_controllable=data.get("user_controllable", True),
            justification=data.get("justification", ""),
        )


@dataclass
class Permission:
    """A single permission declaration."""
    resource: str
    level: PermissionLevel = PermissionLevel.READ
    reason: str = ""
    required: bool = True

    def to_dict(self) -> dict:
        return {
            "resource": self.resource,
            "level": self.level.value,
            "reason": self.reason,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Permission":
        return cls(
            resource=data.get("resource", ""),
            level=PermissionLevel(data.get("level", "read")),
            reason=data.get("reason", ""),
            required=data.get("required", True),
        )


@dataclass
class SkillManifest:
    """Complete skill manifest data model."""
    name: str
    version: str = "0.1.0"
    author: str = ""
    description: str = ""
    category: SkillCategory = SkillCategory.UTILITY
    icon: str = ""

    # Permissions
    permissions: List[Permission] = field(default_factory=list)

    # Privacy
    privacy_labels: List[PrivacyLabel] = field(default_factory=list)
    privacy_policy_url: str = ""

    # Dependencies
    dependencies: Dict[str, str] = field(default_factory=dict)
    min_robot_firmware: str = "1.0.0"
    min_qoocore_version: str = "0.3.0"

    # Metadata
    tags: List[str] = field(default_factory=list)
    homepage: str = ""
    repository: str = ""
    license: str = "MIT"
    changelog: str = ""

    # Runtime
    entry_point: str = "skill.py"
    language: str = "python"
    max_memory_mb: int = 512
    max_gpu_memory_mb: int = 0
    timeout_seconds: int = 300

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "category": self.category.value,
            "icon": self.icon,
            "permissions": [p.to_dict() for p in self.permissions],
            "privacy": {
                "labels": [l.to_dict() for l in self.privacy_labels],
                "policy_url": self.privacy_policy_url,
            },
            "dependencies": self.dependencies,
            "min_robot_firmware": self.min_robot_firmware,
            "min_qoocore_version": self.min_qoocore_version,
            "tags": self.tags,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "changelog": self.changelog,
            "runtime": {
                "entry_point": self.entry_point,
                "language": self.language,
                "max_memory_mb": self.max_memory_mb,
                "max_gpu_memory_mb": self.max_gpu_memory_mb,
                "timeout_seconds": self.timeout_seconds,
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillManifest":
        runtime = data.get("runtime", {})
        privacy = data.get("privacy", {})

        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.1.0"),
            author=data.get("author", ""),
            description=data.get("description", ""),
            category=SkillCategory(data.get("category", "utility")),
            icon=data.get("icon", ""),
            permissions=[Permission.from_dict(p) for p in data.get("permissions", [])],
            privacy_labels=[PrivacyLabel.from_dict(l) for l in privacy.get("labels", [])],
            privacy_policy_url=privacy.get("policy_url", ""),
            dependencies=data.get("dependencies", {}),
            min_robot_firmware=data.get("min_robot_firmware", "1.0.0"),
            min_qoocore_version=data.get("min_qoocore_version", "0.3.0"),
            tags=data.get("tags", []),
            homepage=data.get("homepage", ""),
            repository=data.get("repository", ""),
            license=data.get("license", "MIT"),
            changelog=data.get("changelog", ""),
            entry_point=runtime.get("entry_point", "skill.py"),
            language=runtime.get("language", "python"),
            max_memory_mb=runtime.get("max_memory_mb", 512),
            max_gpu_memory_mb=runtime.get("max_gpu_memory_mb", 0),
            timeout_seconds=runtime.get("timeout_seconds", 300),
        )


# ============================================================================
# Known Resource Registry
# ============================================================================

# All known QooBot hardware/software resources that can be permissioned
KNOWN_RESOURCES = {
    # Sensors
    "camera.rgb_front": "Front RGB camera (640x480 @ 30fps)",
    "camera.rgb_left": "Left side RGB camera",
    "camera.rgb_right": "Right side RGB camera",
    "camera.depth_front": "Front depth camera (ToF)",
    "camera.rgbd_front": "Front RGB-D camera",
    "lidar.os1_64": "Ouster OS1-64 LiDAR",
    "lidar.front_solid": "Front solid-state LiDAR",
    "imu.body": "Body IMU (9-axis)",
    "imu.head": "Head IMU (6-axis)",
    "microphone.array": "Microphone array (4-channel)",
    "speaker.stereo": "Stereo speakers",
    "force_torque.left_wrist": "Left wrist F/T sensor",
    "force_torque.right_wrist": "Right wrist F/T sensor",
    "touch.skin": "Whole-body tactile skin",
    "gps.receiver": "GPS/GNSS receiver",

    # Actuators
    "control.head": "Head pan/tilt control",
    "control.left_arm": "Left arm (7-DOF)",
    "control.right_arm": "Right arm (7-DOF)",
    "control.left_hand": "Left hand/gripper",
    "control.right_hand": "Right hand/gripper",
    "control.torso": "Torso lift control",
    "control.mobile_base": "Mobile base (differential drive)",
    "control.whole_body": "Whole-body coordinated control",

    # System
    "system.led": "LED indicators",
    "system.display": "Face display / screen",
    "system.audio": "Audio output",
    "system.tts": "Text-to-speech engine",
    "system.storage": "Persistent storage access",
    "system.network": "Network access (WiFi/Ethernet)",
    "system.bluetooth": "Bluetooth access",
    "system.power": "Power management",

    # Data
    "data.logging": "Write to system logs",
    "data.telemetry": "Send telemetry data",
    "data.cloud_sync": "Sync data to cloud",
    "data.export": "Export data off-device",
}


# ============================================================================
# Validation Rules
# ============================================================================

class ValidationSeverity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A validation issue found during manifest validation."""
    severity: ValidationSeverity
    field: str
    message: str
    suggestion: str = ""


# ============================================================================
# Skill Manifest Editor
# ============================================================================

class SkillManifestEditor:
    """Editor for creating and editing QooBot skill manifests.

    Provides a programmatic API and CLI interface for:
    - Creating new skill manifests from templates
    - Loading/editing existing manifest.yaml files
    - Adding/removing permissions with known resource validation
    - Declaring privacy labels with sensitivity levels
    - Validating manifests against QooBot platform requirements
    - Exporting to YAML/JSON formats
    """

    _VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
    _NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
    _EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    _URL_RE = re.compile(r"^https?://")

    def __init__(self, name: str, path: Optional[Path] = None):
        """Initialize the editor.

        Args:
            name: Skill name (snake_case, 2-64 chars)
            path: Optional path to existing manifest.yaml
        """
        self._path = path
        if path and path.exists():
            self._manifest = self._load(path)
        else:
            self._manifest = SkillManifest(name=name)
        self._dirty = False

    # ── Property Access ────────────────────────────────────────────────────

    @property
    def manifest(self) -> SkillManifest:
        return self._manifest

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    # ── Loading / Saving ────────────────────────────────────────────────────

    @classmethod
    def from_path(cls, path: Path) -> "SkillManifestEditor":
        """Create editor from an existing manifest file."""
        return cls(name="", path=path)

    def load(self, path: Path) -> None:
        """Load manifest from a YAML/JSON file."""
        self._manifest = self._load(path)
        self._path = path
        self._dirty = False
        console.print(f"[green]✓[/green] Loaded manifest: [bold]{self._manifest.name}[/bold] v{self._manifest.version}")

    def save(self, path: Optional[Path] = None) -> Path:
        """Save manifest to a file.

        Args:
            path: Output path (defaults to loaded path or 'manifest.yaml')

        Returns:
            Path to saved file.
        """
        output = path or self._path or Path("manifest.yaml")
        output = Path(output)

        # Auto-detect format from extension
        data = self._manifest.to_dict()
        if output.suffix in (".yaml", ".yml"):
            content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        elif output.suffix == ".json":
            content = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            output = output.with_suffix(".yaml")
            content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        self._dirty = False
        console.print(f"[green]✓[/green] Saved manifest to: [bold]{output}[/bold]")
        return output

    def _load(self, path: Path) -> SkillManifest:
        """Load manifest from file."""
        raw = path.read_text(encoding="utf-8")
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(raw) or {}
        elif path.suffix == ".json":
            data = json.loads(raw)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")
        return SkillManifest.from_dict(data)

    # ── Metadata Editing ────────────────────────────────────────────────────

    def set_metadata(
        self,
        version: Optional[str] = None,
        author: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        license: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Set basic metadata fields."""
        if version:
            if not self._VERSION_RE.match(version):
                raise ValueError(f"Invalid version format: {version}. Use semver (e.g., 1.0.0)")
            self._manifest.version = version
        if author is not None:
            self._manifest.author = author
        if description is not None:
            self._manifest.description = description
        if category:
            self._manifest.category = SkillCategory(category)
        if license is not None:
            self._manifest.license = license
        if tags is not None:
            self._manifest.tags = tags
        self._dirty = True

    def set_runtime(
        self,
        entry_point: Optional[str] = None,
        language: Optional[str] = None,
        max_memory_mb: Optional[int] = None,
        max_gpu_memory_mb: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
    ) -> None:
        """Set runtime configuration."""
        if entry_point:
            self._manifest.entry_point = entry_point
        if language:
            self._manifest.language = language
        if max_memory_mb is not None:
            self._manifest.max_memory_mb = max_memory_mb
        if max_gpu_memory_mb is not None:
            self._manifest.max_gpu_memory_mb = max_gpu_memory_mb
        if timeout_seconds is not None:
            self._manifest.timeout_seconds = timeout_seconds
        self._dirty = True

    # ── Permission Editing ──────────────────────────────────────────────────

    def add_permission(
        self,
        resource: str,
        level: str = "read",
        reason: str = "",
        required: bool = True,
    ) -> None:
        """Add a permission to the manifest.

        Args:
            resource: Resource identifier (e.g., 'camera.rgb_front')
            level: Access level (read/write/execute/admin)
            reason: Why this permission is needed
            required: Whether this permission is required (vs optional)
        """
        # Validate resource exists
        if resource not in KNOWN_RESOURCES:
            console.print(f"[yellow]⚠[/yellow] Unknown resource: [bold]{resource}[/bold]")
            console.print(f"  Known resources: {', '.join(sorted(KNOWN_RESOURCES.keys())[:10])}...")

        # Check for duplicates
        for p in self._manifest.permissions:
            if p.resource == resource:
                console.print(f"[yellow]⚠[/yellow] Permission already exists: {resource}")
                return

        perm = Permission(
            resource=resource,
            level=PermissionLevel(level),
            reason=reason,
            required=required,
        )
        self._manifest.permissions.append(perm)
        self._dirty = True
        console.print(f"[green]✓[/green] Added permission: [bold]{resource}[/bold] ({level})")

    def remove_permission(self, resource: str) -> bool:
        """Remove a permission by resource name."""
        before = len(self._manifest.permissions)
        self._manifest.permissions = [
            p for p in self._manifest.permissions if p.resource != resource
        ]
        removed = before > len(self._manifest.permissions)
        if removed:
            self._dirty = True
            console.print(f"[green]✓[/green] Removed permission: [bold]{resource}[/bold]")
        else:
            console.print(f"[yellow]⚠[/yellow] Permission not found: {resource}")
        return removed

    def list_permissions(self) -> Table:
        """Display permissions as a Rich table."""
        table = Table(title="Skill Permissions")
        table.add_column("Resource", style="cyan")
        table.add_column("Level", style="yellow")
        table.add_column("Required")
        table.add_column("Reason", style="dim")

        for p in self._manifest.permissions:
            table.add_row(
                p.resource,
                p.level.value,
                "✓" if p.required else "○",
                p.reason or "-",
            )

        console.print(table)
        return table

    @classmethod
    def list_known_resources(cls, filter_str: str = "") -> Table:
        """List all known resources that can be permissioned."""
        table = Table(title="Known QooBot Resources")
        table.add_column("Resource ID", style="cyan")
        table.add_column("Description", style="dim")

        resources = KNOWN_RESOURCES
        if filter_str:
            resources = {k: v for k, v in resources.items() if filter_str.lower() in k.lower()}

        for res_id, desc in sorted(resources.items()):
            table.add_row(res_id, desc)

        console.print(table)
        return table

    # ── Privacy Label Editing ───────────────────────────────────────────────

    def add_privacy_label(
        self,
        data_type: str,
        purpose: str,
        sensitivity: str = "medium",
        retention_days: int = 30,
        shared_with_cloud: bool = False,
        user_controllable: bool = True,
        justification: str = "",
    ) -> None:
        """Add a privacy label declaration."""
        label = PrivacyLabel(
            data_type=data_type,
            purpose=purpose,
            sensitivity=PrivacySensitivity(sensitivity),
            retention_days=retention_days,
            shared_with_cloud=shared_with_cloud,
            user_controllable=user_controllable,
            justification=justification,
        )
        self._manifest.privacy_labels.append(label)
        self._dirty = True
        console.print(f"[green]✓[/green] Added privacy label: [bold]{data_type}[/bold] ({sensitivity})")

    def remove_privacy_label(self, data_type: str) -> bool:
        """Remove a privacy label by data type."""
        before = len(self._manifest.privacy_labels)
        self._manifest.privacy_labels = [
            l for l in self._manifest.privacy_labels if l.data_type != data_type
        ]
        removed = before > len(self._manifest.privacy_labels)
        if removed:
            self._dirty = True
            console.print(f"[green]✓[/green] Removed privacy label: [bold]{data_type}[/bold]")
        return removed

    def list_privacy_labels(self) -> Table:
        """Display privacy labels as a Rich table."""
        table = Table(title="Privacy Labels")
        table.add_column("Data Type", style="cyan")
        table.add_column("Purpose", style="dim")
        table.add_column("Sensitivity")
        table.add_column("Retention")
        table.add_column("Cloud")
        table.add_column("User Ctrl")

        sensitivity_colors = {
            PrivacySensitivity.NONE: "dim",
            PrivacySensitivity.LOW: "green",
            PrivacySensitivity.MEDIUM: "yellow",
            PrivacySensitivity.HIGH: "red",
            PrivacySensitivity.CRITICAL: "bold red",
        }

        for l in self._manifest.privacy_labels:
            sens_color = sensitivity_colors.get(l.sensitivity, "")
            table.add_row(
                l.data_type,
                l.purpose or "-",
                f"[{sens_color}]{l.sensitivity.value}[/{sens_color}]",
                f"{l.retention_days}d",
                "☁" if l.shared_with_cloud else "-",
                "✓" if l.user_controllable else "✗",
            )

        console.print(table)
        return table

    # ── Dependency Management ───────────────────────────────────────────────

    def add_dependency(self, name: str, version: str) -> None:
        """Add a dependency."""
        self._manifest.dependencies[name] = version
        self._dirty = True
        console.print(f"[green]✓[/green] Added dependency: [bold]{name}[/bold] {version}")

    def remove_dependency(self, name: str) -> bool:
        """Remove a dependency."""
        if name in self._manifest.dependencies:
            del self._manifest.dependencies[name]
            self._dirty = True
            console.print(f"[green]✓[/green] Removed dependency: [bold]{name}[/bold]")
            return True
        return False

    # ── Validation ──────────────────────────────────────────────────────────

    def validate(self) -> List[ValidationIssue]:
        """Validate the manifest against QooBot platform requirements.

        Returns:
            List of validation issues (empty if valid).
        """
        issues: List[ValidationIssue] = []
        m = self._manifest

        # Required fields
        if not m.name:
            issues.append(ValidationIssue(ValidationSeverity.ERROR, "name", "Skill name is required"))
        elif not self._NAME_RE.match(m.name):
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "name",
                f"Invalid skill name: '{m.name}'. Must be snake_case, 2-64 chars.",
                "Use lowercase letters, numbers, and underscores (e.g., 'grasp_detector')"
            ))

        if not m.version:
            issues.append(ValidationIssue(ValidationSeverity.ERROR, "version", "Version is required"))
        elif not self._VERSION_RE.match(m.version):
            issues.append(ValidationIssue(
                ValidationSeverity.ERROR, "version",
                f"Invalid version: '{m.version}'. Must be semver (e.g., 1.0.0)"
            ))

        if not m.description:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING, "description",
                "Description is recommended for qoostore listing"
            ))

        # Permissions
        for perm in m.permissions:
            if perm.resource not in KNOWN_RESOURCES:
                issues.append(ValidationIssue(
                    ValidationSeverity.WARNING, f"permissions.{perm.resource}",
                    f"Unknown resource: '{perm.resource}'",
                    f"Use one of: {', '.join(sorted(KNOWN_RESOURCES.keys())[:5])}..."
                ))

        # Privacy
        for label in m.privacy_labels:
            if label.sensitivity in (PrivacySensitivity.HIGH, PrivacySensitivity.CRITICAL):
                if not label.justification:
                    issues.append(ValidationIssue(
                        ValidationSeverity.WARNING, f"privacy.{label.data_type}",
                        f"High-sensitivity data '{label.data_type}' needs justification"
                    ))
                if label.shared_with_cloud and not m.privacy_policy_url:
                    issues.append(ValidationIssue(
                        ValidationSeverity.ERROR, "privacy.policy_url",
                        "Privacy policy URL required when sharing high-sensitivity data with cloud"
                    ))

        # Dependencies
        if "qoobot-sdk" not in m.dependencies:
            issues.append(ValidationIssue(
                ValidationSeverity.INFO, "dependencies",
                "Consider adding 'qoobot-sdk' as a dependency"
            ))

        # Runtime
        if m.language not in ("python", "cpp", "python,cpp"):
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING, "runtime.language",
                f"Unrecognized language: '{m.language}'",
                "Use 'python', 'cpp', or 'python,cpp'"
            ))

        if m.max_memory_mb > 4096:
            issues.append(ValidationIssue(
                ValidationSeverity.WARNING, "runtime.max_memory_mb",
                f"Memory limit {m.max_memory_mb}MB is high. Consider optimizing."
            ))

        # Print results
        self._print_validation(issues)
        return issues

    def _print_validation(self, issues: List[ValidationIssue]) -> None:
        """Print validation results."""
        if not issues:
            console.print(Panel.fit(
                "[bold green]✓ Manifest is valid![/bold green]",
                border_style="green"
            ))
            return

        errors = [i for i in issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in issues if i.severity == ValidationSeverity.WARNING]
        infos = [i for i in issues if i.severity == ValidationSeverity.INFO]

        summary = f"[red]{len(errors)} errors[/red]  [yellow]{len(warnings)} warnings[/yellow]  [dim]{len(infos)} info[/dim]"
        console.print(Panel.fit(summary, title="Validation Results", border_style="red" if errors else "yellow"))

        for issue in issues:
            icon = {"error": "✗", "warning": "⚠", "info": "ℹ"}[issue.severity.value]
            style = {"error": "red", "warning": "yellow", "info": "dim"}[issue.severity.value]
            msg = f"[{style}]{icon} [{issue.field}][/{style}] {issue.message}"
            console.print(msg)
            if issue.suggestion:
                console.print(f"  [dim]→ {issue.suggestion}[/dim]")

    # ── Display ─────────────────────────────────────────────────────────────

    def show(self) -> None:
        """Display the full manifest in a formatted panel."""
        m = self._manifest

        # Basic info
        console.print(Panel.fit(
            f"[bold cyan]{m.name}[/bold cyan] v{m.version}\n"
            f"[dim]{m.description or '(no description)'}[/dim]",
            title="Skill Manifest",
            border_style="cyan",
        ))

        # Metadata table
        meta = Table(show_header=False, box=None, padding=(0, 1))
        meta.add_column(style="bold cyan")
        meta.add_column(style="white")
        meta.add_row("Author", m.author or "-")
        meta.add_row("Category", m.category.value)
        meta.add_row("License", m.license)
        meta.add_row("Tags", ", ".join(m.tags) if m.tags else "-")
        meta.add_row("Entry Point", m.entry_point)
        meta.add_row("Language", m.language)
        meta.add_row("Memory Limit", f"{m.max_memory_mb} MB")
        meta.add_row("Timeout", f"{m.timeout_seconds}s")
        console.print(meta)

        # Permissions
        if m.permissions:
            self.list_permissions()

        # Privacy
        if m.privacy_labels:
            self.list_privacy_labels()

        # Dependencies
        if m.dependencies:
            dep_table = Table(title="Dependencies")
            dep_table.add_column("Package", style="cyan")
            dep_table.add_column("Version", style="yellow")
            for name, ver in m.dependencies.items():
                dep_table.add_row(name, ver)
            console.print(dep_table)

    # ── Template Generation ─────────────────────────────────────────────────

    @classmethod
    def create_from_template(
        cls,
        name: str,
        template: str = "default",
    ) -> "SkillManifestEditor":
        """Create a new manifest from a template.

        Templates:
            - default: Generic skill with camera + arm permissions
            - perception: Computer vision skill
            - navigation: Autonomous navigation skill
            - interaction: HRI (Human-Robot Interaction) skill
            - minimal: Bare minimum manifest
        """
        editor = cls(name=name)

        templates = {
            "default": lambda e: _apply_default_template(e),
            "perception": lambda e: _apply_perception_template(e),
            "navigation": lambda e: _apply_navigation_template(e),
            "interaction": lambda e: _apply_interaction_template(e),
            "minimal": lambda e: None,  # Already minimal
        }

        apply_fn = templates.get(template, templates["default"])
        if apply_fn:
            apply_fn(editor)

        return editor


# ============================================================================
# Template Helpers
# ============================================================================

def _apply_default_template(editor: SkillManifestEditor) -> None:
    editor.add_permission("camera.rgb_front", "read", "Object detection input")
    editor.add_permission("control.right_arm", "write", "Manipulation control")
    editor.add_permission("control.right_hand", "write", "Gripper control")
    editor.add_privacy_label("camera_data", "Object detection and recognition", "medium", 7)
    editor._manifest.dependencies["qoobot-sdk"] = ">=0.1.0"
    editor._manifest.tags = ["manipulation", "vision"]
    editor._dirty = True


def _apply_perception_template(editor: SkillManifestEditor) -> None:
    editor._manifest.category = SkillCategory.PERCEPTION
    editor.add_permission("camera.rgb_front", "read", "Visual perception")
    editor.add_permission("camera.depth_front", "read", "Depth estimation")
    editor.add_permission("lidar.os1_64", "read", "3D perception")
    editor.add_permission("imu.body", "read", "Motion compensation")
    editor.add_privacy_label("camera_data", "Scene understanding", "medium", 1)
    editor.add_privacy_label("lidar_data", "3D mapping", "low", 7)
    editor._manifest.dependencies["qoobot-sdk"] = ">=0.1.0"
    editor._manifest.dependencies["torch"] = ">=2.0"
    editor._manifest.tags = ["perception", "vision", "lidar", "deep-learning"]
    editor._dirty = True


def _apply_navigation_template(editor: SkillManifestEditor) -> None:
    editor._manifest.category = SkillCategory.NAVIGATION
    editor.add_permission("lidar.os1_64", "read", "Obstacle detection")
    editor.add_permission("imu.body", "read", "Odometry")
    editor.add_permission("gps.receiver", "read", "Global localization")
    editor.add_permission("control.mobile_base", "write", "Motion commands")
    editor.add_privacy_label("location_data", "Path planning", "medium", 1)
    editor._manifest.dependencies["qoobot-sdk"] = ">=0.1.0"
    editor._manifest.tags = ["navigation", "slam", "path-planning"]
    editor._dirty = True


def _apply_interaction_template(editor: SkillManifestEditor) -> None:
    editor._manifest.category = SkillCategory.INTERACTION
    editor.add_permission("microphone.array", "read", "Voice commands")
    editor.add_permission("speaker.stereo", "write", "Audio feedback")
    editor.add_permission("system.tts", "execute", "Speech synthesis")
    editor.add_permission("system.display", "write", "Visual feedback")
    editor.add_permission("camera.rgb_front", "read", "Face detection")
    editor.add_privacy_label("audio_data", "Voice interaction", "high", 1,
                             justification="Audio data processed on-device for voice commands")
    editor.add_privacy_label("camera_data", "Face recognition", "high", 1,
                             justification="Face data used only for personalization, not stored")
    editor._manifest.dependencies["qoobot-sdk"] = ">=0.1.0"
    editor._manifest.tags = ["hri", "voice", "face-recognition", "interaction"]
    editor._dirty = True
