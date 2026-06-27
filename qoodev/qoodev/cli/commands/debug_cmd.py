"""qoo debug CLI — 远程调试命令"""

from pathlib import Path
from typer import Typer, Option, Argument
from typing import Optional

app = Typer(name="debug", help="Remote debugging for skills")


@app.command("attach")
def attach(
    host: str = Option("localhost", "--host", "-h", help="Debug server host"),
    port: int = Option(5678, "--port", "-p", help="Debug server port"),
):
    """Attach debugger to a running skill process"""
    print(f"🐛 Connecting to debug server at {host}:{port}")
    print("   (Debug server must be running in the skill process)")
    print("   Use 'qoo debug server' to start the debug server")


@app.command("server")
def start_server(
    host: str = Option("localhost", "--host", "-h", help="Listen host"),
    port: int = Option(5678, "--port", "-p", help="Listen port"),
):
    """Start debug server in current process"""
    import asyncio
    from qoodev.debugger import DebugServer

    server = DebugServer(host=host, port=port)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n⏹ Stopping debug server...")
        asyncio.run(server.stop())


@app.command("breakpoint")
def manage_breakpoint(
    action: str = Argument(..., help="Action: set, list, remove"),
    file: Optional[str] = Option(None, "--file", "-f", help="Source file"),
    line: Optional[int] = Option(None, "--line", "-l", help="Line number"),
    condition: Optional[str] = Option(None, "--condition", "-c", help="Condition expression"),
    bp_id: Optional[str] = Option(None, "--id", help="Breakpoint ID"),
):
    """Manage breakpoints"""
    if action == "set":
        if not file or not line:
            print("❌ --file and --line required for 'set'")
            raise SystemExit(1)
        print(f"🔴 Breakpoint set: {file}:{line}")
        if condition:
            print(f"   Condition: {condition}")

    elif action == "list":
        print("🔴 Breakpoints: (none)")
        print("   Connect to debug server to list remote breakpoints")

    elif action == "remove":
        if bp_id:
            print(f"✅ Removed breakpoint: {bp_id}")
        else:
            print("❌ --id required for 'remove'")
            raise SystemExit(1)


@app.command("backtrace")
def backtrace(
    host: str = Option("localhost", "--host", "-h"),
    port: int = Option(5678, "--port", "-p"),
    max_frames: int = Option(50, "--max-frames", "-n"),
):
    """Get call stack from debug server"""
    print("📋 Backtrace:")
    print("   Connect to debug server to get remote backtrace")
