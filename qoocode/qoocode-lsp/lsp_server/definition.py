"""Definition engine — go-to-definition and find-references for qoocode projects."""

import logging
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    Location,
    Position,
    Range,
    DefinitionParams,
    ReferenceParams,
)

logger = logging.getLogger("qoocode-lsp.definition")


class QooDefinitionEngine:
    """Provides go-to-definition and find-references for qoobot-sdk symbols."""

    def go_to_definition(self, ls: LanguageServer, params: DefinitionParams) -> Optional[list[Location]]:
        doc = ls.workspace.get_text_document(params.text_document.uri)
        if doc is None:
            return None

        line = doc.lines[params.position.line] if params.position.line < len(doc.lines) else ""
        word = self._get_word_at_position(line, params.position.character)

        if word is None:
            return None

        # Search for definition across workspace
        for uri, ws_doc in ls.workspace.text_documents.items():
            text = ws_doc.source
            for i, text_line in enumerate(text.split("\n")):
                # Match class/function definitions
                if f"class {word}" in text_line or f"def {word}" in text_line:
                    col = text_line.index(word)
                    return [
                        Location(
                            uri=uri,
                            range=Range(
                                start=Position(line=i, character=col),
                                end=Position(line=i, character=col + len(word)),
                            ),
                        )
                    ]

        return None

    def find_references(self, ls: LanguageServer, params: ReferenceParams) -> Optional[list[Location]]:
        doc = ls.workspace.get_text_document(params.text_document.uri)
        if doc is None:
            return None

        line = doc.lines[params.position.line] if params.position.line < len(doc.lines) else ""
        word = self._get_word_at_position(line, params.position.character)

        if word is None:
            return None

        locations: list[Location] = []

        # Search for all references across workspace
        for uri, ws_doc in ls.workspace.text_documents.items():
            text = ws_doc.source
            start = 0
            while True:
                idx = text.find(word, start)
                if idx == -1:
                    break

                # Get line/col from character offset
                line_num = text[:idx].count("\n")
                last_nl = text[:idx].rfind("\n")
                col = idx - (last_nl + 1) if last_nl >= 0 else idx

                locations.append(
                    Location(
                        uri=uri,
                        range=Range(
                            start=Position(line=line_num, character=col),
                            end=Position(line=line_num, character=col + len(word)),
                        ),
                    )
                )
                start = idx + len(word)

        return locations

    def _get_word_at_position(self, line: str, col: int) -> Optional[str]:
        """Extract the word at the given column position."""
        if col >= len(line):
            return None

        start = col
        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        end = col
        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        if start < end:
            return line[start:end]

        return None
