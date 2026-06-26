"""qoo init - Project scaffolding command."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from qoocode.cli.scaffold import ProjectScaffold

app = typer.Typer(help="Create a new QooBot project", rich_markup_mode="rich")
console = Console()


@app.callback()
def callback():
    """Initialize a new QooBot project."""


@app.command()
def init(
    name: str = typer.Argument(..., help="Project name"),
    template: str = typer.Option(
        "skill", "--template", "-t", help="Project template: skill, service, model"
    ),
    path: Optional[Path] = typer.Option(
        None, "--path", "-p", help="Target directory (default: ./<name>)"
    ),
    python_version: str = typer.Option(
        "3.11", "--python", help="Minimum Python version"
    ),
):
    """Create a new QooBot project from a template.

    Examples:
        qoo init my-skill
        qoo init my-skill -t service
        qoo init my-skill -t model -p ~/projects/
    """
    valid_templates = ["skill", "service", "model"]
    if template not in valid_templates:
        console.print(f"[red]Error:[/red] Unknown template '{template}'. "
                      f"Choose from: {', '.join(valid_templates)}")
        raise typer.Exit(code=1)

    target_path = path or Path.cwd() / name

    if target_path.exists():
        console.print(f"[red]Error:[/red] Directory '{target_path}' already exists.")
        raise typer.Exit(code=1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Creating project [bold]{name}[/bold]...", total=None)

        scaffold = ProjectScaffold(
            name=name,
            template=template,
            target_path=target_path,
            python_version=python_version,
        )
        created_files = scaffold.create()

        progress.remove_task(task)

    console.print(
        Panel.fit(
            f"[green]✓[/green] Project [bold cyan]{name}[/bold cyan] created successfully!\n\n"
            f"Template: [yellow]{template}[/yellow]\n"
            f"Location: [dim]{target_path}[/dim]\n"
            f"Files created: {len(created_files)}",
            title="[bold]Project Created[/bold]",
            border_style="green",
        )
    )

    console.print("\n[bold]Next steps:[/bold]")
    console.print(f"  cd {name}")
    console.print(f"  qoo build")
    console.print(f"  qoo run")
