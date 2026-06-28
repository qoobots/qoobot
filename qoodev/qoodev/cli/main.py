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
    qoo eco                     qoostore marketplace
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

# qoostore marketplace subcommand
eco_app = typer.Typer(help="qoostore marketplace integration", rich_markup_mode="rich")


@eco_app.command("submit")
def eco_submit(
    package: str = typer.Argument(..., help="Path to .qooskills package"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="qoostore API key"),
    changelog: str = typer.Option("", "--changelog", help="Version changelog"),
):
    """Submit a skill to the qoostore marketplace."""
    from qoodev.qoostore import create_qoostore_client

    with ErrorBoundary("eco submit", suggestion="Check your API key and package path"):
        client = create_qoostore_client(api_key=api_key)
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
    api_key: Optional[str] = typer.Option(None, "--api-key", help="qoostore API key"),
):
    """Check submission review status."""
    from qoodev.qoostore import create_qoostore_client

    client = create_qoostore_client(api_key=api_key)
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
    """Search skills on qoostore marketplace."""
    from qoodev.qoostore import create_qoostore_client, SkillCategory

    client = create_qoostore_client()
    cat = SkillCategory(category) if category else None
    results = client.search_skills(query=query, category=cat, limit=limit)

    if not results:
        console.print("[dim]No skills found.[/dim]")
        return

    table = Table(title=f"qoostore Skills: '{query}'")
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


app.add_typer(eco_app, name="eco", help="qoostore marketplace (submit, search, install)")


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
# v1.6+ New Subcommands
# ---------------------------------------------------------------------------

# IDE tools subcommand
ide_app = typer.Typer(help="IDE integration tools", rich_markup_mode="rich")


@ide_app.command("jetbrains")
def ide_jetbrains(
    ide: str = typer.Option("pycharm", "--ide", "-i", help="Target IDE: pycharm, clion, idea"),
):
    """Generate JetBrains IDE plugin configuration."""
    from qoodev.ide import JetBrainsPlugin
    from qoodev.ide.jetbrains_plugin import JetBrainsIDE

    ide_map = {"pycharm": JetBrainsIDE.PYCHARM, "clion": JetBrainsIDE.CLION, "idea": JetBrainsIDE.IDEA}
    target = ide_map.get(ide, JetBrainsIDE.PYCHARM)

    plugin = JetBrainsPlugin(Path.cwd(), target)
    plugin.generate_config()
    console.print(f"[green]✓[/green] JetBrains config generated for [bold]{ide}[/bold]")


@ide_app.command("generate")
def ide_generate(
    source: str = typer.Argument(..., help="Source config: sensors.yaml, tree.btree.json, model.yaml, service.yaml"),
    output: str = typer.Option("src", "--output", "-o", help="Output directory"),
):
    """Generate code from sensor config, behavior tree, model, or service spec."""
    from qoodev.ide import CodeGenerator

    gen = CodeGenerator(Path(output).resolve())

    ext = Path(source).suffix
    if "sensor" in source.lower():
        gen.from_sensor_config(source)
    elif "btree" in source.lower() or "tree" in source.lower():
        gen.from_behavior_tree(source)
    elif "model" in source.lower():
        gen.from_model_def(source)
    elif "service" in source.lower() or "svc" in source.lower():
        gen.from_service_spec(source)
    else:
        console.print(f"[red]✗[/red] Unknown source type: {source}")
        console.print("  Supported: sensors.yaml, *.btree.json, model.yaml, service.yaml")


