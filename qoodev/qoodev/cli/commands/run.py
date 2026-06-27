"""qoo run - Run command."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(help="Run the project in simulation", rich_markup_mode="rich")
console = Console()


@app.callback()
def callback():
    """Run QooBot project."""


@app.command()
def run(
    sim: str = typer.Option(
        "mujoco", "--sim", "-s", help="Simulation backend: mujoco, isaac, gazebo"
    ),
    scene: str = typer.Option(
        "default", "--scene", help="Scene to load"
    ),
    headless: bool = typer.Option(
        False, "--headless", help="Run without GUI (headless mode)"
    ),
):
    """Run the current project in simulation."""
    from qoodev.cli.context import ProjectContext

    ctx = ProjectContext.from_cwd()
    if not ctx:
        console.print("[red]Error:[/red] Not in a QooBot project directory.")
        console.print("Run [bold]qoo init <name>[/bold] to create a project first.")
        raise typer.Exit(code=1)

    console.print(f"[bold]Running[/bold] [cyan]{ctx.name}[/cyan] in simulation...")
    console.print(f"  Backend: [yellow]{sim}[/yellow]")
    console.print(f"  Scene: [yellow]{scene}[/yellow]")
    console.print(f"  Mode: {'[dim]headless[/dim]' if headless else '[green]GUI[/green]'}")

    # TODO: Implement actual run logic
    console.print("[yellow]⚠[/yellow] Simulation runtime not yet implemented.")
