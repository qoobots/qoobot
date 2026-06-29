"""Symbol engine — document symbol outline for qoodev files."""

import logging
import re
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    DocumentSymbol,
    DocumentSymbolParams,
    Position,
    Range,
    SymbolKind,
)

logger = logging.getLogger("qoodev-lsp.symbols")


class QooSymbolEngine:
    """Provides document symbols for qoodev project files."""

    def get_symbols(self, ls: LanguageServer, params: DocumentSymbolParams) -> Optional[list[DocumentSymbol]]:
        doc = ls.workspace.get_text_document(params.text_document.uri)
        if doc is None:
            return None

        symbols: list[DocumentSymbol] = []

        lines = doc.source.split("\n")

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Class definitions
            m = re.match(r"class\s+(\w+)\s*(?:\(([^)]*)\))?\s*:", stripped)
            if m:
                class_name = m.group(1)
                bases = m.group(2) or ""
                detail = f"class {class_name}"
                if "QooSkill" in bases:
                    detail = f"🤖 {detail} ← QooSkill"
                elif "QooService" in bases:
                    detail = f"⚙ {detail} ← QooService"

                col = line.index("class")
                symbols.append(
                    DocumentSymbol(
                        name=class_name,
                        kind=SymbolKind.Class,
                        range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(class_name) + 5),
                        ),
                        selection_range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(class_name) + 5),
                        ),
                        detail=detail,
                        children=self._get_class_methods(lines, i + 1),
                    )
                )

            # Top-level function definitions
            m = re.match(r"def\s+(\w+)\s*\(", stripped)
            if m:
                func_name = m.group(1)
                col = line.index("def")
                symbols.append(
                    DocumentSymbol(
                        name=func_name,
                        kind=SymbolKind.Function,
                        range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(func_name) + 3),
                        ),
                        selection_range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(func_name) + 3),
                        ),
                    )
                )

        return symbols

    def _get_class_methods(self, lines: list[str], start_line: int) -> list[DocumentSymbol]:
        """Extract methods from a class body (simple indentation-based)."""
        methods: list[DocumentSymbol] = []

        for i in range(start_line, len(lines)):
            line = lines[i]
            stripped = line.strip()

            # Stop at unindented or other class
            if stripped and not line.startswith("    "):
                if stripped.startswith("class ") or stripped.startswith("def ") or stripped.startswith("@"):
                    if not line.startswith("    "):
                        break

            m = re.match(r"\s+def\s+(\w+)\s*\(", stripped)
            if m:
                func_name = m.group(1)
                col = line.index("def")
                # Determine kind: async lifecycle methods
                kind = SymbolKind.Method
                detail = None
                if func_name in ("setup", "loop", "teardown"):
                    detail = "🔄 Lifecycle"
                    kind = SymbolKind.Event
                elif func_name.startswith("on_"):
                    detail = "📡 Event handler"
                    kind = SymbolKind.Event

                methods.append(
                    DocumentSymbol(
                        name=func_name,
                        kind=kind,
                        range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(func_name) + 3),
                        ),
                        selection_range=Range(
                            start=Position(line=i, character=col),
                            end=Position(line=i, character=col + len(func_name) + 3),
                        ),
                        detail=detail,
                    )
                )

        return methods
