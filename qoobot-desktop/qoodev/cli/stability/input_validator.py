"""
Input validation for all CLI inputs and configuration.

Provides reusable validation functions to ensure data integrity
before operations begin, preventing cryptic downstream errors.
"""

from __future__ import annotations

import re
import socket
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Callable, Any, Union

from cli.stability.error_handler import (
    qoodevValidationError,
    ErrorContext,
    ErrorSeverity,
)


# ---------------------------------------------------------------------------
# Validation Rule
# ---------------------------------------------------------------------------

@dataclass
class ValidationRule:
    """A single validation rule with error message."""

    check: Callable[[Any], bool]
    message: str
    field: str = ""


@dataclass
class InputValidator:
    """Validates input values against a set of rules.

    Usage:
        validator = InputValidator()
        validator.add(rule)
        validator.validate(value, field_name="project_name")
    """

    rules: List[ValidationRule] = field(default_factory=list)

    def add(self, rule: ValidationRule) -> "InputValidator":
        self.rules.append(rule)
        return self

    def add_if(self, condition: bool, rule: ValidationRule) -> "InputValidator":
        if condition:
            self.rules.append(rule)
        return self

    def validate(self, value: Any, field_name: str = "value") -> None:
        """Run all validation rules. Raises qoodevValidationError on failure."""
        for rule in self.rules:
            if not rule.check(value):
                ctx = ErrorContext(
                    user_message=rule.message.format(value=value),
                    suggestion=f"Please provide a valid {rule.field or field_name}.",
                    severity=ErrorSeverity.ERROR,
                )
                raise qoodevValidationError(rule.message.format(value=value), ctx=ctx)


# ---------------------------------------------------------------------------
# Built-in Validators
# ---------------------------------------------------------------------------

_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_\-]*$")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?(?:\+[a-zA-Z0-9.]+)?$")


def validate_project_name(name: str) -> None:
    """Validate a QooBot project name."""
    validator = InputValidator()
    validator.add(ValidationRule(
        check=lambda v: bool(v and v.strip()),
        message="Project name cannot be empty.",
        field="project_name",
    ))
    validator.add(ValidationRule(
        check=lambda v: 2 <= len(v) <= 64,
        message="Project name must be between 2 and 64 characters.",
        field="project_name",
    ))
    validator.add(ValidationRule(
        check=lambda v: bool(_PROJECT_NAME_RE.match(v)),
        message=f"Invalid project name '{{value}}'. Must start with a letter and contain only letters, digits, hyphens, and underscores.",
        field="project_name",
    ))
    validator.add(ValidationRule(
        check=lambda v: v.lower() not in _RESERVED_NAMES,
        message="'{value}' is a reserved name and cannot be used as a project name.",
        field="project_name",
    ))
    validator.validate(name, field_name="project_name")


_RESERVED_NAMES = {
    "qoo", "qoobot", "qoodev", "qoocore", "qoobrain", "qoostore", "qooauth",
    "skill", "service", "model", "test", "build", "src", "lib", "bin",
    "import", "class", "def", "if", "for", "while", "return", "yield",
    "none", "true", "false", "and", "or", "not", "is", "in",
}


def validate_version_string(version: str) -> None:
    """Validate a semantic version string."""
    validator = InputValidator()
    validator.add(ValidationRule(
        check=lambda v: bool(v and v.strip()),
        message="Version string cannot be empty.",
        field="version",
    ))
    validator.add(ValidationRule(
        check=lambda v: bool(_VERSION_RE.match(v)),
        message=f"Invalid version '{version}'. Must follow semver (e.g., 1.2.3).",
        field="version",
    ))
    validator.validate(version, field_name="version")


def validate_path(path: Union[str, Path], must_exist: bool = False, writable: bool = False) -> None:
    """Validate a filesystem path."""
    p = Path(path) if isinstance(path, str) else path

    validator = InputValidator()

    if must_exist:
        validator.add(ValidationRule(
            check=lambda v: Path(v).exists(),
            message=f"Path does not exist: '{path}'",
            field="path",
        ))

    if writable:
        validator.add(ValidationRule(
            check=lambda v: _is_writable(Path(v)),
            message=f"Path is not writable: '{path}'",
            field="path",
        ))

    # Prevent path traversal
    validator.add(ValidationRule(
        check=lambda v: ".." not in str(v).split("/") and ".." not in str(v).split("\\"),
        message="Path traversal ('..') is not allowed.",
        field="path",
    ))

    validator.validate(str(p), field_name="path")


def _is_writable(p: Path) -> bool:
    """Check if a path is writable."""
    if p.exists():
        return p.is_dir() and os.access(p, os.W_OK) if p.is_dir() else os.access(p.parent, os.W_OK)
    else:
        parent = p.parent
        return parent.exists() and os.access(parent, os.W_OK)


def validate_port(port: int) -> None:
    """Validate a network port number."""
    validator = InputValidator()
    validator.add(ValidationRule(
        check=lambda v: isinstance(v, int) and 1 <= v <= 65535,
        message=f"Invalid port number: {port}. Must be between 1 and 65535.",
        field="port",
    ))
    validator.add(ValidationRule(
        check=lambda v: v > 1024 or v in _WELL_KNOWN_PORTS,
        message=f"Port {port} is privileged (<1024) and not in the allowed well-known ports list.",
        field="port",
    ))
    validator.validate(port, field_name="port")


_WELL_KNOWN_PORTS = {80, 443, 8080, 8443}


def validate_url(url: str) -> None:
    """Validate a URL string."""
    validator = InputValidator()
    validator.add(ValidationRule(
        check=lambda v: bool(v and v.strip()),
        message="URL cannot be empty.",
        field="url",
    ))
    validator.add(ValidationRule(
        check=lambda v: v.startswith(("http://", "https://", "ws://", "wss://")),
        message=f"Invalid URL scheme: '{url}'. Must start with http://, https://, ws://, or wss://",
        field="url",
    ))
    validator.add(ValidationRule(
        check=lambda v: len(v) <= 2048,
        message="URL exceeds maximum length of 2048 characters.",
        field="url",
    ))
    validator.validate(url, field_name="url")


def validate_semver_range(spec: str) -> None:
    """Validate a semantic version range specifier (e.g., '>=1.0,<2.0')."""
    validator = InputValidator()
    validator.add(ValidationRule(
        check=lambda v: bool(v and v.strip()),
        message="Version range cannot be empty.",
        field="semver_range",
    ))
    # Basic sanity: must contain version-like patterns
    validator.add(ValidationRule(
        check=lambda v: bool(re.search(r"\d+\.\d+", v)),
        message=f"Invalid version range: '{spec}'. Must contain at least one version number.",
        field="semver_range",
    ))
    validator.validate(spec, field_name="semver_range")


def validate_email(email: str) -> None:
    """Validate an email address."""
    validator = InputValidator()
    validator.add(ValidationRule(
        check=lambda v: bool(v and v.strip()),
        message="Email cannot be empty.",
        field="email",
    ))
    validator.add(ValidationRule(
        check=lambda v: "@" in v and "." in v.split("@")[-1],
        message=f"Invalid email address: '{email}'.",
        field="email",
    ))
    validator.validate(email, field_name="email")


import os  # noqa: E402 — used in _is_writable
