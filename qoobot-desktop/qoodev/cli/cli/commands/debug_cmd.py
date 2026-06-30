"""qoo debug CLI — 远程调试命令

通过 WebSocket 协议连接到运行中的 DebugServer，
支持断点管理、步进控制、变量检查、调用栈追踪。
"""

from __future__ import annotations

import json
import asyncio
import signal
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text

app = typer.Typer(name="debug", help="Remote debugging for skills")
console = Console()


# ── WebSocket 调试客户端 ──────────────────────────────────


class _DebugClient:
    """通过 WebSocket 与 DebugServer 通信的轻量客户端。"""

    def __init__(self, host: str = "localhost", port: int = 5678):
        self.host = host
        self.port = port
        self._req_id = 0
        self._ws: Optional[object] = None

    async def connect(self) -> bool:
        try:
            import websockets
            self._ws = await asyncio.wait_for(
                websockets.connect(f"ws://{self.host}:{self.port}"),
                timeout=5.0,
            )
            return True
        except ImportError:
            console.print("[red]Error:[/red] websockets not installed.")
            console.print("Install with: [bold]pip install websockets[/bold]")
            return False
        except asyncio.TimeoutError:
            return False
        except OSError as e:
            console.print(f"[red]Connection failed:[/red] {e}")
            return False

    async def send(self, command: str, arguments: Optional[dict] = None) -> dict:
        if self._ws is None:
            return {"error": "Not connected"}
        self._req_id += 1
        msg = {"command": command, "arguments": arguments or {}, "request_id": self._req_id}
        import websockets
        await self._ws.send(json.dumps(msg))
        raw = await asyncio.wait_for(self._ws.recv(), timeout=10.0)
        return json.loads(raw)

    async def close(self):
        if self._ws:
            import websockets
            await self._ws.close()
            self._ws = None


