"""
qoodev Stability Framework — Global error handling, input validation, and crash reporting.

Provides robust error handling across all CLI commands and runtime environments.
"""

from cli.stability.error_handler import (
    qoodevError,
    qoodevCommandError,
    qoodevConfigError,
    qoodevNetworkError,
    qoodevBuildError,
    qoodevRuntimeError,
    qoodevValidationError,
    global_error_handler,
    ErrorContext,
    ErrorSeverity,
)
from cli.stability.input_validator import (
    InputValidator,
    ValidationRule,
    validate_project_name,
    validate_version_string,
    validate_path,
    validate_port,
    validate_url,
)
from cli.stability.crash_collector import (
    CrashReport,
    CrashCollector,
    CrashReporter,
    Symbolizer,
)

__all__ = [
    # Errors
    "qoodevError",
    "qoodevCommandError",
    "qoodevConfigError",
    "qoodevNetworkError",
    "qoodevBuildError",
    "qoodevRuntimeError",
    "qoodevValidationError",
    "global_error_handler",
    "ErrorContext",
    "ErrorSeverity",
    # Validators
    "InputValidator",
    "ValidationRule",
    "validate_project_name",
    "validate_version_string",
    "validate_path",
    "validate_port",
    "validate_url",
    # Crash
    "CrashReport",
    "CrashCollector",
    "CrashReporter",
    "Symbolizer",
]
