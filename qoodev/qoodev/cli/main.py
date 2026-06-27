"""
qoodev CLI Entry Point.

Usage:
    qoo init <project-name>     Create a new QooBot project
    qoo build                   Build the current project
    qoo run                     Run the project in simulation
    qoo test                    Run tests
    qoo doctor                  Diagnose development environment
    qoo sim                     Simulation management
    qoo package                 Package and distribute skills
    qoo record                  Record and replay data
    qoo debug                   Remote debugging
    qoo ci                      CI/CD integration
    qoo eco                     QooEco marketplace
    qoo docs                    Generate documentation
    qoo profile                 Performance profiling and analysis
    qoo compile                 Model compilation and cross-compilation
    qoo annotate                Data annotation and labeling tools
    qoo version                 Show version info
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from qoodev import __version__
from qoodev.cli.commands import init, build, run, test, doctor, sim
from qoodev.cli.commands import package_cmd, record_cmd, debug_cmd, ci_cmd
from qoodev.cli.commands import profile_cmd, compile_cmd, annotate_cmd
from qoodev.stability.error_handler import (
    qoodevError,
    global_error_handler,
    ErrorBoundary,
    ErrorSeverity,
)
from qoodev.stability.crash_collector import install_crash_hook

app = typer.Typer(
    name="qoo",
    help="qoodev - Developer Toolchain for QooBot Humanoid Robot",
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
    debug: Optional[bool] = typer.Option(
        None, "--debug", "-d", help="Enable debug traceback output", is_eager=True
    ),
):
    """qoodev CLI - Build, test, and deploy QooBot skills.

    Run [bold]qoo --help[/bold] for available commands.
    """
    if version:
        _show_version()
        raise typer.Exit()

    # Install crash hook for production error tracking
    if not debug:
        install_crash_hook(command="qoo")

    # Install global error handler with rich output
    sys.excepthook = global_error_handler(
        exit_on_error=True,
        show_traceback=bool(debug),
        report_url=os.environ.get("qoodev_CRASH_URL", ""),
    )


def _show_version() -> None:
    """Display version information."""
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(style="bold cyan")
    info_table.add_column(style="white")
    info_table.add_row("qoodev CLI", f"v{__version__}")
    info_table.add_row("Python", sys.version.split()[0])
    info_table.add_row("Platform", sys.platform)
    info_table.add_row("Install", str(Path(__file__).resolve().parent.parent.parent))

    console.print(
        Panel(info_table, title="[bold]qoodev[/bold]", border_style="cyan")
    )


# ---------------------------------------------------------------------------
# Register subcommands
# ---------------------------------------------------------------------------
app.add_typer(init.app, name="init", help="Create a new QooBot project")
app.add_typer(build.app, name="build", help="Build the current project")
app.add_typer(run.app, name="run", help="Run the project in simulation")
app.add_typer(test.app, name="test", help="Run project tests")
app.add_typer(doctor.app, name="doctor", help="Diagnose development environment")
app.add_typer(sim.app, name="sim", help="Simulation environment management")
app.add_typer(package_cmd.app, name="package", help="Package and distribute skills")
app.add_typer(record_cmd.app, name="record", help="Record and replay sensor/control data")
app.add_typer(debug_cmd.app, name="debug", help="Remote debugging for skills")
app.add_typer(ci_cmd.app, name="ci", help="CI/CD integration commands")


# ---------------------------------------------------------------------------
# v1.5+ New Subcommands
# ---------------------------------------------------------------------------
app.add_typer(profile_cmd.app, name="profile", help="Performance profiling and analysis")
app.add_typer(compile_cmd.app, name="compile", help="Model compilation and cross-compilation")
app.add_typer(annotate_cmd.app, name="annotate", help="Data annotation and labeling tools")


# ---------------------------------------------------------------------------
# v1.0 New Subcommands
# ---------------------------------------------------------------------------

# QooEco marketplace subcommand
eco_app = typer.Typer(help="QooEco marketplace integration", rich_markup_mode="rich")


@eco_app.command("submit")
def eco_submit(
    package: str = typer.Argument(..., help="Path to .qooskills package"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="QooEco API key"),
    changelog: str = typer.Option("", "--changelog", help="Version changelog"),
):
    """Submit a skill to the QooEco marketplace."""
    from qoodev.qooeco import create_qooeco_client

    with ErrorBoundary("eco submit", suggestion="Check your API key and package path"):
        client = create_qooeco_client(api_key=api_key)
        client.authenticate()
        result = client.submit_skill(Path(package), changelog=changelog)
        if result.success:
            console.print(f"[green]✓[/green] Submitted: [bold]{result.submission_id}[/bold]")
            console.print(f"  Status: [yellow]{result.status.value}[/yellow]")
            if result.review_url:
                console.print(f"  Review: [cyan]{result.review_url}[/cyan]")
        else:
            console.print(f"[red]✗[/red] Submission failed: {result.message}")
            for err in result.errors:
                console.print(f"  [dim]- {err}[/dim]")


@eco_app.command("status")
def eco_status(
    submission_id: str = typer.Argument(..., help="Submission ID"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="QooEco API key"),
):
    """Check submission review status."""
    from qoodev.qooeco import create_qooeco_client

    client = create_qooeco_client(api_key=api_key)
    client.authenticate()
    result = client.get_submission_status(submission_id)
    console.print(f"  ID: [bold]{result.submission_id}[/bold]")
    console.print(f"  Status: [yellow]{result.status.value}[/yellow]")


@eco_app.command("search")
def eco_search(
    query: str = typer.Argument("", help="Search query"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max results"),
):
    """Search skills on QooEco marketplace."""
    from qoodev.qooeco import create_qooeco_client, SkillCategory

    client = create_qooeco_client()
    cat = SkillCategory(category) if category else None
    results = client.search_skills(query=query, category=cat, limit=limit)

    if not results:
        console.print("[dim]No skills found.[/dim]")
        return

    table = Table(title=f"QooEco Skills: '{query}'")
    table.add_column("Name", style="cyan")
    table.add_column("Author", style="dim")
    table.add_column("Version")
    table.add_column("Downloads")
    table.add_column("Rating")

    for skill in results:
        table.add_row(
            skill.name, skill.author, skill.version,
            str(skill.downloads), f"{skill.rating:.1f}★"
        )

    console.print(table)


app.add_typer(eco_app, name="eco", help="QooEco marketplace (submit, search, install)")


# Documentation generator subcommand
docs_app = typer.Typer(help="Documentation generation", rich_markup_mode="rich")


@docs_app.command("generate")
def docs_generate(
    output: str = typer.Option("docs_site", "--output", "-o", help="Output directory"),
):
    """Generate MkDocs documentation site."""
    from qoodev.docs_generator import DocSiteGenerator

    with ErrorBoundary("docs generate", suggestion="Check your project structure"):
        generator = DocSiteGenerator(Path(output).resolve())
        out_path = generator.generate()
        console.print(f"[green]✓[/green] Documentation generated at: [bold]{out_path}[/bold]")
        console.print(f"\n  To preview: [cyan]cd {out_path} && mkdocs serve[/cyan]")
        console.print(f"  To build:   [cyan]cd {out_path} && mkdocs build[/cyan]")


app.add_typer(docs_app, name="docs", help="Documentation site generator")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    """Entry point for console_scripts."""
    app()


if __name__ == "__main__":
    main()
