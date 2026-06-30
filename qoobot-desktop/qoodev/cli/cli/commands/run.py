"""qoo run - Run command.

Launches QooBot projects in simulation or on real hardware,
supporting MuJoCo, Isaac Sim, and Gazebo backends.
"""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Run the project in simulation", rich_markup_mode="rich")
console = Console()

# Graceful shutdown flag
_shutdown_requested = False


@app.callback()
def callback():
    """Run QooBot project."""


@app.command()
def run(
    sim: str = typer.Option(
        "mujoco", "--sim", "-s", help="Simulation backend: mujoco, isaac, gazebo"
    ),
    scene: str = typer.Option(
        "default", "--scene", help="Scene to load: home, factory, warehouse, hospital, default"
    ),
    headless: bool = typer.Option(
        False, "--headless", help="Run without GUI (headless mode)"
    ),
    duration: float = typer.Option(
        0.0, "--duration", "-d", help="Run duration in seconds (0 = run until interrupted)"
    ),
    real_time: bool = typer.Option(
        True, "--real-time/--no-real-time", help="Run in real-time vs as-fast-as-possible"
    ),
    record: bool = typer.Option(
        False, "--record", "-r", help="Record sensor and control data"
    ),
    output: str = typer.Option(
        "", "--output", "-o", help="Output file for recording (.qoodata)"
    ),
):
    """Run the current project in simulation.

    Launches the simulation backend, loads the specified scene,
    and executes the project's main skill or service.
    """
    from qoodev.cli.context import ProjectContext

    ctx = ProjectContext.from_cwd()
    if not ctx:
        console.print("[red]Error:[/red] Not in a QooBot project directory.")
        console.print("Run [bold]qoo init <name>[/bold] to create a project first.")
        raise typer.Exit(code=1)

    # ── Validate backend ──
    valid_backends = {"mujoco", "isaac", "isaac_sim", "gazebo"}
    sim_normalized = "isaac_sim" if sim in ("isaac", "isaac_sim") else sim
    if sim_normalized not in valid_backends and sim not in valid_backends:
        console.print(f"[red]Error:[/red] Unknown backend '{sim}'.")
        console.print(f"  Valid backends: {', '.join(sorted(valid_backends))}")
        raise typer.Exit(code=1)

    # ── Show startup info ──
    console.print(
        Panel.fit(
            f"[bold cyan]{ctx.name}[/bold cyan]  v{ctx.version}  [{ctx.project_type}]",
            title="Run",
            border_style="blue",
        )
    )
    console.print(f"  Backend: [yellow]{sim_normalized}[/yellow]")
    console.print(f"  Scene:   [yellow]{scene}[/yellow]")
    console.print(f"  Mode:    {'[dim]headless[/dim]' if headless else '[green]GUI[/green]'}")
    console.print(f"  Timing:  {'[green]real-time[/green]' if real_time else '[yellow]as-fast-as-possible[/yellow]'}")
    if duration > 0:
        console.print(f"  Duration: [cyan]{duration}s[/cyan]")
    if record:
        out_file = output or f"{ctx.name}_{time.strftime('%Y%m%d_%H%M%S')}.qoodata"
        console.print(f"  Recording: [magenta]{out_file}[/magenta]")
    console.print()

    # ── Initialize simulation ──
    try:
        manager = _init_simulation(ctx, sim_normalized, scene, headless, real_time)
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to initialize simulation: {e}")
        raise typer.Exit(code=1)

    # ── Initialize data recorder ──
    recorder = None
    if record:
        try:
            recorder = _init_recorder(ctx, out_file or f"{ctx.name}_{time.strftime('%Y%m%d_%H%M%S')}.qoodata")
        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Recording unavailable: {e}")

    # ── Setup graceful shutdown ──
    global _shutdown_requested
    _shutdown_requested = False

    def _signal_handler(signum, frame):
        global _shutdown_requested
        _shutdown_requested = True
        console.print("\n[yellow]Shutdown requested...[/yellow]")

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # ── Run simulation loop ──
    run_start = time.perf_counter()
    step_count = 0

    console.print("[green]▶[/green] Simulation started. Press [bold]Ctrl+C[/bold] to stop.")
    console.print()

    try:
        manager.start()

        with Live(_make_status_table(manager, step_count, run_start), console=console, refresh_per_second=4) as live:
            while not _shutdown_requested:
                time.sleep(0.25)  # 4 Hz UI refresh
                step_count = manager.backend.stats.total_steps if manager.backend else 0

                # Check duration
                elapsed = time.perf_counter() - run_start
                if duration > 0 and elapsed >= duration:
                    break

                live.update(_make_status_table(manager, step_count, run_start))

    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
        if recorder:
            try:
                recorder.close()
                console.print(f"[green]✓[/green] Recording saved: {recorder.output_path}")
            except Exception:
                pass

    # ── Final report ──
    elapsed = time.perf_counter() - run_start
    console.print()
    console.print(
        Panel.fit(
            f"  Elapsed:   [bold]{elapsed:.1f}s[/bold]\n"
            f"  Steps:     [bold]{step_count}[/bold]\n"
            f"  Avg FPS:   [bold]{step_count / elapsed:.1f}[/bold]" if elapsed > 0 else "  No steps executed",
            title="Run Summary",
            border_style="green",
        )
    )

    manager.shutdown()


