"""
brain_ai/cli.py — Command-line entry point for brain_ai.

Usage:
    brain-ai serve        Start gRPC + WebSocket servers
    brain-ai parse <text> Parse NL instruction
    brain-ai version      Print version
"""

from __future__ import annotations

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger("brain_ai.cli")


def main():
    """Main CLI entry point."""
    args = sys.argv[1:] if len(sys.argv) > 1 else ["serve"]

    if not args:
        print("Usage: brain-ai [serve|parse|version]")
        sys.exit(1)

    cmd = args[0]

    if cmd == "serve":
        _cmd_serve(args[1:])
    elif cmd == "parse":
        _cmd_parse(args[1:])
    elif cmd == "version":
        from brain_ai import __version__
        print(f"brain_ai v{__version__}")
    else:
        print(f"Unknown command: {cmd}")
        print("Available: serve, parse, version")
        sys.exit(1)


def _cmd_serve(args: list[str]) -> None:
    """Start all brain_ai servers."""
    import asyncio
    from brain_ai.grpc_server.server import serve_async

    print("╔══════════════════════════════════════════╗")
    print("║   Brain OS AI Engine v0.1.0              ║")
    print("║   gRPC + WebSocket Server                ║")
    print("╚══════════════════════════════════════════╝")

    grpc_address = "0.0.0.0:50052"
    logger.info(f"[brain_ai] Starting gRPC server on {grpc_address}")
    logger.info("[brain_ai] Starting WebSocket server on 0.0.0.0:8765")
    logger.info("[brain_ai] Services: Cognition | Decision | Knowledge")
    logger.info("[brain_ai] Ctrl+C to stop")

    asyncio.run(serve_async(grpc_address))


def _cmd_parse(args: list[str]) -> None:
    """Parse a natural language instruction."""
    if not args:
        print("Usage: brain-ai parse <instruction>")
        sys.exit(1)

    instruction = " ".join(args)
    from brain_ai.llm_agent.intent_parser import IntentParser

    parser = IntentParser()
    intent = parser.parse(instruction)
    print(f"Instruction: {instruction}")
    print(f"Intent: {intent.model_dump_json(indent=2)}")


if __name__ == "__main__":
    main()
