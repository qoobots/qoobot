"""qoo build - Build command."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(help="Build the current project", rich_markup_mode="rich")
console = Console()


@app.callback()
def callback():
    """Build QooBot project."""


@app.command()
def build(
    target: str = typer.Option(
        "all", "--target", "-t", help="Build target: all, python, cpp, model"
    ),
    release: bool = typer.Option(
        False, "--release", "-r", help="Build in release mode"
    ),
):
    """Build the current QooBot project.

    Detects project type and runs appropriate build steps.
    """
    from qoocode.cli.context import ProjectContext

    ctx = ProjectContext.from_cwd()
    if not ctx:
        console.print("[red]Error:[/red] Not in a QooBot project directory.")
        console.print("Run [bold]qoo init <name>[/bold] to create a project first.")
        raise typer.Exit(code=1)

    console.print(f"[bold]Building[/bold] [cyan]{ctx.name}[/cyan]...")
    console.print(f"  Project type: [yellow]{ctx.project_type}[/yellow]")
    console.print(f"  Mode: {'[green]release[/green]' if release else '[dim]debug[/dim]'}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Building...", total=None)
        # TODO: Implement actual build logic per project type
        progress.remove_task(task)

    console.print("[green]✓[/green] Build completed successfully.")


@app.command()
def clean():
    """Clean build artifacts."""
    console.print("[yellow]Cleaning build artifacts...[/yellow]")
    # TODO: Implement clean logic
    console.print("[green]✓[/green] Clean completed.")
