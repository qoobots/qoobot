"""
qoodev `qoo compile` CLI commands — v1.5+
Model compilation and cross-compilation for QooBot skills.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from qoodev.compiler import (
    CompilerBridge,
    ModelCompiler,
    CrossCompiler,
    Quantizer,
    ToolchainDetector,
    TargetArch,
    QuantizationMode,
    OptimizationLevel,
    Framework,
    CompileConfig,
    CrossCompileConfig,
    CompileResult,
    CrossCompileResult,
    format_compile_result,
)
from qoodev.stability.error_handler import ErrorBoundary

app = typer.Typer(help="Model compilation and cross-compilation", rich_markup_mode="rich")
console = Console()


# ============================================================================
# `qoo compile model` — Compile AI model to .qoomodel
# ============================================================================

@app.command("model")
def compile_model(
    model: str = typer.Argument(..., help="Path to model file (.onnx, .pt, .h5, .pdmodel)"),
    output: str = typer.Option("", "--output", "-o", help="Output .qoomodel path (auto if empty)"),
    target: str = typer.Option("x86_64", "--target", "-t", help="Target architecture: x86_64, aarch64, armv7l, riscv64"),
    quantize: str = typer.Option("none", "--quantize", "-q", help="Quantization: none, fp16, int8, int4, mixed"),
    optimize: int = typer.Option(2, "--optimize", "-O", help="Optimization level: 0-3"),
    framework: str = typer.Option("auto", "--framework", "-f", help="Model framework: auto, pytorch, onnx, tensorflow, tflite, paddle, jax"),
):
    """Compile an AI model to QooBot .qoomodel format.

    Supported input formats: ONNX (.onnx), PyTorch (.pt), TensorFlow (.h5/.pb), TFLite (.tflite)

    Example:
        qoo compile model model.onnx -t aarch64 -q int8 -O 3
    """
    with ErrorBoundary("compile model", suggestion="Check that qoocore toolchain is installed"):
        model_path = Path(model).resolve()
        if not model_path.exists():
            console.print(f"[red]✗[/red] Model file not found: {model_path}")
            raise typer.Exit(1)

        # Determine output path
        output_path = Path(output).resolve() if output else model_path.with_suffix(".qoomodel")

        # Parse enums
        try:
            arch = TargetArch(target)
        except ValueError:
            console.print(f"[red]✗[/red] Invalid target architecture: {target}")
            console.print(f"[dim]Valid targets: {', '.join(a.value for a in TargetArch)}[/dim]")
            raise typer.Exit(1)

        try:
            qmode = QuantizationMode(quantize)
        except ValueError:
            console.print(f"[red]✗[/red] Invalid quantization mode: {quantize}")
            raise typer.Exit(1)

        opt_level = OptimizationLevel(optimize) if 0 <= optimize <= 3 else OptimizationLevel.O2

        # Detect framework
        fw = Framework.AUTO
        if framework != "auto":
            try:
                fw = Framework(framework)
            except ValueError:
                console.print(f"[yellow]⚠[/yellow] Unknown framework '{framework}', using auto-detection")

        console.print(f"[cyan]Compiling model:[/cyan] {model_path.name}")
        console.print(f"  Target: [bold]{arch.value}[/bold]")
        console.print(f"  Quantization: [bold]{qmode.value.upper()}[/bold]")
        console.print(f"  Optimization: [bold]O{opt_level.value}[/bold]")
        console.print(f"  Output: [dim]{output_path}[/dim]\n")

        # Detect toolchain
        detector = ToolchainDetector()
        toolchain = detector.detect()

        console.print("[bold]Toolchain Status:[/bold]")
        tc_table = Table(show_header=False, box=None)
        tc_table.add_column(style="cyan")
        tc_table.add_column()
        tc_table.add_row("qoocore", "✅ Found" if toolchain.has_qoocore else "⚠ Not found (will use ONNX fallback)")
        tc_table.add_row("Cross Compiler", toolchain.cross_compiler or "Not configured")
        tc_table.add_row("CMake", toolchain.cmake_version or "Not found")
        console.print(tc_table)
        console.print()

        # Compile
        config = CompileConfig(
            target_arch=arch,
            quantization=qmode,
            optimization=opt_level,
            framework=fw,
        )

        compiler = ModelCompiler(toolchain)
        result = compiler.compile(str(model_path), str(output_path), config=config)

        # Display result
        if result.success:
            console.print(f"\n[green]✓[/green] Compilation successful!")
            _display_compile_result(result)
        else:
            console.print(f"\n[red]✗[/red] Compilation failed: {result.error}")
            if result.warnings:
                for w in result.warnings:
                    console.print(f"  [yellow]⚠[/yellow] {w}")


def _display_compile_result(result: CompileResult) -> None:
    """Display compilation result details."""
    table = Table(title="Compilation Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Output", str(result.output_path))
    table.add_row("Framework", result.framework or "unknown")
    table.add_row("Target Arch", result.target_arch or "unknown")
    table.add_row("Quantization", result.quantization or "none")
    table.add_row("Input Size", _format_bytes(result.input_size_bytes))
    table.add_row("Output Size", _format_bytes(result.output_size_bytes))
    if result.input_size_bytes and result.output_size_bytes:
        ratio = result.output_size_bytes / result.input_size_bytes * 100
        table.add_row("Compression", f"{ratio:.1f}%")
    table.add_row("Duration", f"{result.duration_seconds:.2f}s" if result.duration_seconds else "N/A")
    console.print(table)


# ============================================================================
# `qoo compile quantize` — Quantize model
# ============================================================================

@app.command("quantize")
def compile_quantize(
    model: str = typer.Argument(..., help="Path to .qoomodel or .onnx model"),
    mode: str = typer.Option("int8", "--mode", "-m", help="Quantization mode: fp16, int8, int4, mixed"),
    calibration: Optional[str] = typer.Option(None, "--calibration", "-c", help="Path to calibration dataset (for INT8)"),
    output: str = typer.Option("", "--output", "-o", help="Output path (auto if empty)"),
):
    """Quantize a model to reduce size and improve inference speed.

    Example:
        qoo compile quantize model.qoomodel -m int8 -c calibration_data/
    """
    with ErrorBoundary("compile quantize", suggestion="Check that qoocore toolchain is installed"):
        model_path = Path(model).resolve()
        if not model_path.exists():
            console.print(f"[red]✗[/red] Model file not found: {model_path}")
            raise typer.Exit(1)

        try:
            qmode = QuantizationMode(mode)
        except ValueError:
            console.print(f"[red]✗[/red] Invalid mode: {mode}")
            console.print(f"[dim]Valid modes: {', '.join(m.value for m in QuantizationMode)}[/dim]")
            raise typer.Exit(1)

        output_path = Path(output).resolve() if output else model_path.parent / f"{model_path.stem}_{mode}{model_path.suffix}"

        console.print(f"[cyan]Quantizing model:[/cyan] {model_path.name}")
        console.print(f"  Mode: [bold]{qmode.value.upper()}[/bold]")

        if calibration and qmode == QuantizationMode.INT8:
            console.print(f"  Calibration: [dim]{calibration}[/dim]")

        detector = ToolchainDetector()
        toolchain = detector.detect()
        quantizer = Quantizer(toolchain)
        result = quantizer.quantize(
            str(model_path), str(output_path), mode=qmode, calibration_data=calibration
        )

        if result.get("success"):
            console.print(f"\n[green]✓[/green] Quantization complete!")
            qtable = Table(title="Quantization Result")
            qtable.add_column("Metric", style="cyan")
            qtable.add_column("Value", style="green")
            qtable.add_row("Output", str(output_path))
            qtable.add_row("Original Size", _format_bytes(result.get("original_size", 0)))
            qtable.add_row("Quantized Size", _format_bytes(result.get("quantized_size", 0)))
            qtable.add_row("Accuracy Loss", f"{result.get('accuracy_loss_pct', 0):.2f}%")
            console.print(qtable)
        else:
            console.print(f"\n[red]✗[/red] Quantization failed: {result.get('error', 'unknown error')}")


# ============================================================================
# `qoo compile cross` — Cross-compile C++ skill
# ============================================================================

@app.command("cross")
def compile_cross(
    project: str = typer.Argument(".", help="Path to CMake project directory"),
    target: str = typer.Option("aarch64", "--target", "-t", help="Target architecture: x86_64, aarch64, armv7l, riscv64"),
    build_type: str = typer.Option("Release", "--build-type", help="CMake build type: Debug, Release, RelWithDebInfo"),
    toolchain_file: Optional[str] = typer.Option(None, "--toolchain", help="Custom CMake toolchain file"),
    output: str = typer.Option("build_cross", "--output", "-o", help="Output build directory"),
    jobs: int = typer.Option(0, "--jobs", "-j", help="Parallel build jobs (0 = auto)"),
):
    """Cross-compile a C++ skill for a target architecture.

    Example:
        qoo compile cross ./my_skill -t aarch64 -j 8
    """
    with ErrorBoundary("compile cross", suggestion="Ensure CMake and cross-compiler toolchain are installed"):
        project_path = Path(project).resolve()
        if not project_path.exists():
            console.print(f"[red]✗[/red] Project directory not found: {project_path}")
            raise typer.Exit(1)

        try:
            arch = TargetArch(target)
        except ValueError:
            console.print(f"[red]✗[/red] Invalid target: {target}")
            console.print(f"[dim]Valid targets: {', '.join(a.value for a in TargetArch)}[/dim]")
            raise typer.Exit(1)

        console.print(f"[cyan]Cross-compiling:[/cyan] {project_path.name}")
        console.print(f"  Target: [bold]{arch.value}[/bold]")
        console.print(f"  Build Type: [bold]{build_type}[/bold]")

        detector = ToolchainDetector()
        toolchain = detector.detect()
        config = CrossCompileConfig(
            target_arch=arch,
            build_type=build_type,
            toolchain_file=toolchain_file,
            build_dir=str(Path(output).resolve()),
            jobs=jobs,
        )

        compiler = CrossCompiler(toolchain)
        result = compiler.compile(str(project_path), config)

        if result.success:
            console.print(f"\n[green]✓[/green] Cross-compilation successful!")
            ctable = Table(title="Cross-Compilation Summary")
            ctable.add_column("Metric", style="cyan")
            ctable.add_column("Value", style="green")
            ctable.add_row("Target", result.target_arch or arch.value)
            ctable.add_row("Output Dir", str(result.output_dir))
            if result.artifacts:
                ctable.add_row("Artifacts", f"{len(result.artifacts)} files")
                for art in result.artifacts[:10]:
                    ctable.add_row("  ↳", str(art))
            ctable.add_row("Duration", f"{result.duration_seconds:.2f}s" if result.duration_seconds else "N/A")
            console.print(ctable)
        else:
            console.print(f"\n[red]✗[/red] Cross-compilation failed: {result.error}")
            if result.warnings:
                for w in result.warnings:
                    console.print(f"  [yellow]⚠[/yellow] {w}")


# ============================================================================
# `qoo compile toolchain` — Show toolchain status
# ============================================================================

@app.command("toolchain")
def compile_toolchain():
    """Display the status of installed compilation toolchains."""
    detector = ToolchainDetector()
    toolchain = detector.detect()

    console.print(Panel("[bold]qoodev Compilation Toolchain[/bold]", border_style="cyan"))

    # qoocore
    tc_table = Table(title="Toolchain Components")
    tc_table.add_column("Component", style="cyan")
    tc_table.add_column("Status")
    tc_table.add_column("Details")

    if toolchain.has_qoocore:
        tc_table.add_row("qoocore", "[green]✓ Installed[/green]", toolchain.qoocore_version or "version unknown")
    else:
        tc_table.add_row("qoocore", "[yellow]⚠ Not found[/yellow]", "Will use ONNX optimizer fallback")

    if toolchain.has_cross_compiler:
        tc_table.add_row("Cross Compiler", "[green]✓ Available[/green]", toolchain.cross_compiler or "")
    else:
        tc_table.add_row("Cross Compiler", "[yellow]⚠ Not found[/yellow]", "Cross-compilation disabled")

    if toolchain.has_cmake:
        tc_table.add_row("CMake", "[green]✓ Available[/green]", toolchain.cmake_version or "")
    else:
        tc_table.add_row("CMake", "[red]✗ Not found[/red]", "Required for C++ cross-compilation")

    console.print(tc_table)

    # Supported targets
    console.print("\n[bold]Supported Target Architectures:[/bold]")
    arch_table = Table()
    arch_table.add_column("Architecture", style="cyan")
    arch_table.add_column("Triplet")
    arch_table.add_column("Compilation")
    arch_table.add_column("Simulation")
    arch_table.add_row("x86_64", "x86_64-linux-gnu", "✅ Native", "✅ Native")
    arch_table.add_row("aarch64", "aarch64-linux-gnu", "🔧 Cross", "🔧 QEMU")
    arch_table.add_row("armv7l", "arm-linux-gnueabihf", "🔧 Cross", "🔧 QEMU")
    arch_table.add_row("riscv64", "riscv64-linux-gnu", "🔧 Cross", "🔧 QEMU")
    console.print(arch_table)


# ============================================================================
# Helpers
# ============================================================================

def _format_bytes(size_bytes: Optional[int]) -> str:
    """Format byte size to human-readable string."""
    if size_bytes is None:
        return "N/A"
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


if __name__ == "__main__":
    app()
