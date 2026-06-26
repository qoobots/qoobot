"""Signature help engine — shows function signatures for qoobot-sdk APIs."""

import logging
from typing import Optional

from pygls.server import LanguageServer
from lsprotocol.types import (
    SignatureHelp,
    SignatureHelpParams,
    SignatureInformation,
    ParameterInformation,
    MarkupContent,
    MarkupKind,
)

logger = logging.getLogger("qoocode-lsp.signature")

SIGNATURES: dict[str, list[tuple[str, str, list[str]]]] = {
    "QooSkill": [
        ("QooSkill(config: SkillConfig | None = None)", "Create a new QooSkill instance.", ["config"]),
    ],
    "setup": [
        ("async def setup(self) -> None", "Initialize skill resources. Called once when skill is loaded.", []),
    ],
    "loop": [
        ("async def loop(self) -> None", "Main skill loop. Called repeatedly after setup.", []),
    ],
    "teardown": [
        ("async def teardown(self) -> None", "Clean up resources. Called when skill is unloaded.", []),
    ],
    "send_control": [
        ("async def send_control(self, cmd: JointCommand | EndEffectorTarget | GripperCommand) -> None",
         "Send a control command to the robot runtime.", ["cmd"]),
    ],
    "BrainOSClient": [
        ("BrainOSClient(host: str = 'localhost', port: int = 9090)",
         "Create a BrainOS communication client.", ["host", "port"]),
    ],
    "ROS2Bridge": [
        ("ROS2Bridge(node_name: str, namespace: str = '')",
         "Create a ROS 2 bridge instance.", ["node_name", "namespace"]),
    ],
    "subscribe": [
        ("def subscribe(self, topic: str, callback: Callable, qos: int = 10) -> None",
         "Subscribe to a ROS 2 topic.", ["topic", "callback", "qos"]),
    ],
    "publish": [
        ("async def publish(self, topic: str, msg: Any) -> None",
         "Publish a message to a ROS 2 topic.", ["topic", "msg"]),
    ],
}


class QooSignatureEngine:
    """Provides signature help for qoobot-sdk functions."""

    def get_signature_help(self, ls: LanguageServer, params: SignatureHelpParams) -> Optional[SignatureHelp]:
        doc = ls.workspace.get_text_document(params.text_document.uri)
        if doc is None:
            return None

        line = doc.lines[params.position.line] if params.position.line < len(doc.lines) else ""

        # Find the function name before the open paren
        col = min(params.position.character, len(line))
        # Find the most recent open paren
        paren_idx = line.rfind("(", 0, col)
        if paren_idx < 0:
            return None

        # Find the function name before the paren
        before_paren = line[:paren_idx].rstrip()
        parts = before_paren.split()
        if not parts:
            return None

        func_name = parts[-1]
        # Remove leading dots for method calls
        if "." in func_name:
            func_name = func_name.split(".")[-1]

        if func_name in SIGNATURES:
            signatures: list[SignatureInformation] = []
            for sig, doc_str, params in SIGNATURES[func_name]:
                param_infos = [
                    ParameterInformation(label=p) for p in params
                ]
                signatures.append(
                    SignatureInformation(
                        label=sig,
                        documentation=MarkupContent(kind=MarkupKind.Markdown, value=doc_str),
                        parameters=param_infos if param_infos else None,
                    )
                )

            if signatures:
                return SignatureHelp(signatures=signatures, active_signature=0, active_parameter=0)

        return None