def _with_client(host: str, port: int):
    """装饰器：注入已连接的 _DebugClient。"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            client = _DebugClient(host, port)
            if not await client.connect():
                console.print(f"[red]Cannot connect to debug server at {host}:{port}[/red]")
                console.print("Make sure the debug server is running:")
                console.print("  [bold]qoo debug server[/bold]")
                raise typer.Exit(code=1)
            try:
                await func(client, *args, **kwargs)
            finally:
                await client.close()
        return wrapper
    return decorator


# ── 命令 ──────────────────────────────────────────────────


@app.command("server")
def start_server(
    host: str = typer.Option("localhost", "--host", "-h", help="Listen host"),
    port: int = typer.Option(5678, "--port", "-p", help="Listen port"),
):
    """Start debug server in current process.

    The server listens for WebSocket connections from IDE plugins
    and the qoo debug CLI. Attach it to a running skill process to
    enable interactive debugging.
    """
    from cli.debugger import DebugServer

    server = DebugServer(host=host, port=port)

    async def _run():
        await server.start()
        console.print(
            Panel.fit(
                f"[green]✓ Debug server started[/green]\n"
                f"Listening on: [bold]ws://{host}:{port}[/bold]\n\n"
                f"Connect with:\n"
                f"  qoo debug attach --host {host} --port {port}\n"
                f"  qoo debug backtrace --host {host} --port {port}",
                title="[bold]Debug Server[/bold]",
                border_style="green",
            )
        )
        # Keep running until interrupted
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹ Stopping debug server...[/yellow]")


@app.command("attach")
def attach(
    host: str = typer.Option("localhost", "--host", "-h", help="Debug server host"),
    port: int = typer.Option(5678, "--port", "-p", help="Debug server port"),
):
    """Attach to a running debug server and enter interactive mode.

    Interactive commands:
      bp set <file> <line>  - Set a breakpoint
      bp list               - List all breakpoints
      bp remove <id>        - Remove a breakpoint
      bt / backtrace        - Show call stack
      vars / locals         - Show local variables
      step / next / s       - Step over
      si / step_into        - Step into
      finish / so           - Step out
      c / continue          - Continue execution
      eval <expr>           - Evaluate expression
      state                 - Show debugger state
      q / quit              - Detach and quit
    """

    async def _interactive(client: _DebugClient):
        resp = await client.send("attach")
        console.print("[green]🐛 Attached to debug server[/green]")

        # Display initial state
        await _show_state(client)

        console.print("\n[dim]Type 'help' for commands, 'q' to quit[/dim]\n")

        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("(qoo-dbg) ")
                )
            except (EOFError, KeyboardInterrupt):
                break

            if not line:
                continue
            parts = line.strip().split()
            cmd = parts[0].lower()

            if cmd in ("q", "quit", "exit"):
                break
            elif cmd == "help":
                _print_help()
            elif cmd == "bp":
                if len(parts) < 2:
                    console.print("[yellow]Usage: bp <set|list|remove> ...[/yellow]")
                elif parts[1] == "set" and len(parts) >= 4:
                    resp = await client.send("set_breakpoint", {
                        "file": parts[2], "line": int(parts[3]),
                    })
                    if resp.get("status") == "ok":
                        console.print(f"[green]🔴 Breakpoint set: {parts[2]}:{parts[3]}[/green]")
                    else:
                        console.print(f"[red]{resp.get('error')}[/red]")
                elif parts[1] == "list":
                    resp = await client.send("list_breakpoints")
                    if resp.get("status") == "ok":
                        bps = resp.get("breakpoints", [])
                        if bps:
                            table = Table(title="Breakpoints")
                            table.add_column("ID", style="cyan")
                            table.add_column("Location", style="white")
                            table.add_column("Hits", justify="right")
                            table.add_column("Cond", style="yellow")
                            for bp in bps:
                                table.add_row(
                                    bp["id"],
                                    f"{bp['file']}:{bp['line']}",
                                    str(bp["hit_count"]),
                                    bp.get("condition", ""),
                                )
                            console.print(table)
                        else:
                            console.print("[dim]No breakpoints set[/dim]")
                elif parts[1] == "remove" and len(parts) >= 3:
                    resp = await client.send("remove_breakpoint", {"breakpoint_id": parts[2]})
                    console.print(f"[green]✅ Removed: {parts[2]}[/green]")
            elif cmd in ("bt", "backtrace"):
                await _show_backtrace(client)
            elif cmd in ("vars", "locals"):
                resp = await client.send("variables", {"scope": "locals"})
                await _show_variables(resp)
            elif cmd in ("step", "next", "s"):
                resp = await client.send("step_over")
                console.print("[cyan]→ Step over[/cyan]")
                await _show_state(client)
            elif cmd in ("si", "step_into"):
                resp = await client.send("step_into")
                console.print("[cyan]↓ Step into[/cyan]")
                await _show_state(client)
            elif cmd in ("finish", "so"):
                resp = await client.send("step_out")
                console.print("[cyan]↑ Step out[/cyan]")
                await _show_state(client)
            elif cmd in ("c", "continue"):
                resp = await client.send("continue")
                console.print("[green]▶ Continue[/green]")
            elif cmd == "state":
                await _show_state(client)
            elif cmd == "eval" and len(parts) >= 2:
                expr = " ".join(parts[1:])
                resp = await client.send("evaluate", {"expression": expr})
                result = resp.get("result", resp.get("error", "?"))
                console.print(f"[yellow]{result}[/yellow]")
            else:
                console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
                console.print("[dim]Type 'help' for available commands[/dim]")

        # Detach
        await client.send("detach")
        console.print("[yellow]👋 Detached from debug server[/yellow]")

    async def _run():
        await _with_client(host, port)(_interactive)()

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise
    except Exception:
        pass


@app.command("backtrace")
def backtrace(
    host: str = typer.Option("localhost", "--host", "-h", help="Debug server host"),
    port: int = typer.Option(5678, "--port", "-p", help="Debug server port"),
    max_frames: int = typer.Option(50, "--max-frames", "-n", help="Max stack frames"),
):
    """Get call stack from debug server."""

    async def _run():
        client = _DebugClient(host, port)
        if not await client.connect():
            console.print(f"[red]Cannot connect to debug server at {host}:{port}[/red]")
            raise typer.Exit(code=1)
        try:
            await _show_backtrace(client, max_frames)
        finally:
            await client.close()

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise


@app.command("breakpoint")
def manage_breakpoint(
    action: str = typer.Argument(..., help="Action: set, list, remove"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Source file"),
    line: Optional[int] = typer.Option(None, "--line", "-l", help="Line number"),
    condition: Optional[str] = typer.Option(None, "--condition", "-c", help="Condition expression"),
    bp_id: Optional[str] = typer.Option(None, "--id", help="Breakpoint ID"),
    host: str = typer.Option("localhost", "--host", "-h", help="Debug server host"),
    port: int = typer.Option(5678, "--port", "-p", help="Debug server port"),
):
    """Manage breakpoints on a remote debug server.

    Examples:
        qoo debug breakpoint set -f skill.py -l 42
        qoo debug breakpoint set -f skill.py -l 42 -c "x > 10"
        qoo debug breakpoint list
        qoo debug breakpoint remove --id bp:skill.py:42
    """

    async def _run():
        client = _DebugClient(host, port)
        if not await client.connect():
            console.print(f"[red]Cannot connect to debug server at {host}:{port}[/red]")
            raise typer.Exit(code=1)

        try:
            if action == "set":
                if not file or not line:
                    console.print("[red]❌ --file and --line required for 'set'[/red]")
                    raise typer.Exit(code=1)
                resp = await client.send("set_breakpoint", {
                    "file": file,
                    "line": line,
                    "condition": condition,
                })
                if resp.get("status") == "ok":
                    console.print(f"[green]🔴 Breakpoint set: {file}:{line}[/green]")
                    if condition:
                        console.print(f"   Condition: [yellow]{condition}[/yellow]")
                    console.print(f"   ID: [cyan]{resp.get('breakpoint_id')}[/cyan]")
                else:
                    console.print(f"[red]Error: {resp.get('error', 'unknown')}[/red]")
                    raise typer.Exit(code=1)

            elif action == "list":
                resp = await client.send("list_breakpoints")
                if resp.get("status") == "ok":
                    bps = resp.get("breakpoints", [])
                    if not bps:
                        console.print("[dim]No breakpoints set[/dim]")
                    else:
                        table = Table(title="Breakpoints")
                        table.add_column("ID", style="cyan")
                        table.add_column("Location", style="white")
                        table.add_column("Hits", justify="right")
                        table.add_column("Cond", style="yellow")
                        table.add_column("Enabled", justify="center")
                        for bp in bps:
                            table.add_row(
                                bp["id"],
                                f"{bp['file']}:{bp['line']}",
                                str(bp.get("hit_count", 0)),
                                bp.get("condition", ""),
                                "✓" if bp.get("enabled", True) else "✗",
                            )
                        console.print(table)
                else:
                    console.print(f"[red]Error: {resp.get('error', 'unknown')}[/red]")
                    raise typer.Exit(code=1)

            elif action == "remove":
                if not bp_id:
                    console.print("[red]❌ --id required for 'remove'[/red]")
                    raise typer.Exit(code=1)
                resp = await client.send("remove_breakpoint", {"breakpoint_id": bp_id})
                if resp.get("status") == "ok":
                    console.print(f"[green]✅ Removed breakpoint: {bp_id}[/green]")
                else:
                    console.print(f"[red]Error: {resp.get('error', 'unknown')}[/red]")
                    raise typer.Exit(code=1)

            else:
                console.print(f"[red]Unknown action: {action}[/red]")
                console.print("Available: set, list, remove")
                raise typer.Exit(code=1)

        finally:
            await client.close()

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise


@app.command("variables")
def variables(
    host: str = typer.Option("localhost", "--host", "-h", help="Debug server host"),
    port: int = typer.Option(5678, "--port", "-p", help="Debug server port"),
    scope: str = typer.Option("locals", "--scope", "-s", help="Scope: locals, globals"),
):
    """Show local variables from debug server."""

    async def _run():
        client = _DebugClient(host, port)
        if not await client.connect():
            console.print(f"[red]Cannot connect to debug server at {host}:{port}[/red]")
            raise typer.Exit(code=1)
        try:
            resp = await client.send("variables", {"scope": scope})
            await _show_variables(resp)
        finally:
            await client.close()

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise


@app.command("eval")
def eval_expr(
    expression: str = typer.Argument(..., help="Python expression to evaluate"),
    host: str = typer.Option("localhost", "--host", "-h", help="Debug server host"),
    port: int = typer.Option(5678, "--port", "-p", help="Debug server port"),
):
    """Evaluate a Python expression in the debugged process."""

    async def _run():
        client = _DebugClient(host, port)
        if not await client.connect():
            console.print(f"[red]Cannot connect to debug server at {host}:{port}[/red]")
            raise typer.Exit(code=1)
        try:
            resp = await client.send("evaluate", {"expression": expression})
            result = resp.get("result", resp.get("error", "No result"))
            console.print(f"[yellow]{result}[/yellow]")
        finally:
            await client.close()

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise


@app.command("state")
def debug_state(
    host: str = typer.Option("localhost", "--host", "-h", help="Debug server host"),
    port: int = typer.Option(5678, "--port", "-p", help="Debug server port"),
):
    """Show debugger state from remote server."""

    async def _run():
        client = _DebugClient(host, port)
        if not await client.connect():
            console.print(f"[red]Cannot connect to debug server at {host}:{port}[/red]")
            raise typer.Exit(code=1)
        try:
            await _show_state(client)
        finally:
            await client.close()

    try:
        asyncio.run(_run())
    except typer.Exit:
        raise


# ── 辅助函数 ──────────────────────────────────────────────


async def _show_state(client: _DebugClient):
    """显示调试器状态"""
    resp = await client.send("state")
    if resp.get("status") != "ok":
        console.print(f"[red]{resp.get('error', 'unknown')}[/red]")
        return

    state = resp.get("state", {})
    running = "✓" if state.get("running") else "✗"
    paused = "⏸" if state.get("paused") else "▶"
    loc = state.get("location")

    lines = [
        f"Running: [green]{running}[/green]  Paused: [yellow]{paused}[/yellow]",
    ]
    if loc:
        lines.append(f"Location: [cyan]{loc['file']}:{loc['line']}[/cyan] in [bold]{loc['function']}[/bold]")
        if loc.get("source"):
            lines.append("")
            lines.append(Syntax(loc["source"], "python", theme="monokai", line_numbers=False))

    console.print(Panel.fit(
        "\n".join(str(l) for l in lines),
        title="[bold]Debugger State[/bold]",
        border_style="blue",
    ))


async def _show_backtrace(client: _DebugClient, max_frames: int = 50):
    """显示调用栈"""
    resp = await client.send("stack_trace", {"max_frames": max_frames})
    if resp.get("status") != "ok":
        console.print(f"[red]{resp.get('error', 'unknown')}[/red]")
        return

    frames = resp.get("frames", [])
    if not frames:
        console.print("[dim]No stack frames available[/dim]")
        return

    table = Table(title="Call Stack")
    table.add_column("#", style="dim", width=4)
    table.add_column("Function", style="cyan")
    table.add_column("Location", style="white")
    table.add_column("Source", style="green")

    for f in frames:
        loc = f.get("location", {})
        table.add_row(
            str(f.get("index", "")),
            loc.get("function", "?"),
            f"{loc.get('file', '?')}:{loc.get('line', '?')}",
            (loc.get("source", "") or "")[:80],
        )

    console.print(table)


async def _show_variables(resp: dict):
    """显示变量"""
    if resp.get("status") != "ok":
        console.print(f"[red]{resp.get('error', 'unknown')}[/red]")
        return

    vars_data = resp.get("variables", {})
    if not vars_data:
        console.print("[dim]No variables[/dim]")
        return

    table = Table(title="Variables")
    table.add_column("Name", style="cyan")
    table.add_column("Value", style="white")

    for name, value in sorted(vars_data.items()):
        table.add_row(name, str(value)[:120])

    console.print(table)


def _print_help():
    """打印交互式帮助"""
    help_text = """
[bold cyan]qoo debug[/bold cyan] — Interactive Debug Commands

[bold]Execution Control:[/bold]
  [yellow]step / s[/yellow]         Step over current line
  [yellow]si[/yellow]               Step into function call
  [yellow]finish / so[/yellow]      Step out of current function
  [yellow]c / continue[/yellow]     Continue execution

[bold]Breakpoints:[/bold]
  [yellow]bp set <file> <line>[/yellow]          Set breakpoint
  [yellow]bp set <file> <line> -c "x>10"[/yellow]  Conditional breakpoint
  [yellow]bp list[/yellow]                        List all breakpoints
  [yellow]bp remove <id>[/yellow]                 Remove breakpoint

[bold]Inspection:[/bold]
  [yellow]bt / backtrace[/yellow]   Show call stack
  [yellow]vars / locals[/yellow]    Show local variables
  [yellow]eval <expr>[/yellow]      Evaluate Python expression
  [yellow]state[/yellow]            Show debugger state

[bold]Session:[/bold]
  [yellow]q / quit[/yellow]         Detach and exit
  [yellow]help[/yellow]             Show this help
"""
    console.print(help_text)
