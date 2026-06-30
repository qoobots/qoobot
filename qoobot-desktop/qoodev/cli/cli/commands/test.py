"""qoo test - Test command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(help="Run project tests", rich_markup_mode="rich")
console = Console()


@app.callback()
def callback():
    """Run QooBot project tests."""


@app.command()
def test(
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose output"
    ),
    coverage: bool = typer.Option(
        False, "--coverage", "-c", help="Generate coverage report"
    ),
    filter_pattern: str = typer.Option(
        "", "--filter", "-k", help="Only run tests matching pattern"
    ),
):
    """Run tests for the current project."""
    from cli.cli.context import ProjectContext

    ctx = ProjectContext.from_cwd()
    if not ctx:
        console.print("[red]Error:[/red] Not in a QooBot project directory.")
        raise typer.Exit(code=1)

    test_dir = ctx.root / "tests"
    if not test_dir.exists():
        console.print("[yellow]No tests directory found.[/yellow]")
        console.print(f"Create [bold]{test_dir}/[/bold] and add test files.")
        return

    console.print(f"[bold]Running tests[/bold] for [cyan]{ctx.name}[/cyan]...")

    pytest_args = [str(test_dir), "-v" if verbose else ""]
    if filter_pattern:
        pytest_args.extend(["-k", filter_pattern])
    if coverage:
        pytest_args.extend(["--cov=qoobot_sdk", "--cov-report=term-missing"])

    pytest_args = [a for a in pytest_args if a]  # Remove empty strings

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running pytest...", total=None)

        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest"] + pytest_args,
                cwd=str(ctx.root),
                capture_output=not verbose,
                text=True,
            )
        except FileNotFoundError:
            progress.remove_task(task)
            console.print("[red]Error:[/red] pytest is not installed.")
            console.print("Install with: [bold]pip install pytest[/bold]")
            raise typer.Exit(code=1)

        progress.remove_task(task)

    if result.returncode == 0:
        console.print("[green]✓[/green] All tests passed.")
    else:
        console.print("[red]✗[/red] Some tests failed.")
        if not verbose and result.stdout:
            console.print(result.stdout)
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        raise typer.Exit(code=result.returncode)
