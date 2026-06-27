"""
qoodev `qoo profile` CLI commands — v1.5+
Performance profiling for QooBot skills.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from qoodev.profiler import (
    ProfilerSession,
    LatencyTracker,
    CommunicationProfiler,
    ModelProfiler,
    ResourceMonitor,
    FlameGraphBuilder,
    BottleneckDetector,
    ProfilerReport,
    Severity,
)
from qoodev.stability.error_handler import ErrorBoundary

app = typer.Typer(help="Performance profiling and analysis", rich_markup_mode="rich")
console = Console()


# ============================================================================
# `qoo profile run` — Profile a skill execution
# ============================================================================

@app.command("run")
def profile_run(
    skill_file: str = typer.Argument(..., help="Path to the skill Python file"),
    duration: int = typer.Option(30, "--duration", "-d", help="Profile duration in seconds"),
    output: str = typer.Option("profile_report", "--output", "-o", help="Output report directory"),
    monitor_resources: bool = typer.Option(
        True, "--resources/--no-resources", help="Monitor CPU/GPU/NPU/Memory usage"
    ),
    trace_comm: bool = typer.Option(
        False, "--comm", help="Trace DDS/ROS2 communication"
    ),
    profile_inference: bool = typer.Option(
        False, "--inference", help="Profile model inference"
    ),
    generate_flame: bool = typer.Option(
        True, "--flame/--no-flame", help="Generate flame graph data"
    ),
    detect_bottlenecks: bool = typer.Option(
        True, "--bottlenecks/--no-bottlenecks", help="Auto-detect performance bottlenecks"
    ),
    format: str = typer.Option(
        "all", "--format", "-f", help="Output format: json, html, terminal, all"
    ),
):
    """Profile a QooBot skill and generate performance report.

    Example:
        qoo profile run my_skill.py -d 60 --comm --inference -o ./profiles
    """
    from qoodev.profiler import ProfilerSession

    with ErrorBoundary("profile run", suggestion="Check that the skill file exists and is valid"):
        skill_path = Path(skill_file).resolve()
        if not skill_path.exists():
            console.print(f"[red]✗[/red] Skill file not found: {skill_path}")
            raise typer.Exit(1)

        output_path = Path(output).resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        console.print(f"[cyan]Profiling:[/cyan] {skill_path.name}")
        console.print(f"[dim]Duration: {duration}s | Output: {output_path}[/dim]\n")

        with ProfilerSession(
            name=skill_path.stem,
            output_dir=str(output_path),
            monitor_resources=monitor_resources,
            trace_communication=trace_comm,
            profile_inference=profile_inference,
            generate_flame=generate_flame,
            detect_bottlenecks=detect_bottlenecks,
        ) as session:
            # Simulate running the skill (in real usage, this would exec the skill)
            import runpy
            import sys
            import threading
            import time

            # Add skill directory to path
            skill_dir = str(skill_path.parent)
            if skill_dir not in sys.path:
                sys.path.insert(0, skill_dir)

            def run_skill():
                try:
                    runpy.run_path(str(skill_path), run_name="__qoodev_profile__")
                except SystemExit:
                    pass

            # Start skill in background, profile for the specified duration
            thread = threading.Thread(target=run_skill, daemon=True)
            thread.start()

            console.print("[dim]Profiling in progress...[/dim]")
            import time as _time
            _time.sleep(duration)

        # Display report
        _display_profile_report(session.report, format, output_path)


def _display_profile_report(report: ProfilerReport, fmt: str, output_path: Path) -> None:
    """Display profiling report in the requested format."""
    if fmt in ("terminal", "all"):
        _display_terminal_report(report)

    if fmt in ("json", "all"):
        json_path = output_path / f"{report.name}_report.json"
        with open(json_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        console.print(f"\n[dim]JSON report saved to: {json_path}[/dim]")

    if fmt in ("html", "all"):
        html_path = output_path / f"{report.name}_report.html"
        _generate_html_report(report, html_path)
        console.print(f"[dim]HTML report saved to: {html_path}[/dim]")


def _display_terminal_report(report: ProfilerReport) -> None:
    """Display profiling report in the terminal using rich tables."""

    # Summary
    summary_table = Table(title="[bold]Performance Profile Report[/bold]", show_header=False)
    summary_table.add_column(style="bold cyan")
    summary_table.add_column()
    summary_table.add_row("Skill", report.name)
    summary_table.add_row("Duration", f"{report.duration:.2f}s")
    summary_table.add_row("Samples", str(report.sample_count))
    console.print(Panel(summary_table, border_style="cyan"))

    # Latency breakdown
    if report.latency_breakdown:
        console.print("\n[bold]End-to-End Latency Breakdown:[/bold]")
        lat_table = Table()
        lat_table.add_column("Stage", style="cyan")
        lat_table.add_column("Avg (ms)", justify="right")
        lat_table.add_column("P50 (ms)", justify="right")
        lat_table.add_column("P99 (ms)", justify="right")
        lat_table.add_column("Max (ms)", justify="right")
        lat_table.add_column("Count", justify="right")

        for stage, stats in report.latency_breakdown.items():
            lat_table.add_row(
                stage,
                f"{stats.get('avg', 0):.2f}",
                f"{stats.get('p50', 0):.2f}",
                f"{stats.get('p99', 0):.2f}",
                f"{stats.get('max', 0):.2f}",
                str(stats.get('count', 0)),
            )
        console.print(lat_table)

    # Resource usage
    if report.resource_usage:
        console.print("\n[bold]Resource Utilization:[/bold]")
        res_table = Table()
        res_table.add_column("Resource", style="cyan")
        res_table.add_column("Avg (%)", justify="right")
        res_table.add_column("Peak (%)", justify="right")
        res_table.add_column("Avg Mem (MB)", justify="right")
        res_table.add_column("Peak Mem (MB)", justify="right")

        for res, stats in report.resource_usage.items():
            res_table.add_row(
                res,
                f"{stats.get('avg_util', 0):.1f}",
                f"{stats.get('peak_util', 0):.1f}",
                f"{stats.get('avg_mem', 0):.1f}",
                f"{stats.get('peak_mem', 0):.1f}",
            )
        console.print(res_table)

    # Communication profiling
    if report.communication_stats:
        console.print("\n[bold]Communication Stats:[/bold]")
        comm_table = Table()
        comm_table.add_column("Topic", style="cyan")
        comm_table.add_column("Avg Latency (ms)", justify="right")
        comm_table.add_column("P99 Latency (ms)", justify="right")
        comm_table.add_column("Bandwidth (MB/s)", justify="right")
        comm_table.add_column("Drop Rate (%)", justify="right")
        comm_table.add_column("Messages", justify="right")

        for topic, stats in report.communication_stats.items():
            comm_table.add_row(
                topic,
                f"{stats.get('avg_latency_ms', 0):.2f}",
                f"{stats.get('p99_latency_ms', 0):.2f}",
                f"{stats.get('bandwidth_mbps', 0):.2f}",
                f"{stats.get('drop_rate_pct', 0):.2f}",
                str(stats.get('message_count', 0)),
            )
        console.print(comm_table)

    # Bottlenecks
    if report.bottlenecks:
        console.print("\n[bold red]Detected Bottlenecks:[/bold red]")
        for bn in report.bottlenecks:
            sev_color = {
                Severity.CRITICAL: "red",
                Severity.HIGH: "yellow",
                Severity.MEDIUM: "cyan",
                Severity.LOW: "dim",
            }
            color = sev_color.get(bn.severity, "white")
            console.print(
                f"  [{color}]●[/{color}] [{color}]{bn.severity.value.upper()}[/{color}] "
                f"[bold]{bn.description}[/bold]"
            )
            if bn.suggestion:
                console.print(f"    [dim]→ {bn.suggestion}[/dim]")

    if not report.latency_breakdown and not report.resource_usage and not report.bottlenecks:
        console.print("[dim]No profiling data collected.[/dim]")


def _generate_html_report(report: ProfilerReport, output_path: Path) -> None:
    """Generate a standalone HTML profiling report."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>qoodev Profile: {report.name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 960px; margin: 0 auto; padding: 24px; background: #0d1117; color: #c9d1d9; }}
  h1 {{ color: #58a6ff; }}
  h2 {{ color: #f0883e; margin-top: 32px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
  th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #21262d; }}
  th {{ background: #161b22; color: #8b949e; }}
  .critical {{ color: #f85149; }}
  .high {{ color: #d29922; }}
  .medium {{ color: #58a6ff; }}
  .low {{ color: #8b949e; }}
  .metric {{ font-family: 'SF Mono', monospace; text-align: right; }}
</style>
</head>
<body>
<h1>qoodev Performance Profile: {report.name}</h1>
<p>Duration: {report.duration:.2f}s | Samples: {report.sample_count}</p>
"""
    # Latency section
    if report.latency_breakdown:
        html += "<h2>Latency Breakdown</h2><table><tr><th>Stage</th><th>Avg (ms)</th><th>P50 (ms)</th><th>P99 (ms)</th><th>Max (ms)</th></tr>"
        for stage, stats in report.latency_breakdown.items():
            html += f"<tr><td>{stage}</td><td class='metric'>{stats.get('avg', 0):.2f}</td><td class='metric'>{stats.get('p50', 0):.2f}</td><td class='metric'>{stats.get('p99', 0):.2f}</td><td class='metric'>{stats.get('max', 0):.2f}</td></tr>"
        html += "</table>"

    # Resource section
    if report.resource_usage:
        html += "<h2>Resource Utilization</h2><table><tr><th>Resource</th><th>Avg (%)</th><th>Peak (%)</th><th>Avg Mem (MB)</th><th>Peak Mem (MB)</th></tr>"
        for res, stats in report.resource_usage.items():
            html += f"<tr><td>{res}</td><td class='metric'>{stats.get('avg_util', 0):.1f}</td><td class='metric'>{stats.get('peak_util', 0):.1f}</td><td class='metric'>{stats.get('avg_mem', 0):.1f}</td><td class='metric'>{stats.get('peak_mem', 0):.1f}</td></tr>"
        html += "</table>"

    # Bottlenecks
    if report.bottlenecks:
        html += "<h2>Bottlenecks</h2><ul>"
        for bn in report.bottlenecks:
            sev = bn.severity.value
            html += f"<li class='{sev}'><strong>[{sev.upper()}]</strong> {bn.description}"
            if bn.suggestion:
                html += f"<br><small>→ {bn.suggestion}</small>"
            html += "</li>"
        html += "</ul>"

    html += "</body></html>"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


# ============================================================================
# `qoo profile flame` — Generate flame graph
# ============================================================================

@app.command("flame")
def profile_flame(
    data_file: str = typer.Argument(..., help="Path to profiling data JSON file"),
    output: str = typer.Option("flamegraph.json", "--output", "-o", help="Output flame graph JSON"),
    title: str = typer.Option("QooBot Skill Flame Graph", "--title", help="Graph title"),
):
    """Generate a flame graph from profiling data.

    Example:
        qoo profile flame profile_data.json -o flamegraph.json
    """
    with ErrorBoundary("profile flame", suggestion="Ensure the profiling data file is valid JSON"):
        data_path = Path(data_file).resolve()
        if not data_path.exists():
            console.print(f"[red]✗[/red] Data file not found: {data_path}")
            raise typer.Exit(1)

        with open(data_path) as f:
            data = json.load(f)

        builder = FlameGraphBuilder()
        flame_data = builder.build(data.get("call_stacks", []), title=title)

        output_path = Path(output).resolve()
        with open(output_path, "w") as f:
            json.dump(flame_data, f, indent=2)

        console.print(f"[green]✓[/green] Flame graph saved to: [bold]{output_path}[/bold]")
        console.print(f"  Nodes: {len(flame_data.get('nodes', []))}")


# ============================================================================
# `qoo profile comm` — Communication profiling
# ============================================================================

@app.command("comm")
def profile_comm(
    topics: str = typer.Option("", "--topics", "-t", help="Comma-separated topics to monitor"),
    duration: int = typer.Option(30, "--duration", "-d", help="Monitoring duration in seconds"),
    output: str = typer.Option("comm_report.json", "--output", "-o", help="Output report path"),
):
    """Profile DDS/ROS2 communication performance.

    Example:
        qoo profile comm --topics "/camera,/lidar,/cmd_vel" -d 60
    """
    with ErrorBoundary("profile comm", suggestion="Check that the DDS/ROS2 network is active"):
        topic_list = [t.strip() for t in topics.split(",") if t.strip()] if topics else []

        console.print(f"[cyan]Communication profiling[/cyan] for {duration}s...")
        if topic_list:
            console.print(f"[dim]Topics: {', '.join(topic_list)}[/dim]")

        profiler = CommunicationProfiler(topics=topic_list if topic_list else None)
        profiler.start()

        import time
        time.sleep(duration)

        profiler.stop()
        stats = profiler.get_stats()

        # Display results
        comm_table = Table(title="Communication Profile Results")
        comm_table.add_column("Topic", style="cyan")
        comm_table.add_column("Avg Lat (ms)", justify="right")
        comm_table.add_column("P99 Lat (ms)", justify="right")
        comm_table.add_column("BW (MB/s)", justify="right")
        comm_table.add_column("Drop %", justify="right")
        comm_table.add_column("Msgs", justify="right")

        for topic, s in stats.items():
            comm_table.add_row(
                topic,
                f"{s.get('avg_latency_ms', 0):.2f}",
                f"{s.get('p99_latency_ms', 0):.2f}",
                f"{s.get('bandwidth_mbps', 0):.2f}",
                f"{s.get('drop_rate_pct', 0):.2f}",
                str(s.get('message_count', 0)),
            )

        console.print(comm_table)

        # Save report
        output_path = Path(output).resolve()
        with open(output_path, "w") as f:
            json.dump(stats, f, indent=2, default=str)
        console.print(f"\n[dim]Report saved to: {output_path}[/dim]")


# ============================================================================
# `qoo profile model` — Model inference profiling
# ============================================================================

@app.command("model")
def profile_model(
    model_path: str = typer.Argument(..., help="Path to model file (.onnx, .pt, .qoomodel)"),
    iterations: int = typer.Option(100, "--iterations", "-n", help="Number of inference iterations"),
    warmup: int = typer.Option(10, "--warmup", "-w", help="Warmup iterations"),
    output: str = typer.Option("model_report.json", "--output", "-o", help="Output report path"),
):
    """Profile model inference performance.

    Example:
        qoo profile model model.onnx -n 500 -w 50
    """
    with ErrorBoundary("profile model", suggestion="Check that the model file exists and is valid"):
        model_file = Path(model_path).resolve()
        if not model_file.exists():
            console.print(f"[red]✗[/red] Model file not found: {model_file}")
            raise typer.Exit(1)

        console.print(f"[cyan]Profiling model:[/cyan] {model_file.name}")
        console.print(f"[dim]Iterations: {iterations} | Warmup: {warmup}[/dim]\n")

        profiler = ModelProfiler()
        result = profiler.profile(
            str(model_file),
            iterations=iterations,
            warmup=warmup,
        )

        # Display results
        model_table = Table(title="Model Inference Profile")
        model_table.add_column("Metric", style="cyan")
        model_table.add_column("Value", style="green")
        model_table.add_row("Model", model_file.name)
        model_table.add_row("Framework", result.get("framework", "unknown"))
        model_table.add_row("Avg Latency", f"{result.get('avg_latency_ms', 0):.2f} ms")
        model_table.add_row("P50 Latency", f"{result.get('p50_latency_ms', 0):.2f} ms")
        model_table.add_row("P99 Latency", f"{result.get('p99_latency_ms', 0):.2f} ms")
        model_table.add_row("Throughput", f"{result.get('throughput', 0):.1f} inf/s")
        model_table.add_row("Memory", f"{result.get('peak_memory_mb', 0):.1f} MB")
        console.print(model_table)

        # Layer-wise breakdown
        if result.get("layer_breakdown"):
            console.print("\n[bold]Layer-wise Latency (Top 10):[/bold]")
            layer_table = Table()
            layer_table.add_column("Layer", style="cyan")
            layer_table.add_column("Time (ms)", justify="right")
            layer_table.add_column("Memory (MB)", justify="right")
            layer_table.add_column("% of Total", justify="right")

            layers = sorted(result["layer_breakdown"], key=lambda x: x.get("time_ms", 0), reverse=True)[:10]
            total_time = sum(l.get("time_ms", 0) for l in result["layer_breakdown"])
            for layer in layers:
                pct = (layer.get("time_ms", 0) / total_time * 100) if total_time > 0 else 0
                layer_table.add_row(
                    layer.get("name", "unknown"),
                    f"{layer.get('time_ms', 0):.3f}",
                    f"{layer.get('memory_mb', 0):.2f}",
                    f"{pct:.1f}",
                )
            console.print(layer_table)

        # Save report
        output_path = Path(output).resolve()
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2, default=str)
        console.print(f"\n[dim]Report saved to: {output_path}[/dim]")


if __name__ == "__main__":
    app()
