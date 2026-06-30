"""Entry point for qoodev-lsp."""

import sys
import argparse
import logging

from .server import QooLspServer


def main():
    parser = argparse.ArgumentParser(description="qoodev Language Server")
    parser.add_argument("--tcp", action="store_true", help="Use TCP transport instead of stdio")
    parser.add_argument("--host", default="127.0.0.1", help="TCP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=2087, help="TCP port (default: 2087)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            filename="qoodev-lsp.log",
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    server = QooLspServer()
    if args.tcp:
        server.start_tcp(args.host, args.port)
    else:
        server.start_stdio()


if __name__ == "__main__":
    main()
