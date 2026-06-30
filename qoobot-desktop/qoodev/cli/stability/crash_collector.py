"""
Crash collection and reporting system.

Collects, aggregates, and optionally uploads crash/error reports
to a central service for analysis. Supports local symbolication
and anonymous telemetry.
"""

from __future__ import annotations

import json
import os
import platform
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from cli import __version__ as qoodev_version


# ---------------------------------------------------------------------------
# Crash Report
# ---------------------------------------------------------------------------

@dataclass
class CrashReport:
    """A single crash/error report."""

    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    qoodev_version: str = qoodev_version
    python_version: str = sys.version
    platform_info: Dict[str, str] = field(default_factory=lambda: {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
    })

    # Error details
    error_type: str = ""
    error_message: str = ""
    traceback_text: str = ""
    command: str = ""
    working_directory: str = ""

    # Context
    project_name: str = ""
    project_type: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "qoodev_version": self.qoodev_version,
            "python_version": self.python_version,
            "platform": self.platform_info,
            "error": {
                "type": self.error_type,
                "message": self.error_message,
                "traceback": self.traceback_text,
            },
            "context": {
                "command": self.command,
                "working_directory": self.working_directory,
                "project_name": self.project_name,
                "project_type": self.project_type,
            },
            "environment": self.environment,
            "extra": self.extra,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_exception(
        cls,
        exc_type: type,
        exc_value: BaseException,
        exc_tb: Any,
        command: str = "",
        project_name: str = "",
        project_type: str = "",
    ) -> "CrashReport":
        return cls(
            error_type=exc_type.__name__,
            error_message=str(exc_value),
            traceback_text="".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
            command=command,
            working_directory=str(Path.cwd()),
            project_name=project_name,
            project_type=project_type,
            environment=_sanitized_env(),
        )


def _sanitized_env() -> Dict[str, str]:
    """Collect environment variables, stripping secrets."""
    safe_vars = {}
    sensitive_keys = {"TOKEN", "KEY", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "AUTH"}
    for key, value in os.environ.items():
        if any(s in key.upper() for s in sensitive_keys):
            safe_vars[key] = "***REDACTED***"
        else:
            safe_vars[key] = value
    return safe_vars


# ---------------------------------------------------------------------------
# Symbolizer — Stack trace symbolization
# ---------------------------------------------------------------------------

class Symbolizer:
    """Symbolizes stack traces for C++/Python mixed code.

    Resolves addresses to function names using debug symbols
    from build artifacts.
    """

    def __init__(self, build_dir: Optional[Path] = None):
        self.build_dir = build_dir or Path.cwd() / "build"
        self._symbol_cache: Dict[str, str] = {}

    def symbolize(self, traceback_text: str) -> str:
        """Enhance traceback with symbol information."""
        lines = traceback_text.split("\n")
        result = []
        for line in lines:
            result.append(line)
            # Try to find native stack frames
            if "0x" in line and ("libqoo" in line or ".so" in line):
                resolved = self._resolve_address(line)
                if resolved:
                    result.append(f"         [symbolized] {resolved}")
        return "\n".join(result)

    def _resolve_address(self, line: str) -> Optional[str]:
        """Resolve a memory address to a function name."""
        # In production, this would call addr2line or llvm-symbolizer
        # For now, use the cache and pattern matching
        for addr in self._symbol_cache:
            if addr in line:
                return self._symbol_cache[addr]
        return None

    def load_symbols(self, binary_path: Path) -> None:
        """Load debug symbols from a binary."""
        # In production: parse DWARF/PDB symbols
        # Stub implementation
        if not binary_path.exists():
            return
        # Placeholder — actual symbol loading via pyelftools or similar
        pass


# ---------------------------------------------------------------------------
# Crash Collector
# ---------------------------------------------------------------------------

class CrashCollector:
    """Collects and stores crash reports locally.

    Reports are stored as JSON files in ~/.qoodev/crashes/
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".qoodev" / "crashes")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_reports: int = 100

    def collect(self, report: CrashReport) -> Path:
        """Store a crash report locally."""
        report_path = self.storage_dir / f"crash_{report.report_id}.json"
        report_path.write_text(report.to_json(), encoding="utf-8")
        self._prune_old_reports()
        return report_path

    def list_reports(self, limit: int = 20) -> List[CrashReport]:
        """List recent crash reports."""
        reports = []
        for f in sorted(self.storage_dir.glob("crash_*.json"), reverse=True):
            if len(reports) >= limit:
                break
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                reports.append(CrashReport(**data))
            except (json.JSONDecodeError, TypeError):
                continue
        return reports

    def get_report(self, report_id: str) -> Optional[CrashReport]:
        """Retrieve a specific crash report by ID."""
        report_path = self.storage_dir / f"crash_{report_id}.json"
        if not report_path.exists():
            return None
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            return CrashReport(**data)
        except (json.JSONDecodeError, TypeError):
            return None

    def clear_reports(self) -> int:
        """Delete all stored crash reports. Returns count of deleted files."""
        count = 0
        for f in self.storage_dir.glob("crash_*.json"):
            f.unlink()
            count += 1
        return count

    def _prune_old_reports(self) -> None:
        """Keep only the most recent N reports."""
        reports = sorted(self.storage_dir.glob("crash_*.json"), key=lambda f: f.stat().st_mtime)
        while len(reports) > self.max_reports:
            reports.pop(0).unlink()


# ---------------------------------------------------------------------------
# Crash Reporter — Remote upload
# ---------------------------------------------------------------------------

class CrashReporter:
    """Uploads crash reports to a remote collection service."""

    def __init__(
        self,
        endpoint_url: str = "",
        collector: Optional[CrashCollector] = None,
        enabled: bool = True,
    ):
        self.endpoint_url = endpoint_url
        self.collector = collector or CrashCollector()
        self.enabled = enabled

    def report(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb: Any,
        command: str = "",
        project_name: str = "",
        project_type: str = "",
    ) -> Optional[str]:
        """Create and optionally upload a crash report.

        Returns the report ID, or None if disabled.
        """
        report = CrashReport.from_exception(
            exc_type, exc_value, exc_tb,
            command=command,
            project_name=project_name,
            project_type=project_type,
        )

        # Always store locally
        self.collector.collect(report)

        # Upload if enabled and endpoint configured
        if self.enabled and self.endpoint_url:
            self._upload(report)

        return report.report_id

    def _upload(self, report: CrashReport) -> bool:
        """Upload a crash report to the remote endpoint."""
        try:
            import urllib.request

            data = report.to_json().encode("utf-8")
            req = urllib.request.Request(
                self.endpoint_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            # Never let crash reporting itself cause a crash
            return False


# ---------------------------------------------------------------------------
# Convenience: install global crash hook
# ---------------------------------------------------------------------------

def install_crash_hook(
    collector: Optional[CrashCollector] = None,
    reporter: Optional[CrashReporter] = None,
    command: str = "",
) -> None:
    """Install a global exception hook that captures crashes.

    Usage:
        install_crash_hook(command="qoo build")
    """
    collector = collector or CrashCollector()
    reporter = reporter or CrashReporter(collector=collector)
    original_hook = sys.excepthook

    def crash_hook(exc_type, exc_value, exc_tb):
        try:
            reporter.report(exc_type, exc_value, exc_tb, command=command)
        except Exception:
            pass  # Crash reporting must never fail
        original_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = crash_hook
