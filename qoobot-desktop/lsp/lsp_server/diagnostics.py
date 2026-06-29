"""Diagnostics engine — validates qoodev project files."""

import logging
import re
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    Diagnostic,
    DiagnosticSeverity,
    Position,
    Range,
)

logger = logging.getLogger("qoodev-lsp.diagnostics")


class QooDiagnosticEngine:
    """Provides project-aware diagnostics for qoodev files."""

    def __init__(self, server: LanguageServer):
        self.server = server

    def check_document(self, ls: LanguageServer, uri: str):
        """Run diagnostics on a document."""
        doc = ls.workspace.get_text_document(uri)
        if doc is None:
            return

        diagnostics: list[Diagnostic] = []

        if doc.uri.endswith(".py"):
            diagnostics.extend(self._check_python_skill(doc))

        ls.publish_diagnostics(doc.uri, diagnostics)

    def _check_python_skill(self, doc) -> list[Diagnostic]:
        """Check Python skill files for common issues."""
        diagnostics: list[Diagnostic] = []
        lines = doc.source.split("\n")

        for i, line in enumerate(lines):
            # Check for QooSkill subclass without required methods
            pass  # Deeper checks will be added as the SDK matures

        return diagnostics
