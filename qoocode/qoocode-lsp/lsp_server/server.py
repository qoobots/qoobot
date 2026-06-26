"""qoocode LSP Server implementation using pygls."""

import logging
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_DOCUMENT_SYMBOL,
    TEXT_DOCUMENT_SIGNATURE_HELP,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_SAVE,
    CompletionOptions,
    CompletionParams,
    CompletionList,
    Hover,
    HoverParams,
    DefinitionParams,
    ReferenceParams,
    DocumentSymbol,
    DocumentSymbolParams,
    SignatureHelpParams,
    SignatureHelp,
    Location,
    INITIALIZED,
    InitializedParams,
)

from .completion import QooCompletionEngine
from .hover import QooHoverEngine
from .definition import QooDefinitionEngine
from .diagnostics import QooDiagnosticEngine
from .symbols import QooSymbolEngine
from .signature import QooSignatureEngine

logger = logging.getLogger("qoocode-lsp")


class QooLspServer:
    """qoocode Language Server for robot skill development."""

    def __init__(self):
        self.server = LanguageServer("qoocode-lsp", "0.3.0")

        self.completion_engine = QooCompletionEngine()
        self.hover_engine = QooHoverEngine()
        self.definition_engine = QooDefinitionEngine()
        self.diagnostic_engine = QooDiagnosticEngine(self.server)
        self.symbol_engine = QooSymbolEngine()
        self.signature_engine = QooSignatureEngine()

        self._register_handlers()

    def _register_handlers(self):
        """Register all LSP request/notification handlers."""

        @self.server.feature(INITIALIZED)
        def on_initialized(ls: LanguageServer, params: InitializedParams):
            logger.info("qoocode LSP server initialized")

        @self.server.feature(
            TEXT_DOCUMENT_COMPLETION,
            CompletionOptions(trigger_characters=[".", "(", '"'])
        )
        def on_completion(ls: LanguageServer, params: CompletionParams) -> Optional[CompletionList]:
            return self.completion_engine.complete(ls, params)

        @self.server.feature(TEXT_DOCUMENT_HOVER)
        def on_hover(ls: LanguageServer, params: HoverParams) -> Optional[Hover]:
            return self.hover_engine.hover(ls, params)

        @self.server.feature(TEXT_DOCUMENT_DEFINITION)
        def on_definition(ls: LanguageServer, params: DefinitionParams) -> Optional[list[Location]]:
            return self.definition_engine.go_to_definition(ls, params)

        @self.server.feature(TEXT_DOCUMENT_REFERENCES)
        def on_references(ls: LanguageServer, params: ReferenceParams) -> Optional[list[Location]]:
            return self.definition_engine.find_references(ls, params)

        @self.server.feature(TEXT_DOCUMENT_DOCUMENT_SYMBOL)
        def on_document_symbol(ls: LanguageServer, params: DocumentSymbolParams) -> Optional[list[DocumentSymbol]]:
            return self.symbol_engine.get_symbols(ls, params)

        @self.server.feature(TEXT_DOCUMENT_SIGNATURE_HELP)
        def on_signature_help(ls: LanguageServer, params: SignatureHelpParams) -> Optional[SignatureHelp]:
            return self.signature_engine.get_signature_help(ls, params)

        @self.server.feature(TEXT_DOCUMENT_DID_OPEN)
        def on_did_open(ls: LanguageServer, params):
            self.diagnostic_engine.check_document(ls, params.text_document.uri)

        @self.server.feature(TEXT_DOCUMENT_DID_CHANGE)
        def on_did_change(ls: LanguageServer, params):
            self.diagnostic_engine.check_document(ls, params.text_document.uri)

        @self.server.feature(TEXT_DOCUMENT_DID_SAVE)
        def on_did_save(ls: LanguageServer, params):
            self.diagnostic_engine.check_document(ls, params.text_document.uri)

    def start_stdio(self):
        """Start LSP server over stdio."""
        self.server.start_io()

    def start_tcp(self, host: str, port: int):
        """Start LSP server over TCP."""
        self.server.start_tcp(host, port)