@ide_app.command("manifest")
def ide_manifest(
    name: str = typer.Argument(..., help="Skill name"),
    template: str = typer.Option("default", "--template", "-t", help="Template: default, perception, navigation, interaction, minimal"),
):
    """Create or edit a QooBot skill manifest."""
    from qoodev.ide import SkillManifestEditor

    editor = SkillManifestEditor.create_from_template(name, template)
    editor.show()

    # Interactive editing loop
    console.print("\n[bold]Manifest Editor[/bold] — type [cyan]help[/cyan] for commands, [cyan]save[/cyan] to save, [cyan]quit[/cyan] to exit")
    while True:
        try:
            cmd = input("\n[manifest] > ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not cmd:
            continue

        parts = cmd.split()
        action = parts[0].lower()

        if action == "quit":
            break
        elif action == "save":
            editor.save()
        elif action == "show":
            editor.show()
        elif action == "validate":
            editor.validate()
        elif action == "add-perm" and len(parts) >= 2:
            level = parts[2] if len(parts) > 2 else "read"
            editor.add_permission(parts[1], level)
        elif action == "remove-perm" and len(parts) >= 2:
            editor.remove_permission(parts[1])
        elif action == "add-privacy" and len(parts) >= 2:
            sensitivity = parts[2] if len(parts) > 2 else "medium"
            editor.add_privacy_label(parts[1], "", sensitivity)
        elif action == "help":
            console.print("add-perm <resource> [level] | remove-perm <resource> | "
                           "add-privacy <data_type> [sensitivity] | show | validate | save | quit")
        else:
            console.print(f"[red]Unknown command: {action}[/red] (type 'help')")


app.add_typer(ide_app, name="ide", help="IDE integration (jetbrains, generate, manifest)")


# Domain randomization subcommand
dr_app = typer.Typer(help="Domain randomization for Sim2Real", rich_markup_mode="rich")


@dr_app.command("init")
def dr_init(
    output: str = typer.Option("domain_config.yaml", "--output", "-o", help="Output config file"),
):
    """Create a default domain randomization config."""
    from qoodev.domain_randomization import DomainRandomizer

    dr = DomainRandomizer()
    dr.save_config(output)


@dr_app.command("step")
def dr_step(
    config: str = typer.Option("domain_config.yaml", "--config", "-c", help="Config file"),
    num_steps: int = typer.Option(1, "--num", "-n", help="Number of steps"),
):
    """Run domain randomization steps."""
    from qoodev.domain_randomization import DomainRandomizer

    dr = DomainRandomizer.from_config(config)
    for _ in range(num_steps):
        state = dr.step()
        console.print(f"[dim]Episode {state.episode}:[/dim] {len(state.param_values)} params randomized")
    dr.show_state()


@dr_app.command("curriculum")
def dr_curriculum(
    config: str = typer.Option("domain_config.yaml", "--config", "-c", help="Config file"),
    episodes_per_level: int = typer.Option(100, "--per-level", "-n", help="Episodes per difficulty level"),
    start_level: str = typer.Option("easy", "--start", "-s", help="Starting difficulty"),
):
    """Enable curriculum learning with progressive difficulty."""
    from qoodev.domain_randomization import DomainRandomizer, DifficultyLevel

    dr = DomainRandomizer.from_config(config)
    level = DifficultyLevel(start_level)
    dr.enable_curriculum(episodes_per_level, level)


app.add_typer(dr_app, name="dr", help="Domain randomization (init, step, curriculum)")


# Data management subcommand
data_app = typer.Typer(help="Dataset management tools", rich_markup_mode="rich")


@data_app.command("init")
def data_init(
    path: str = typer.Argument(..., help="Dataset directory path"),
):
    """Initialize a new dataset."""
    from qoodev.data_management import DataManager

    dm = DataManager(path, create=True)
    dm.summary()


@data_app.command("add")
def data_add(
    dataset: str = typer.Argument(..., help="Dataset directory"),
    source: str = typer.Argument(..., help="Source directory of data files"),
):
    """Add samples to a dataset."""
    from qoodev.data_management import DataManager

    dm = DataManager(dataset)
    added = dm.add_samples(source)
    console.print(f"[green]✓[/green] Added [bold]{added}[/bold] samples")


@data_app.command("version")
def data_version(
    dataset: str = typer.Argument(..., help="Dataset directory"),
    tag: str = typer.Argument(..., help="Version tag (e.g., v1.0)"),
    message: str = typer.Option("", "--message", "-m", help="Version message"),
):
    """Create a dataset version snapshot."""
    from qoodev.data_management import DataManager

    dm = DataManager(dataset)
    dm.version(tag, message)


@data_app.command("clean")
def data_clean(
    dataset: str = typer.Argument(..., help="Dataset directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview only, don't remove"),
):
    """Clean dataset (deduplicate, remove outliers, validate)."""
    from qoodev.data_management import DataManager

    dm = DataManager(dataset)
    dm.clean(dry_run=dry_run)


@data_app.command("report")
def data_report(
    dataset: str = typer.Argument(..., help="Dataset directory"),
):
    """Generate dataset quality report."""
    from qoodev.data_management import DataManager

    dm = DataManager(dataset)
    dm.quality_report()


@data_app.command("split")
def data_split(
    dataset: str = typer.Argument(..., help="Dataset directory"),
    train: float = typer.Option(0.7, "--train", help="Train ratio"),
    val: float = typer.Option(0.15, "--val", help="Validation ratio"),
    test: float = typer.Option(0.15, "--test", help="Test ratio"),
    strategy: str = typer.Option("random", "--strategy", "-s", help="Split strategy: random, stratified, temporal"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
):
    """Split dataset into train/val/test sets."""
    from qoodev.data_management import DataManager, SplitStrategy

    dm = DataManager(dataset)
    strat = {"random": SplitStrategy.RANDOM, "stratified": SplitStrategy.STRATIFIED, "temporal": SplitStrategy.TEMPORAL}.get(strategy, SplitStrategy.RANDOM)
    dm.split(train_ratio=train, val_ratio=val, test_ratio=test, strategy=strat, seed=seed)


@data_app.command("export")
def data_export(
    dataset: str = typer.Argument(..., help="Dataset directory"),
    format: str = typer.Option("coco", "--format", "-f", help="Export format: coco, yolo"),
    output: str = typer.Option("./export", "--output", "-o", help="Output path"),
):
    """Export dataset to standard format."""
    from qoodev.data_management import DataManager

    dm = DataManager(dataset)
    if format == "coco":
        dm.export_coco(output)
    elif format == "yolo":
        dm.export_yolo(output)
    else:
        console.print(f"[red]✗[/red] Unknown format: {format}")


app.add_typer(data_app, name="data", help="Dataset management (init, add, version, clean, report, split, export)")


# Behavior tree debugger subcommand
bt_app = typer.Typer(help="Behavior tree debugging", rich_markup_mode="rich")


@bt_app.command("debug")
def bt_debug(
    tree_file: str = typer.Argument(..., help="Path to behavior tree JSON file"),
):
    """Start interactive behavior tree debugger."""
    from qoodev.bt_debugger import BehaviorTreeDebugger
    import json

    tree_path = Path(tree_file)
    if not tree_path.exists():
        console.print(f"[red]✗[/red] Tree file not found: {tree_file}")
        raise typer.Exit(1)

    tree_data = json.loads(tree_path.read_text(encoding="utf-8"))
    tree_name = tree_data.get("name", tree_path.stem)

    debugger = BehaviorTreeDebugger(tree_name)
    debugger.register_tree(tree_data.get("root", tree_data))
    debugger.cli_interactive()


@bt_app.command("replay")
def bt_replay(
    session_file: str = typer.Argument(..., help="Path to debug session JSON"),
    speed: float = typer.Option(1.0, "--speed", "-s", help="Replay speed multiplier"),
):
    """Replay a previously recorded behavior tree debug session."""
    from qoodev.bt_debugger import BehaviorTreeDebugger

    debugger = BehaviorTreeDebugger("replay")
    debugger.replay_session(Path(session_file), speed)


app.add_typer(bt_app, name="bt", help="Behavior tree debugging (debug, replay)")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

def main():
    """Entry point for console_scripts."""
    app()


if __name__ == "__main__":
    main()
