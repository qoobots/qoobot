"""
Behavior Tree Debugger — v1.6+

Real-time behavior tree debugging with:
- Node status highlighting (running/success/failure)
- Transition history tracking with timestamps
- Breakpoint pause on specific nodes
- Step-through execution (tick-by-tick)
- Variable inspection per node
- Execution statistics (tick count, avg duration, success rate)

Integrates with the existing RemoteDebugger and Dashboard WebSocket server.

Usage:
    from cli.bt_debugger import BehaviorTreeDebugger

    bt_debugger = BehaviorTreeDebugger(bt_engine)
    bt_debugger.set_breakpoint("grasp_approach")
    bt_debugger.start()
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich.layout import Layout
from rich.text import Text

console = Console()


# ============================================================================
# Data Models
# ============================================================================

class BTNodeStatus(Enum):
    """Behavior tree node execution status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    PAUSED = "paused"
    ERROR = "error"


class BTDebugMode(Enum):
    """Debug execution mode."""
    RUN = "run"           # Normal execution
    PAUSE = "pause"       # Paused at breakpoint
    STEP = "step"         # Step to next tick
    STEP_INTO = "step_into"  # Step into child node
    STEP_OVER = "step_over"  # Step over current node


@dataclass
class BTNodeInfo:
    """Runtime information about a behavior tree node."""
    id: str
    name: str
    node_type: str
    status: BTNodeStatus = BTNodeStatus.IDLE
    depth: int = 0
    parent_id: str = ""

    # Execution statistics
    tick_count: int = 0
    total_duration_ms: float = 0.0
    last_duration_ms: float = 0.0
    success_count: int = 0
    failure_count: int = 0

    # Children
    children: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / self.tick_count if self.tick_count > 0 else 0.0


@dataclass
class BTTransition:
    """A single state transition in the behavior tree."""
    timestamp: float
    node_id: str
    from_status: BTNodeStatus
    to_status: BTNodeStatus
    tick_number: int
    reason: str = ""


@dataclass
class BTBreakpoint:
    """A breakpoint on a behavior tree node."""
    node_id: str
    enabled: bool = True
    condition: str = ""  # Optional Python expression
    hit_count: int = 0
    max_hits: int = 0  # 0 = unlimited
    one_shot: bool = False

    def should_break(self, status: BTNodeStatus, variables: Dict[str, Any]) -> bool:
        """Check if breakpoint should trigger."""
        if not self.enabled:
            return False
        if self.one_shot and self.hit_count > 0:
            return False
        if self.max_hits > 0 and self.hit_count >= self.max_hits:
            return False

        # Evaluate condition if set
        if self.condition:
            try:
                if not eval(self.condition, {"__builtins__": {}}, variables):
                    return False
            except Exception:
                return False

        return True


@dataclass
class BTDebugSession:
    """A behavior tree debugging session."""
    session_id: str
    started_at: float = field(default_factory=time.time)
    mode: BTDebugMode = BTDebugMode.RUN
    nodes: Dict[str, BTNodeInfo] = field(default_factory=dict)
    transitions: List[BTTransition] = field(default_factory=list)
    breakpoints: Dict[str, BTBreakpoint] = field(default_factory=dict)
    current_tick: int = 0
    paused_node_id: str = ""
    max_history: int = 1000

    # Callbacks
    on_breakpoint_hit: Optional[Callable[[str, BTNodeInfo], None]] = None
    on_tick_complete: Optional[Callable[[int, Dict[str, BTNodeInfo]], None]] = None
    on_transition: Optional[Callable[[BTTransition], None]] = None


# ============================================================================
# Behavior Tree Debugger
# ============================================================================

