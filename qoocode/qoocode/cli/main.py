"""
QooCode CLI Entry Point.

Usage:
    qoo init <project-name>     Create a new QooBot project
    qoo build                   Build the current project
    qoo run                     Run the project in simulation
    qoo test                    Run tests
    qoo doctor                  Diagnose development environment
    qoo version                 Show version info
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from qoocode import __version__
from qoocode.cli.commands import init, build, run, test, doctor, sim

app = typer.Typer(
    name="qoo",
    help="QooCode - Developer Toolchain for QooBot Humanoid Robot",
    add_completion=True,
    rich_markup_mode="rich",
)

console = Console()


@app.callback()
def callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", help="Show version and exit", is_eager=True
    ),
):
    """QooCode CLI - Build, test, and deploy QooBot skills."""
    if version:
        _show_version()
        raise typer.Exit()


def _show_version() -> None:
    """Display version information."""
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(style="bold cyan")
    info_table.add_column(style="white")
    info_table.add_row("QooCode CLI", f"v{__version__}")
    info_table.add_row("Python", sys.version.split()[0])
    info_table.add_row("Platform", sys.platform)

    console.print(
        Panel(info_table, title="[bold]QooCode[/bold]", border_style="cyan")
    )


# Register subcommands
app.add_typer(init.app, name="init", help="Create a new QooBot project")
app.add_typer(build.app, name="build", help="Build the current project")
app.add_typer(run.app, name="run", help="Run the project in simulation")
app.add_typer(test.app, name="test", help="Run project tests")
app.add_typer(doctor.app, name="doctor", help="Diagnose development environment")
app.add_typer(sim.app, name="sim", help="Simulation environment management")


def main():
    """Entry point for console_scripts."""
    app()


if __name__ == "__main__":
    main()
