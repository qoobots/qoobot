"""qoo build - Build command.

Builds QooBot projects of different types (skill/service/model),
supporting Python, C++, and model compilation targets.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

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
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Verbose build output"
    ),
):
    """Build the current QooBot project.

    Detects project type and runs appropriate build steps:
    - Python projects: installs dependencies, runs type checking
    - C++ projects: runs CMake build
    - Model projects: compiles models via qoocore toolchain
    """
    from qoodev.cli.context import ProjectContext

    ctx = ProjectContext.from_cwd()
    if not ctx:
        console.print("[red]Error:[/red] Not in a QooBot project directory.")
        console.print("Run [bold]qoo init <name>[/bold] to create a project first.")
        raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold cyan]{ctx.name}[/bold cyan]  v{ctx.version}",
            title="Build",
            border_style="blue",
        )
    )
    console.print(f"  Project type: [yellow]{ctx.project_type}[/yellow]")
    console.print(f"  Mode: {'[green]release[/green]' if release else '[dim]debug[/dim]'}")
    console.print(f"  Target: [cyan]{target}[/cyan]")
    console.print()

    build_start = time.perf_counter()
    results: dict[str, bool] = {}

    # ── Python build ──
    if target in ("all", "python"):
        results["python"] = _build_python(ctx, release, verbose)

    # ── C++ build ──
    if target in ("all", "cpp"):
        results["cpp"] = _build_cpp(ctx, release, verbose)

    # ── Model build ──
    if target in ("all", "model"):
        results["model"] = _build_model(ctx, release, verbose)

    # ── Summary ──
    build_time = time.perf_counter() - build_start

    table = Table(title="Build Results", box=None)
    table.add_column("Target", style="cyan")
    table.add_column("Status")
    table.add_column("Duration")

    all_ok = True
    for name, ok in results.items():
        status = "[green]✓ PASS[/green]" if ok else "[red]✗ FAIL[/red]"
        table.add_row(name, status, f"{build_time:.1f}s" if name == list(results.keys())[0] else "")
        if not ok:
            all_ok = False

    console.print(table)
    console.print(f"\nTotal build time: [bold]{build_time:.1f}s[/bold]")

    if not all_ok:
        console.print("\n[red]Build failed.[/red] Check the output above for details.")
        raise typer.Exit(code=1)

    console.print("\n[green]✓[/green] Build completed successfully.")


@app.command()
def clean(
    all: bool = typer.Option(
        False, "--all", "-a", help="Remove all build artifacts including cache"
    ),
):
    """Clean build artifacts."""
    from qoodev.cli.context import ProjectContext

    ctx = ProjectContext.from_cwd()
    root = ctx.root if ctx else Path.cwd()

    cleaned = []

    # Clean build directory
    build_dir = root / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
        cleaned.append("build/")

    # Clean dist directory
    dist_dir = root / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        cleaned.append("dist/")

    # Clean Python cache
    for pattern in ["__pycache__", "*.egg-info"]:
        for p in root.rglob(pattern):
            if p.is_dir():
                shutil.rmtree(p)
                cleaned.append(str(p.relative_to(root)))

    # Clean C++ artifacts
    for pattern in ["*.o", "*.obj", "*.so", "*.dylib", "*.dll"]:
        for p in root.rglob(pattern):
            if p.is_file() and "node_modules" not in str(p):
                p.unlink()
                cleaned.append(str(p.relative_to(root)))

    # Clean CMake cache
    cmake_cache = root / "CMakeCache.txt"
    if cmake_cache.exists():
        cmake_cache.unlink()
        cleaned.append("CMakeCache.txt")

    cmake_files = root / "CMakeFiles"
    if cmake_files.exists():
        shutil.rmtree(cmake_files)
        cleaned.append("CMakeFiles/")

    if all:
        for cache_dir in [root / ".mypy_cache", root / ".ruff_cache", root / ".pytest_cache"]:
            if cache_dir.exists():
                shutil.rmtree(cache_dir)
                cleaned.append(str(cache_dir.relative_to(root)))

    if cleaned:
        console.print("[green]✓[/green] Cleaned:")
        for item in cleaned:
            console.print(f"  [dim]- {item}[/dim]")
    else:
        console.print("[dim]Nothing to clean.[/dim]")


# ── Internal builders ──────────────────────────────────────────


def _build_python(ctx, release: bool, verbose: bool) -> bool:
    """Build a Python project.

    Steps:
    1. Install project dependencies (pip install -e .)
    2. Run type checking (mypy) if available
    3. Run linting (ruff) if available
    """
    console.print("[bold]Python Build[/bold]")
    root = ctx.root

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Step 1: Install project in development mode
        task = progress.add_task("Installing project dependencies...", total=None)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(root)],
                capture_output=not verbose,
                text=True,
                cwd=str(root),
                timeout=120,
            )
            if result.returncode != 0:
                progress.remove_task(task)
                console.print(f"[red]✗[/red] pip install failed")
                if verbose and result.stderr:
                    console.print(f"  [dim]{result.stderr[-500:]}[/dim]")
                return False
        except subprocess.TimeoutExpired:
            progress.remove_task(task)
            console.print("[red]✗[/red] pip install timed out")
            return False
        except FileNotFoundError:
            progress.remove_task(task)
            console.print("[red]✗[/red] pip not found. Is Python installed?")
            return False
        progress.remove_task(task)
        console.print("  [green]✓[/green] Dependencies installed")

        # Step 2: Type checking
        task = progress.add_task("Type checking (mypy)...", total=None)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "mypy", str(ctx.src_dir), "--ignore-missing-imports"],
                capture_output=not verbose,
                text=True,
                cwd=str(root),
                timeout=60,
            )
            if result.returncode == 0:
                progress.remove_task(task)
                console.print("  [green]✓[/green] Type check passed")
            else:
                progress.remove_task(task)
                console.print("  [yellow]⚠[/yellow] Type check warnings (non-fatal)")
                if verbose and result.stdout:
                    console.print(f"  [dim]{result.stdout[-300:]}[/dim]")
        except Exception:
            progress.remove_task(task)
            console.print("  [dim]⊘[/dim] Type check skipped (mypy not available)")

        # Step 3: Linting
        task = progress.add_task("Linting (ruff)...", total=None)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", str(ctx.src_dir)],
                capture_output=not verbose,
                text=True,
                cwd=str(root),
                timeout=60,
            )
            if result.returncode == 0:
                progress.remove_task(task)
                console.print("  [green]✓[/green] Lint passed")
            else:
                progress.remove_task(task)
                console.print("  [yellow]⚠[/yellow] Lint warnings (non-fatal)")
        except Exception:
            progress.remove_task(task)
            console.print("  [dim]⊘[/dim] Lint skipped (ruff not available)")

    return True


def _build_cpp(ctx, release: bool, verbose: bool) -> bool:
    """Build a C++ project using CMake.

    Checks for CMakeLists.txt existence and runs cmake build.
    """
    console.print("[bold]C++ Build[/bold]")
    root = ctx.root

    cmake_file = root / "CMakeLists.txt"
    if not cmake_file.exists():
        console.print("  [dim]⊘[/dim] No CMakeLists.txt found, skipping C++ build")
        return True

    build_dir = root / "build" / ("release" if release else "debug")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        build_type = "Release" if release else "Debug"

        # Step 1: Configure
        task = progress.add_task("Configuring CMake...", total=None)
        try:
            build_dir.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(
                ["cmake", str(root), "-B", str(build_dir),
                 f"-DCMAKE_BUILD_TYPE={build_type}"],
                capture_output=not verbose,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                progress.remove_task(task)
                console.print(f"[red]✗[/red] CMake configure failed")
                if verbose and result.stderr:
                    console.print(f"  [dim]{result.stderr[-500:]}[/dim]")
                return False
        except FileNotFoundError:
            progress.remove_task(task)
            console.print("  [dim]⊘[/dim] CMake not found, skipping C++ build")
            return True
        except subprocess.TimeoutExpired:
            progress.remove_task(task)
            console.print("[red]✗[/red] CMake configure timed out")
            return False
        progress.remove_task(task)
        console.print("  [green]✓[/green] CMake configured")

        # Step 2: Build
        n_jobs = max(1, (subprocess.run(
            ["nproc"], capture_output=True, text=True
        ).stdout.strip() if sys.platform != "win32" else str(4)))

        task = progress.add_task(f"Building (parallel={n_jobs})...", total=None)
        try:
            result = subprocess.run(
                ["cmake", "--build", str(build_dir), "--parallel", str(n_jobs)],
                capture_output=not verbose,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                progress.remove_task(task)
                console.print(f"[red]✗[/red] Build failed")
                if verbose and result.stderr:
                    console.print(f"  [dim]{result.stderr[-500:]}[/dim]")
                return False
        except subprocess.TimeoutExpired:
            progress.remove_task(task)
            console.print("[red]✗[/red] Build timed out")
            return False
        progress.remove_task(task)
        console.print("  [green]✓[/green] C++ build complete")

    return True


def _build_model(ctx, release: bool, verbose: bool) -> bool:
    """Build AI model artifacts.

    Looks for model configuration files and invokes qoocore compiler bridge
    if available.
    """
    console.print("[bold]Model Build[/bold]")
    root = ctx.root

    # Check for model sources
    model_dir = root / "models"
    if not model_dir.exists() or not any(model_dir.iterdir()):
        console.print("  [dim]⊘[/dim] No models directory found, skipping model build")
        return True

    # Find model files
    model_files = []
    for ext in [".onnx", ".pt", ".pth", ".tflite", ".h5", ".pb"]:
        model_files.extend(model_dir.rglob(f"*{ext}"))

    if not model_files:
        console.print("  [dim]⊘[/dim] No model files found, skipping model build")
        return True

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        task = progress.add_task(f"Compiling {len(model_files)} model(s)...", total=None)
        try:
            # Try to use qoocore compiler bridge
            from qoodev.compiler import CompilerBridge, TargetArch

            compiler = CompilerBridge(root)
            for model_file in model_files:
                try:
                    compiler.compile_model(
                        model_file,
                        target=TargetArch.AARCH64,
                        quantize="fp16" if release else None,
                    )
                    console.print(f"  [green]✓[/green] Compiled: {model_file.name}")
                except Exception as e:
                    console.print(f"  [yellow]⚠[/yellow] Skipped {model_file.name}: {e}")
        except ImportError:
            # qoocore toolchain not available, just report
            console.print(f"  [yellow]⚠[/yellow] qoocore toolchain not available")
            console.print(f"  Found {len(model_files)} model(s) to compile:")
            for mf in model_files:
                console.print(f"  [dim]- {mf.relative_to(root)}[/dim]")
        except Exception as e:
            progress.remove_task(task)
            console.print(f"  [yellow]⚠[/yellow] Model compilation: {e}")
        progress.remove_task(task)

    return True
