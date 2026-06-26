"""qoo doctor - Environment diagnostic command."""

from __future__ import annotations

import shutil
import sys
from importlib.metadata import version as pkg_version

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Diagnose development environment", rich_markup_mode="rich")
console = Console()

# Tools to check
REQUIRED_TOOLS = {
    "python": {"min_version": "3.11", "check": lambda: sys.version_info >= (3, 11)},
    "pip": {"check": lambda: shutil.which("pip") is not None},
    "git": {"check": lambda: shutil.which("git") is not None},
    "cmake": {"check": lambda: shutil.which("cmake") is not None},
    "docker": {"check": lambda: shutil.which("docker") is not None},
}

OPTIONAL_TOOLS = {
    "mujoco": {"check": lambda: shutil.which("simulate") is not None},
    "isaac_sim": {"check": lambda: False},  # TODO: proper check
    "gazebo": {"check": lambda: shutil.which("gz") is not None or shutil.which("ign") is not None},
    "ros2": {"check": lambda: shutil.which("ros2") is not None},
}


@app.callback()
def callback():
    """Check your development environment for QooBot development."""


@app.command()
def doctor():
    """Run environment diagnostics.

    Checks for required and optional tools needed for QooBot development.
    """
    console.print(
        Panel.fit(
            "[bold]QooCode Environment Doctor[/bold]\n"
            "Checking your development environment...",
            border_style="cyan",
        )
    )

    # Required tools
    req_table = Table(title="Required Tools", show_header=True)
    req_table.add_column("Tool", style="cyan")
    req_table.add_column("Status", style="bold")
    req_table.add_column("Details")

    all_ok = True
    for name, info in REQUIRED_TOOLS.items():
        ok = info["check"]()
        if ok:
            if name == "python":
                detail = f"v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            else:
                detail = shutil.which(name) or "found"
            req_table.add_row(name, "[green]✓ Found[/green]", detail)
        else:
            all_ok = False
            min_ver = info.get("min_version", "")
            req_table.add_row(
                name, "[red]✗ Missing[/red]",
                f"Required: {min_ver}" if min_ver else "Not found in PATH"
            )

    console.print(req_table)

    # Optional tools
    opt_table = Table(title="Optional Tools", show_header=True)
    opt_table.add_column("Tool", style="cyan")
    opt_table.add_column("Status", style="bold")
    opt_table.add_column("Details")

    for name, info in OPTIONAL_TOOLS.items():
        ok = info["check"]()
        if ok:
            opt_table.add_row(name, "[green]✓ Found[/green]", "")
        else:
            opt_table.add_row(name, "[dim]Not found[/dim]", "Optional - for simulation")

    console.print(opt_table)

    if not all_ok:
        console.print("\n[yellow]⚠[/yellow] Some required tools are missing.")
        console.print("Please install the missing tools and try again.")
    else:
        console.print("\n[green]✓[/green] All required tools are available!")
        console.print("[bold]You're ready to develop QooBot skills![/bold]")
