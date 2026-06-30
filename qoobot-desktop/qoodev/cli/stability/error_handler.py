"""
Global error handling system.

Provides typed exceptions, contextual error reporting, and graceful degradation
for all qoodev operations.
"""

from __future__ import annotations

import enum
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any, Callable, Dict, Type

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Error Severity
# ---------------------------------------------------------------------------

class ErrorSeverity(enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


# ---------------------------------------------------------------------------
# Error Context
# ---------------------------------------------------------------------------

@dataclass
class ErrorContext:
    """Contextual information attached to an error."""
    command: str = ""
    project_root: Optional[Path] = None
    user_message: str = ""
    suggestion: str = ""
    severity: ErrorSeverity = ErrorSeverity.ERROR
    recoverable: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Base Exceptions
# ---------------------------------------------------------------------------

class qoodevError(Exception):
    """Base exception for all qoodev errors."""

    def __init__(
        self,
        message: str,
        ctx: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.ctx = ctx or ErrorContext(user_message=message)
        self.cause = cause


class qoodevCommandError(qoodevError):
    """Raised when a CLI command fails."""


class qoodevConfigError(qoodevError):
    """Raised for project configuration errors."""


class qoodevNetworkError(qoodevError):
    """Raised for network/connection failures."""


class qoodevBuildError(qoodevError):
    """Raised when build operations fail."""


class qoodevRuntimeError(qoodevError):
    """Raised for runtime/simulation failures."""


class qoodevValidationError(qoodevError):
    """Raised when input validation fails."""


# ---------------------------------------------------------------------------
# Global Error Handler
# ---------------------------------------------------------------------------

def global_error_handler(
    exit_on_error: bool = True,
    show_traceback: bool = False,
    report_url: Optional[str] = None,
) -> Callable:
    """Create a global exception hook that formats errors with rich output.

    Usage:
        sys.excepthook = global_error_handler()
    """

    def handler(exc_type: Type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
        if exc_type is KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user.[/yellow]")
            sys.exit(130)
            return

        if exc_type is SystemExit:
            sys.exit(exc_value.code if hasattr(exc_value, "code") else 1)
            return

        # Format the error
        if isinstance(exc_value, qoodevError):
            _render_qoodev_error(exc_value, show_traceback, report_url)
        else:
            _render_unexpected_error(exc_type, exc_value, exc_tb, show_traceback, report_url)

        if exit_on_error:
            sys.exit(1)

    return handler


def _render_qoodev_error(
    error: qoodevError,
    show_traceback: bool,
    report_url: Optional[str],
) -> None:
    """Render a typed qoodev error with rich formatting."""
    ctx = error.ctx

    # Error header
    severity_color = {
        ErrorSeverity.DEBUG: "dim",
        ErrorSeverity.INFO: "blue",
        ErrorSeverity.WARNING: "yellow",
        ErrorSeverity.ERROR: "red",
        ErrorSeverity.FATAL: "bold red",
    }
    color = severity_color.get(ctx.severity, "red")

    console.print()
    console.print(f"[{color}]━━━ qoodev Error ━━━[/{color}]")
    console.print(f"[{color} bold]{ctx.severity.value.upper()}[/{color} bold]: {ctx.user_message}")

    if ctx.command:
        console.print(f"  Command: [cyan]{ctx.command}[/cyan]")

    if ctx.suggestion:
        console.print(f"\n  [green]💡 {ctx.suggestion}[/green]")

    # Cause chain
    if error.cause:
        console.print(f"\n  [dim]Caused by: {type(error.cause).__name__}: {error.cause}[/dim]")

    if ctx.extra:
        extras_table = Table(show_header=False, box=None, padding=(0, 2))
        extras_table.add_column(style="dim")
        extras_table.add_column(style="white")
        for key, val in ctx.extra.items():
            extras_table.add_row(f"  {key}:", str(val))
        console.print(extras_table)

    if show_traceback and error.__traceback__:
        console.print("\n[dim]Traceback:[/dim]")
        tb_lines = traceback.format_exception(type(error), error, error.__traceback__)
        console.print(Syntax("".join(tb_lines), "python", theme="monokai"))

    if report_url:
        console.print(f"\n[dim]Crash report will be sent to: {report_url}[/dim]")

    console.print()


def _render_unexpected_error(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_tb: Any,
    show_traceback: bool,
    report_url: Optional[str],
) -> None:
    """Render an unexpected/uncaught exception."""
    console.print()
    console.print("[bold red]━━━ Unexpected Error ━━━[/bold red]")
    console.print(f"[red]{exc_type.__name__}: {exc_value}[/red]")

    if show_traceback:
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_tb)
        console.print("\n[dim]Traceback:[/dim]")
        console.print(Syntax("".join(tb_lines), "python", theme="monokai"))
    else:
        console.print("\n[dim]Run with --debug for full traceback.[/dim]")

    console.print("\n[yellow]This is an unexpected error. Please report it to the QooBot team.[/yellow]")
    if report_url:
        console.print(f"[dim]Report URL: {report_url}[/dim]")

    console.print()


# ---------------------------------------------------------------------------
# Context Manager for Error Boundaries
# ---------------------------------------------------------------------------

class ErrorBoundary:
    """Context manager that catches and wraps exceptions as qoodevError.

    Usage:
        with ErrorBoundary("build", suggestion="Check your project configuration"):
            do_build()
    """

    def __init__(
        self,
        command: str = "",
        suggestion: str = "",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        error_type: Type[qoodevError] = qoodevCommandError,
    ):
        self.command = command
        self.suggestion = suggestion
        self.severity = severity
        self.error_type = error_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if exc_value is None:
            return False

        if isinstance(exc_value, qoodevError):
            # Already a qoodev error, re-raise
            return False

        if isinstance(exc_value, (KeyboardInterrupt, SystemExit)):
            return False

        ctx = ErrorContext(
            command=self.command,
            user_message=str(exc_value),
            suggestion=self.suggestion,
            severity=self.severity,
        )
        raise self.error_type(str(exc_value), ctx=ctx, cause=exc_value) from exc_value
