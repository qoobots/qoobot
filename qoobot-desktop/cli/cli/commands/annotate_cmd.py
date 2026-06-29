"""
qoodev `qoo annotate` CLI commands — v1.5+
Data annotation tools for QooBot perception data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from qoodev.annotation import (
    AnnotationProject,
    Labeler2D,
    Labeler3D,
    TrajectoryLabeler,
    QualityReviewer,
    AnnotationType,
    LabelClass,
    BBox2D,
    BBox3D,
    AnnotationStats,
)
from qoodev.stability.error_handler import ErrorBoundary

app = typer.Typer(help="Data annotation and labeling tools", rich_markup_mode="rich")
console = Console()


# ============================================================================
# `qoo annotate create` — Create annotation project
# ============================================================================

@app.command("create")
def annotate_create(
    name: str = typer.Argument(..., help="Project name"),
    data_dir: str = typer.Option("", "--data", "-d", help="Path to data directory (images/pointclouds)"),
    annotation_type: str = typer.Option(
        "bbox_2d", "--type", "-t",
        help="Annotation type: bbox_2d, bbox_3d, keypoint, segmentation, semantic, trajectory"
    ),
    labels: str = typer.Option(
        "", "--labels", "-l",
        help="Comma-separated label classes, e.g. 'person,car,dog'"
    ),
    output: str = typer.Option("", "--output", "-o", help="Project output directory"),
):
    """Create a new annotation project.

    Example:
        qoo annotate create my_dataset -d ./data/images -t bbox_2d -l "person,car,robot"
    """
    with ErrorBoundary("annotate create", suggestion="Check that the data directory exists"):
        try:
            ann_type = AnnotationType(annotation_type)
        except ValueError:
            valid = ", ".join(a.value for a in AnnotationType)
            console.print(f"[red]✗[/red] Invalid annotation type: {annotation_type}")
            console.print(f"[dim]Valid types: {valid}[/dim]")
            raise typer.Exit(1)

        label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else []

        project_dir = Path(output).resolve() if output else Path.cwd() / name
        project_dir.mkdir(parents=True, exist_ok=True)

        project = AnnotationProject(
            name=name,
            project_dir=str(project_dir),
            annotation_type=ann_type,
        )

        # Set label classes
        if label_list:
            project.set_label_classes(label_list)

        # Import data if provided
        if data_dir:
            data_path = Path(data_dir).resolve()
            if not data_path.exists():
                console.print(f"[red]✗[/red] Data directory not found: {data_path}")
                raise typer.Exit(1)

            if ann_type in (AnnotationType.BBOX_3D,):
                project.add_pointclouds(str(data_path))
            else:
                project.add_images(str(data_path))

        # Save project
        project_path = project_dir / f"{name}.qooannot"
        project.save(str(project_path))

        console.print(f"[green]✓[/green] Annotation project created: [bold]{name}[/bold]")
        console.print(f"  Type: [cyan]{ann_type.value}[/cyan]")
        console.print(f"  Labels: [dim]{', '.join(label_list) if label_list else 'none defined'}[/dim]")
        console.print(f"  Data: [dim]{len(project.items)} items loaded[/dim]")
        console.print(f"  Project file: [dim]{project_path}[/dim]")


# ============================================================================
# `qoo annotate label` — Run annotation
# ============================================================================

@app.command("label")
def annotate_label(
    project_file: str = typer.Argument(..., help="Path to .qooannot project file"),
    mode: str = typer.Option("bbox", "--mode", "-m", help="Labeling mode: bbox, keypoint, seg, 3d, trajectory"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="Launch interactive labeling UI"),
    output: str = typer.Option("", "--output", "-o", help="Export annotations to this path"),
    export_format: str = typer.Option("coco", "--format", "-f", help="Export format: coco, yolo, qooannot"),
):
    """Label data in an annotation project.

    Example:
        qoo annotate label my_dataset.qooannot -m bbox -i
        qoo annotate label my_dataset.qooannot -m 3d -f coco -o output/
    """
    with ErrorBoundary("annotate label", suggestion="Check that the project file exists"):
        proj_path = Path(project_file).resolve()
        if not proj_path.exists():
            console.print(f"[red]✗[/red] Project file not found: {proj_path}")
            raise typer.Exit(1)

        project = AnnotationProject.load(str(proj_path))
        console.print(f"[cyan]Labeling project:[/cyan] {project.name}")
        console.print(f"  Type: [bold]{project.annotation_type.value}[/bold]")
        console.print(f"  Items: [dim]{len(project.items)}[/dim]")

        if interactive:
            console.print("\n[yellow]⚠ Interactive labeling UI not yet available.[/yellow]")
            console.print("[dim]Use programmatic API for batch labeling: qoodev.annotation.Labeler2D/Labeler3D[/dim]")
            return

        # Programmatic labeling
        if mode == "bbox":
            labeler = Labeler2D(project)
            stats = labeler.label_all()
        elif mode == "keypoint":
            labeler = Labeler2D(project)
            stats = labeler.label_keypoints()
        elif mode == "seg":
            labeler = Labeler2D(project)
            stats = labeler.label_segmentation()
        elif mode == "3d":
            labeler = Labeler3D(project)
            stats = labeler.label_all()
        elif mode == "trajectory":
            labeler = TrajectoryLabeler(project)
            stats = labeler.label_all()
        else:
            console.print(f"[red]✗[/red] Unknown labeling mode: {mode}")
            console.print("[dim]Valid modes: bbox, keypoint, seg, 3d, trajectory[/dim]")
            raise typer.Exit(1)

        console.print(f"\n[green]✓[/green] Labeling complete!")
        _display_labeling_stats(stats)

        # Save project
        project.save(str(proj_path))

        # Export if requested
        if output:
            export_path = Path(output).resolve()
            if export_format == "coco":
                result = project.export_coco(str(export_path))
            elif export_format == "yolo":
                result = project.export_yolo(str(export_path))
            else:
                result = project.export_qooannot(str(export_path))
            console.print(f"[green]✓[/green] Exported to: [bold]{export_path}[/bold]")


def _display_labeling_stats(stats) -> None:
    """Display labeling statistics."""
    if isinstance(stats, dict):
        table = Table(title="Labeling Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        for key, value in stats.items():
            table.add_row(key, str(value))
        console.print(table)


# ============================================================================
# `qoo annotate review` — Quality review
# ============================================================================

@app.command("review")
def annotate_review(
    project_file: str = typer.Argument(..., help="Path to .qooannot project file"),
    reference: Optional[str] = typer.Option(None, "--reference", "-r", help="Path to reference/ground-truth annotations"),
    min_iou: float = typer.Option(0.5, "--min-iou", help="Minimum IoU threshold for quality check"),
    output: str = typer.Option("review_report.json", "--output", "-o", help="Output report path"),
):
    """Review annotation quality and detect issues.

    Example:
        qoo annotate review my_dataset.qooannot -r ground_truth.json --min-iou 0.7
    """
    with ErrorBoundary("annotate review", suggestion="Check that the project and reference files exist"):
        proj_path = Path(project_file).resolve()
        if not proj_path.exists():
            console.print(f"[red]✗[/red] Project file not found: {proj_path}")
            raise typer.Exit(1)

        project = AnnotationProject.load(str(proj_path))
        reviewer = QualityReviewer(project, min_iou=min_iou)

        # Load reference annotations if provided
        reference_data = None
        if reference:
            ref_path = Path(reference).resolve()
            if not ref_path.exists():
                console.print(f"[yellow]⚠[/yellow] Reference file not found, skipping comparison: {ref_path}")
            else:
                with open(ref_path) as f:
                    reference_data = json.load(f)

        console.print(f"[cyan]Reviewing annotations:[/cyan] {project.name}")
        console.print(f"  Min IoU: [bold]{min_iou}[/bold]")

        report = reviewer.review(reference_data=reference_data)

        # Display results
        console.print(f"\n[bold]Review Summary:[/bold]")
        summary_table = Table(show_header=False)
        summary_table.add_column(style="cyan")
        summary_table.add_column()

        total = report.get("total_annotations", 0)
        passed = report.get("passed", 0)
        issues = report.get("issues_found", 0)

        pass_color = "green" if passed == total else ("yellow" if passed > total * 0.8 else "red")
        summary_table.add_row("Total Annotations", str(total))
        summary_table.add_row("Passed", f"[{pass_color}]{passed}[/{pass_color}]")
        summary_table.add_row("Issues Found", f"[{'red' if issues > 0 else 'green'}]{issues}[/{'red' if issues > 0 else 'green'}]")

        if reference_data:
            agreement = report.get("inter_annotator_agreement", 0) * 100
            summary_table.add_row("Agreement (vs ref)", f"{agreement:.1f}%")

        console.print(Panel(summary_table, border_style="cyan"))

        # Issue details
        if report.get("issues"):
            console.print("\n[bold red]Issues Detected:[/bold red]")
            for issue in report["issues"]:
                sev = issue.get("severity", "medium")
                color = {"critical": "red", "high": "yellow", "medium": "cyan", "low": "dim"}.get(sev, "white")
                console.print(
                    f"  [{color}]●[/{color}] [{color}]{sev.upper()}[/{color}] "
                    f"[bold]{issue.get('description', 'unknown')}[/bold]"
                )
                if issue.get("suggestion"):
                    console.print(f"    [dim]→ {issue['suggestion']}[/dim]")
        else:
            console.print("\n[green]✓ No issues found![/green]")

        # Save report
        output_path = Path(output).resolve()
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        console.print(f"\n[dim]Review report saved to: {output_path}[/dim]")


# ============================================================================
# `qoo annotate stats` — Annotation statistics
# ============================================================================

@app.command("stats")
def annotate_stats(
    project_file: str = typer.Argument(..., help="Path to .qooannot project file"),
    output: str = typer.Option("", "--output", "-o", help="Output stats JSON path"),
):
    """Display annotation project statistics.

    Example:
        qoo annotate stats my_dataset.qooannot
    """
    with ErrorBoundary("annotate stats", suggestion="Check that the project file exists"):
        proj_path = Path(project_file).resolve()
        if not proj_path.exists():
            console.print(f"[red]✗[/red] Project file not found: {proj_path}")
            raise typer.Exit(1)

        project = AnnotationProject.load(str(proj_path))
        stats = project.get_statistics()

        console.print(Panel(f"[bold]Annotation Statistics: {project.name}[/bold]", border_style="cyan"))

        # Overview
        overview = Table(title="Overview")
        overview.add_column("Metric", style="cyan")
        overview.add_column("Value", style="green")
        overview.add_row("Project Name", project.name)
        overview.add_row("Type", project.annotation_type.value)
        overview.add_row("Total Items", str(stats.total_items))
        overview.add_row("Annotated Items", str(stats.annotated_items))
        overview.add_row("Total Annotations", str(stats.total_annotations))
        overview.add_row("Completion", f"{stats.completion_rate:.1f}%")
        console.print(overview)

        # Label distribution
        if stats.label_distribution:
            console.print("\n[bold]Label Distribution:[/bold]")
            dist_table = Table()
            dist_table.add_column("Label", style="cyan")
            dist_table.add_column("Count", justify="right")
            dist_table.add_column("Percentage", justify="right")

            total = sum(stats.label_distribution.values())
            for label, count in sorted(stats.label_distribution.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total * 100) if total > 0 else 0
                dist_table.add_row(label, str(count), f"{pct:.1f}%")
            console.print(dist_table)

        # Size distribution (for bbox)
        if stats.bbox_size_distribution:
            console.print("\n[bold]BBox Size Distribution:[/bold]")
            size_table = Table()
            size_table.add_column("Category", style="cyan")
            size_table.add_column("Count", justify="right")
            for cat, count in stats.bbox_size_distribution.items():
                size_table.add_row(cat, str(count))
            console.print(size_table)

        if output:
            out_path = Path(output).resolve()
            with open(out_path, "w") as f:
                json.dump(stats.to_dict(), f, indent=2, default=str)
            console.print(f"\n[dim]Stats saved to: {out_path}[/dim]")


# ============================================================================
# `qoo annotate export` — Export annotations
# ============================================================================

@app.command("export")
def annotate_export(
    project_file: str = typer.Argument(..., help="Path to .qooannot project file"),
    output: str = typer.Option("", "--output", "-o", help="Output directory or file"),
    fmt: str = typer.Option("coco", "--format", "-f", help="Export format: coco, yolo, qooannot"),
    split: bool = typer.Option(False, "--split", help="Create train/val/test split"),
    train_ratio: float = typer.Option(0.7, "--train-ratio", help="Training set ratio (if --split)"),
    val_ratio: float = typer.Option(0.15, "--val-ratio", help="Validation set ratio (if --split)"),
):
    """Export annotations to standard formats.

    Example:
        qoo annotate export my_dataset.qooannot -f coco -o ./output --split
    """
    with ErrorBoundary("annotate export", suggestion="Check that the project file exists"):
        proj_path = Path(project_file).resolve()
        if not proj_path.exists():
            console.print(f"[red]✗[/red] Project file not found: {proj_path}")
            raise typer.Exit(1)

        project = AnnotationProject.load(str(proj_path))
        output_path = Path(output).resolve() if output else Path.cwd() / f"{project.name}_export"

        console.print(f"[cyan]Exporting annotations:[/cyan] {project.name}")
        console.print(f"  Format: [bold]{fmt.upper()}[/bold]")
        console.print(f"  Output: [dim]{output_path}[/dim]")

        if split:
            console.print(f"  Split: train={train_ratio:.0%} val={val_ratio:.0%} test={(1-train_ratio-val_ratio):.0%}")

        if fmt == "coco":
            result = project.export_coco(str(output_path), split=split, train_ratio=train_ratio, val_ratio=val_ratio)
        elif fmt == "yolo":
            result = project.export_yolo(str(output_path), split=split, train_ratio=train_ratio, val_ratio=val_ratio)
        elif fmt == "qooannot":
            result = project.export_qooannot(str(output_path))
        else:
            console.print(f"[red]✗[/red] Unsupported format: {fmt}")
            console.print("[dim]Valid formats: coco, yolo, qooannot[/dim]")
            raise typer.Exit(1)

        console.print(f"\n[green]✓[/green] Export complete!")
        if isinstance(result, dict):
            for key, val in result.items():
                console.print(f"  [dim]{key}:[/dim] {val}")


# ============================================================================
# `qoo annotate import` — Import annotations
# ============================================================================

@app.command("import")
def annotate_import(
    source: str = typer.Argument(..., help="Path to annotation file (COCO JSON, YOLO, etc.)"),
    fmt: str = typer.Option("coco", "--format", "-f", help="Source format: coco, yolo"),
    output: str = typer.Option("", "--output", "-o", help="Output .qooannot project file"),
    name: str = typer.Option("", "--name", "-n", help="Project name (auto from file if empty)"),
):
    """Import annotations from external formats.

    Example:
        qoo annotate import coco_annotations.json -f coco -o my_project.qooannot
    """
    with ErrorBoundary("annotate import", suggestion="Check that the source file exists"):
        src_path = Path(source).resolve()
        if not src_path.exists():
            console.print(f"[red]✗[/red] Source file not found: {src_path}")
            raise typer.Exit(1)

        project_name = name or src_path.stem

        console.print(f"[cyan]Importing annotations:[/cyan] {src_path.name}")
        console.print(f"  Format: [bold]{fmt.upper()}[/bold]")

        project = AnnotationProject(name=project_name)

        if fmt == "coco":
            project.import_coco(str(src_path))
        elif fmt == "yolo":
            project.import_yolo(str(src_path))
        else:
            console.print(f"[red]✗[/red] Unsupported import format: {fmt}")
            console.print("[dim]Valid formats: coco, yolo[/dim]")
            raise typer.Exit(1)

        output_path = Path(output).resolve() if output else src_path.with_suffix(".qooannot")
        project.save(str(output_path))

        console.print(f"\n[green]✓[/green] Import complete!")
        console.print(f"  Project: [bold]{project.name}[/bold]")
        console.print(f"  Items: [dim]{len(project.items)}[/dim]")
        console.print(f"  Saved to: [dim]{output_path}[/dim]")


if __name__ == "__main__":
    app()