class BehaviorTreeDebugger:
    """Real-time behavior tree debugger.

    Features:
    - Live tree visualization with node status colors
    - Breakpoint management (set/enable/disable/remove)
    - Step-through execution (step over / step into)
    - Transition history with timestamps
    - Per-node execution statistics
    - WebSocket integration for remote IDE debugging
    - Session recording and replay
    """

    # Status color mapping for terminal output
    _STATUS_COLORS = {
        BTNodeStatus.IDLE: "dim",
        BTNodeStatus.RUNNING: "yellow",
        BTNodeStatus.SUCCESS: "green",
        BTNodeStatus.FAILURE: "red",
        BTNodeStatus.PAUSED: "cyan",
        BTNodeStatus.ERROR: "bold red",
    }

    _STATUS_ICONS = {
        BTNodeStatus.IDLE: "○",
        BTNodeStatus.RUNNING: "▶",
        BTNodeStatus.SUCCESS: "✓",
        BTNodeStatus.FAILURE: "✗",
        BTNodeStatus.PAUSED: "⏸",
        BTNodeStatus.ERROR: "⚠",
    }

    def __init__(self, tree_name: str = "behavior_tree"):
        self.tree_name = tree_name
        self._session: Optional[BTDebugSession] = None
        self._lock = threading.Lock()
        self._step_event = threading.Event()
        self._ws_clients: List[Any] = []
        self._recorded_sessions: List[BTDebugSession] = []

    # ── Session Management ──────────────────────────────────────────────────

    def start(self) -> BTDebugSession:
        """Start a new debugging session."""
        import uuid

        session = BTDebugSession(session_id=str(uuid.uuid4())[:8])
        self._session = session
        console.print(Panel.fit(
            f"[bold cyan]BT Debugger Started[/bold cyan]\n"
            f"Tree: [yellow]{self.tree_name}[/yellow]  "
            f"Session: [dim]{session.session_id}[/dim]",
            border_style="cyan",
        ))
        return session

    def stop(self) -> None:
        """Stop the current debugging session."""
        if self._session:
            self._recorded_sessions.append(self._session)
            console.print(Panel.fit(
                f"[bold yellow]BT Debugger Stopped[/bold yellow]\n"
                f"Ticks: {self._session.current_tick}  "
                f"Transitions: {len(self._session.transitions)}",
                border_style="yellow",
            ))
        self._session = None
        self._step_event.set()  # Release any waiting step

    # ── Node Registration ──────────────────────────────────────────────────

    def register_node(
        self,
        node_id: str,
        name: str,
        node_type: str,
        parent_id: str = "",
        depth: int = 0,
    ) -> None:
        """Register a behavior tree node for tracking."""
        if not self._session:
            self.start()

        info = BTNodeInfo(
            id=node_id,
            name=name,
            node_type=node_type,
            depth=depth,
            parent_id=parent_id,
        )

        with self._lock:
            self._session.nodes[node_id] = info
            if parent_id and parent_id in self._session.nodes:
                self._session.nodes[parent_id].children.append(node_id)

    def register_tree(self, tree_root: dict) -> None:
        """Register entire tree from a JSON dict."""
        self._register_node_recursive(tree_root, "", 0)

    def _register_node_recursive(self, node: dict, parent_id: str, depth: int) -> None:
        """Recursively register nodes."""
        node_id = node.get("id", str(hash(str(node))))
        self.register_node(
            node_id=node_id,
            name=node.get("name", node_id),
            node_type=node.get("type", "action"),
            parent_id=parent_id,
            depth=depth,
        )
        for child in node.get("children", []):
            self._register_node_recursive(child, node_id, depth + 1)

    # ── Status Updates ─────────────────────────────────────────────────────

    def update_node_status(
        self,
        node_id: str,
        new_status: BTNodeStatus,
        duration_ms: float = 0.0,
        reason: str = "",
    ) -> None:
        """Update a node's execution status and record transition."""
        if not self._session:
            return

        with self._lock:
            session = self._session

            if node_id not in session.nodes:
                return

            node = session.nodes[node_id]
            old_status = node.status

            # Record transition
            transition = BTTransition(
                timestamp=time.time(),
                node_id=node_id,
                from_status=old_status,
                to_status=new_status,
                tick_number=session.current_tick,
                reason=reason,
            )
            session.transitions.append(transition)

            # Trim history
            if len(session.transitions) > session.max_history:
                session.transitions = session.transitions[-session.max_history:]

            # Update node
            node.status = new_status
            if new_status in (BTNodeStatus.SUCCESS, BTNodeStatus.FAILURE):
                node.tick_count += 1
                node.last_duration_ms = duration_ms
                node.total_duration_ms += duration_ms
                if new_status == BTNodeStatus.SUCCESS:
                    node.success_count += 1
                else:
                    node.failure_count += 1

            # Check breakpoints
            if new_status == BTNodeStatus.RUNNING:
                self._check_breakpoint(node_id, node)

            # Notify
            if session.on_transition:
                session.on_transition(transition)

            # Broadcast to WebSocket clients
            self._broadcast({
                "type": "bt_node_update",
                "node_id": node_id,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "duration_ms": duration_ms,
                "tick": session.current_tick,
            })

    def tick_complete(self) -> None:
        """Signal that a tick cycle has completed."""
        if not self._session:
            return

        with self._lock:
            self._session.current_tick += 1
            tick = self._session.current_tick

            if self._session.on_tick_complete:
                self._session.on_tick_complete(tick, dict(self._session.nodes))

    # ── Breakpoint Management ───────────────────────────────────────────────

    def set_breakpoint(
        self,
        node_id: str,
        condition: str = "",
        max_hits: int = 0,
        one_shot: bool = False,
    ) -> BTBreakpoint:
        """Set a breakpoint on a behavior tree node.

        Args:
            node_id: Node ID to break on
            condition: Optional Python expression (e.g., "tick_count > 10")
            max_hits: Max times to hit before auto-disabling (0 = unlimited)
            one_shot: Remove breakpoint after first hit

        Returns:
            The created breakpoint.
        """
        if not self._session:
            self.start()

        bp = BTBreakpoint(
            node_id=node_id,
            condition=condition,
            max_hits=max_hits,
            one_shot=one_shot,
        )

        with self._lock:
            self._session.breakpoints[node_id] = bp

        node_name = self._session.nodes.get(node_id, BTNodeInfo(id=node_id, name=node_id, node_type="")).name
        console.print(f"[green]●[/green] Breakpoint set on [bold]{node_name}[/bold] ({node_id})")
        if condition:
            console.print(f"  Condition: [dim]{condition}[/dim]")
        return bp

    def enable_breakpoint(self, node_id: str) -> bool:
        """Enable a breakpoint."""
        if self._session and node_id in self._session.breakpoints:
            self._session.breakpoints[node_id].enabled = True
            return True
        return False

    def disable_breakpoint(self, node_id: str) -> bool:
        """Disable a breakpoint without removing it."""
        if self._session and node_id in self._session.breakpoints:
            self._session.breakpoints[node_id].enabled = False
            return True
        return False

    def remove_breakpoint(self, node_id: str) -> bool:
        """Remove a breakpoint."""
        if self._session and node_id in self._session.breakpoints:
            del self._session.breakpoints[node_id]
            console.print(f"[yellow]●[/yellow] Breakpoint removed: {node_id}")
            return True
        return False

    def list_breakpoints(self) -> Table:
        """List all breakpoints."""
        table = Table(title="Breakpoints")
        table.add_column("Node ID", style="cyan")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Hits")
        table.add_column("Condition", style="dim")

        if not self._session:
            console.print("[dim]No active session[/dim]")
            return table

        for bp_id, bp in self._session.breakpoints.items():
            node = self._session.nodes.get(bp_id)
            name = node.name if node else bp_id
            status = "[green]enabled[/green]" if bp.enabled else "[dim]disabled[/dim]"
            table.add_row(bp_id, name, status, str(bp.hit_count), bp.condition or "-")

        console.print(table)
        return table

    def _check_breakpoint(self, node_id: str, node: BTNodeInfo) -> None:
        """Check and handle breakpoint hit."""
        if not self._session:
            return

        bp = self._session.breakpoints.get(node_id)
        if not bp:
            return

        variables = {
            "tick_count": node.tick_count,
            "success_count": node.success_count,
            "failure_count": node.failure_count,
            "success_rate": node.success_rate,
            "avg_duration_ms": node.avg_duration_ms,
        }

        if bp.should_break(node.status, variables):
            bp.hit_count += 1
            self._session.mode = BTDebugMode.PAUSE
            self._session.paused_node_id = node_id

            console.print(Panel(
                f"[bold yellow]⏸ Breakpoint Hit[/bold yellow]\n"
                f"Node: [cyan]{node.name}[/cyan] ({node_id})\n"
                f"Tick: {self._session.current_tick}  "
                f"Hit #{bp.hit_count}",
                border_style="yellow",
            ))

            if self._session.on_breakpoint_hit:
                self._session.on_breakpoint_hit(node_id, node)

            self._broadcast({
                "type": "bt_breakpoint_hit",
                "node_id": node_id,
                "node_name": node.name,
                "tick": self._session.current_tick,
                "hit_count": bp.hit_count,
            })

            # Wait for step command
            self._step_event.clear()
            self._step_event.wait()

            if bp.one_shot:
                self.remove_breakpoint(node_id)

    # ── Step Execution ──────────────────────────────────────────────────────

    def step_over(self) -> None:
        """Step over current node (continue to next sibling/parent)."""
        if self._session and self._session.mode == BTDebugMode.PAUSE:
            self._session.mode = BTDebugMode.STEP_OVER
            self._step_event.set()
            console.print("[cyan]→[/cyan] Step over")

    def step_into(self) -> None:
        """Step into current node's first child."""
        if self._session and self._session.mode == BTDebugMode.PAUSE:
            self._session.mode = BTDebugMode.STEP_INTO
            self._step_event.set()
            console.print("[cyan]→[/cyan] Step into")

    def continue_execution(self) -> None:
        """Continue execution until next breakpoint or completion."""
        if self._session:
            self._session.mode = BTDebugMode.RUN
            self._session.paused_node_id = ""
            self._step_event.set()
            console.print("[green]▶[/green] Continue")

    # ── Visualization ───────────────────────────────────────────────────────

    def show_tree(self) -> Tree:
        """Render the behavior tree with current node statuses."""
        if not self._session:
            console.print("[dim]No active session[/dim]")
            return Tree("No Session")

        root_tree = Tree(f"[bold]🌳 {self.tree_name}[/bold]")

        # Find root nodes (no parent)
        child_ids = set()
        for node in self._session.nodes.values():
            child_ids.update(node.children)
        root_ids = [nid for nid in self._session.nodes if nid not in child_ids]

        for root_id in root_ids:
            self._add_node_to_tree(root_tree, root_id)

        console.print(root_tree)
        return root_tree

    def _add_node_to_tree(self, tree: Tree, node_id: str) -> None:
        """Recursively add a node to the Rich tree."""
        if not self._session:
            return

        node = self._session.nodes.get(node_id)
        if not node:
            return

        icon = self._STATUS_ICONS.get(node.status, "?")
        color = self._STATUS_COLORS.get(node.status, "white")

        # Build label
        label_parts = [f"[{color}]{icon} {node.name}[/{color}]"]
        if node.node_type:
            label_parts.append(f"[dim]({node.node_type})[/dim]")
        if node.tick_count > 0:
            label_parts.append(f"[dim]×{node.tick_count}[/dim]")
        if node.last_duration_ms > 0:
            label_parts.append(f"[dim]{node.last_duration_ms:.1f}ms[/dim]")

        # Highlight paused node
        if node_id == self._session.paused_node_id:
            label_parts.insert(0, "[bold cyan]◀[/bold cyan]")

        label = " ".join(label_parts)
        branch = tree.add(label)

        for child_id in node.children:
            self._add_node_to_tree(branch, child_id)

    def show_statistics(self) -> Table:
        """Show per-node execution statistics."""
        table = Table(title="Node Execution Statistics")
        table.add_column("Node", style="cyan")
        table.add_column("Type")
        table.add_column("Ticks")
        table.add_column("Success Rate")
        table.add_column("Avg Duration")
        table.add_column("Last Duration")

        if not self._session:
            return table

        for node_id, node in sorted(self._session.nodes.items()):
            if node.tick_count == 0:
                continue
            table.add_row(
                node.name,
                node.node_type,
                str(node.tick_count),
                f"{node.success_rate:.1%}",
                f"{node.avg_duration_ms:.2f}ms",
                f"{node.last_duration_ms:.2f}ms",
            )

        console.print(table)
        return table

    def show_history(self, limit: int = 20) -> Table:
        """Show recent state transitions."""
        table = Table(title="Transition History")
        table.add_column("Tick", style="dim")
        table.add_column("Node", style="cyan")
        table.add_column("From")
        table.add_column("To")
        table.add_column("Reason", style="dim")

        if not self._session:
            return table

        transitions = self._session.transitions[-limit:]
        for t in transitions:
            node = self._session.nodes.get(t.node_id)
            node_name = node.name if node else t.node_id
            from_color = self._STATUS_COLORS.get(t.from_status, "")
            to_color = self._STATUS_COLORS.get(t.to_status, "")
            table.add_row(
                str(t.tick_number),
                node_name,
                f"[{from_color}]{t.from_status.value}[/{from_color}]",
                f"[{to_color}]{t.to_status.value}[/{to_color}]",
                t.reason or "-",
            )

        console.print(table)
        return table

    def show_live(self) -> Live:
        """Start a live-updating tree display."""
        def render() -> Panel:
            if not self._session:
                return Panel("[dim]No active session[/dim]", title="BT Debugger")

            layout = Layout()
            layout.split_column(
                Layout(self._render_tree_text(), name="tree"),
                Layout(self._render_stats_text(), name="stats"),
            )
            return Panel(layout, title=f"[bold]🌳 {self.tree_name}[/bold] — Tick {self._session.current_tick}")

        live = Live(render(), refresh_per_second=10, console=console)
        return live

    def _render_tree_text(self) -> Text:
        """Render tree as Text for live display."""
        text = Text()
        if not self._session:
            return text

        for node_id, node in self._session.nodes.items():
            indent = "  " * node.depth
            icon = self._STATUS_ICONS.get(node.status, "?")
            color = self._STATUS_COLORS.get(node.status, "white")
            text.append(f"{indent}{icon} {node.name}\n", style=color)

        return text

    def _render_stats_text(self) -> Text:
        """Render stats summary as Text."""
        text = Text()
        if not self._session:
            return text

        running = sum(1 for n in self._session.nodes.values() if n.status == BTNodeStatus.RUNNING)
        success = sum(1 for n in self._session.nodes.values() if n.status == BTNodeStatus.SUCCESS)
        failure = sum(1 for n in self._session.nodes.values() if n.status == BTNodeStatus.FAILURE)

        text.append(f"Running: {running}  ", style="yellow")
        text.append(f"Success: {success}  ", style="green")
        text.append(f"Failure: {failure}  ", style="red")
        text.append(f"BPs: {len(self._session.breakpoints)}", style="cyan")
        return text

    # ── Session Export ─────────────────────────────────────────────────────

    def export_session(self, output_path: Optional[Path] = None) -> Path:
        """Export the debugging session to a JSON file for replay."""
        if not self._session:
            raise RuntimeError("No active session to export")

        output = output_path or Path(f"bt_debug_{self._session.session_id}.json")

        data = {
            "session_id": self._session.session_id,
            "tree_name": self.tree_name,
            "started_at": self._session.started_at,
            "total_ticks": self._session.current_tick,
            "nodes": {
                nid: {
                    "id": n.id,
                    "name": n.name,
                    "type": n.node_type,
                    "depth": n.depth,
                    "parent_id": n.parent_id,
                    "children": n.children,
                    "tick_count": n.tick_count,
                    "total_duration_ms": n.total_duration_ms,
                    "success_count": n.success_count,
                    "failure_count": n.failure_count,
                }
                for nid, n in self._session.nodes.items()
            },
            "transitions": [
                {
                    "timestamp": t.timestamp,
                    "node_id": t.node_id,
                    "from": t.from_status.value,
                    "to": t.to_status.value,
                    "tick": t.tick_number,
                    "reason": t.reason,
                }
                for t in self._session.transitions
            ],
            "breakpoints": list(self._session.breakpoints.keys()),
        }

        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        console.print(f"[green]✓[/green] Session exported to: [bold]{output}[/bold]")
        return output

    def replay_session(self, session_path: Path, speed: float = 1.0) -> None:
        """Replay a previously exported session."""
        if not session_path.exists():
            raise FileNotFoundError(f"Session file not found: {session_path}")

        data = json.loads(session_path.read_text(encoding="utf-8"))

        console.print(Panel.fit(
            f"[bold cyan]Replaying Session[/bold cyan]\n"
            f"ID: [dim]{data['session_id']}[/dim]  "
            f"Ticks: {data['total_ticks']}  "
            f"Transitions: {len(data['transitions'])}  "
            f"Speed: {speed}x",
            border_style="cyan",
        ))

        # Register nodes
        self.start()
        for nid, ndata in data["nodes"].items():
            self.register_node(
                node_id=nid,
                name=ndata["name"],
                node_type=ndata["type"],
                parent_id=ndata["parent_id"],
                depth=ndata["depth"],
            )

        # Replay transitions
        prev_time = data["transitions"][0]["timestamp"] if data["transitions"] else 0
        for trans in data["transitions"]:
            # Simulate timing
            delay = (trans["timestamp"] - prev_time) / speed
            if delay > 0:
                time.sleep(min(delay, 0.1))  # Cap at 100ms
            prev_time = trans["timestamp"]

            self.update_node_status(
                node_id=trans["node_id"],
                new_status=BTNodeStatus(trans["to"]),
                reason=trans["reason"],
            )

        console.print("[green]✓[/green] Replay complete")

    # ── WebSocket Integration ───────────────────────────────────────────────

    def register_ws_client(self, client: Any) -> None:
        """Register a WebSocket client for real-time updates."""
        self._ws_clients.append(client)

    def unregister_ws_client(self, client: Any) -> None:
        """Unregister a WebSocket client."""
        if client in self._ws_clients:
            self._ws_clients.remove(client)

    def _broadcast(self, message: dict) -> None:
        """Broadcast a message to all WebSocket clients."""
        msg_json = json.dumps(message)
        dead_clients = []
        for client in self._ws_clients:
            try:
                client.send(msg_json)
            except Exception:
                dead_clients.append(client)
        for dc in dead_clients:
            self._ws_clients.remove(dc)

    # ── CLI Commands ───────────────────────────────────────────────────────

    def cli_interactive(self) -> None:
        """Start an interactive debug session (for CLI usage)."""
        self.start()
        console.print("[bold]BT Debugger Interactive Mode[/bold]")
        console.print("Commands: [cyan]step[/cyan] [cyan]step-into[/cyan] [cyan]continue[/cyan] "
                       "[cyan]tree[/cyan] [cyan]stats[/cyan] [cyan]history[/cyan] "
                       "[cyan]bp <node_id>[/cyan] [cyan]quit[/cyan]")

        while True:
            try:
                cmd = input("\n[bt-debug] > ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            if action == "quit":
                break
            elif action == "step":
                self.step_over()
            elif action == "step-into":
                self.step_into()
            elif action == "continue":
                self.continue_execution()
            elif action == "tree":
                self.show_tree()
            elif action == "stats":
                self.show_statistics()
            elif action == "history":
                self.show_history()
            elif action == "bp" and len(parts) >= 2:
                self.set_breakpoint(parts[1])
            elif action == "bp-list":
                self.list_breakpoints()
            elif action == "bp-remove" and len(parts) >= 2:
                self.remove_breakpoint(parts[1])
            elif action == "export":
                self.export_session()
            elif action == "help":
                console.print("step | step-into | continue | tree | stats | history | "
                               "bp <id> | bp-list | bp-remove <id> | export | quit")
            else:
                console.print(f"[red]Unknown command: {action}[/red] (type 'help')")

        self.stop()