# ── Internal helpers ───────────────────────────────────────────


def _init_simulation(ctx, backend: str, scene: str, headless: bool, real_time: bool):
    """Initialize the simulation backend and load the scene."""
    from qoodev.sim_bridge.interface import SimConfig, SimScene
    from qoodev.sim_bridge.manager import SimManager, register_backend
    from qoodev.sim_bridge.muJoCo_backend import MuJoCoBackend

    # Register available backends
    register_backend("mujoco", MuJoCoBackend)
    try:
        from qoodev.sim_bridge.isaac_sim_backend import IsaacSimBackend
        register_backend("isaac_sim", IsaacSimBackend)
    except ImportError:
        pass

    # Create config
    config = SimConfig(
        backend=backend,
        headless=headless,
        real_time=real_time,
        time_step=0.001,
        enable_profiling=True,
    )

    # Create scene
    scene_obj = _load_scene(scene)

    # Initialize manager
    manager = SimManager(config)
    manager.initialize()
    manager.load_scene(scene_obj)

    return manager


def _load_scene(scene_name: str):
    """Load a named scene or create a default one."""
    from qoodev.sim_bridge.interface import SimScene, SimRobot, ControlMode

    # Try to load from scene loader
    try:
        from qoodev.sim_bridge.scene_loader import SceneLoader
        loader = SceneLoader()
        return loader.load(scene_name)
    except Exception:
        pass

    # Fallback: create default scene
    scene = SimScene(
        name=scene_name,
        description=f"Default {scene_name} scene",
        robots=[
            SimRobot(
                name="qoobot",
                model_path=f"scenes/{scene_name}/qoobot.xml",
                base_position=(0.0, 0.0, 0.0),
                control_mode=ControlMode.POSITION,
            )
        ],
    )
    return scene


def _init_recorder(ctx, output_path: str):
    """Initialize the data recorder."""
    from qoodev.data_recorder import DataRecorder

    out = Path(output_path)
    if not out.is_absolute():
        out = ctx.root / out
    recorder = DataRecorder(str(out))
    recorder.start()
    return recorder


def _make_status_table(manager, step_count: int, run_start: float) -> Table:
    """Create a live status table for the simulation."""
    from qoodev.sim_bridge.interface import SimState

    elapsed = time.perf_counter() - run_start
    state = manager.state if manager else SimState.UNINITIALIZED

    state_color = {
        SimState.RUNNING: "green",
        SimState.PAUSED: "yellow",
        SimState.READY: "cyan",
        SimState.LOADING: "blue",
        SimState.ERROR: "red",
        SimState.STOPPED: "dim",
        SimState.UNINITIALIZED: "dim",
    }.get(state, "white")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Status", f"[{state_color}]{state.name}[/{state_color}]")
    table.add_row("Elapsed", f"{elapsed:.1f}s")
    table.add_row("Steps", str(step_count))
    if elapsed > 0:
        table.add_row("Sim FPS", f"{step_count / elapsed:.1f}")

    # Add stats if available
    if manager.backend:
        try:
            stats = manager.backend.get_stats()
            if stats.real_time_factor > 0:
                table.add_row("RT Factor", f"{stats.real_time_factor:.2f}x")
        except Exception:
            pass

    return table
