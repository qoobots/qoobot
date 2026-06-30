"""
Data Management — v1.6+

Dataset version management, data cleaning, and quality reporting for QooBot
robot perception and control data.

Features:
- Dataset versioning (Git-like snapshot with metadata)
- Data cleaning (outlier detection, deduplication, format validation)
- Quality reports (completeness, distribution, bias analysis)
- Data splitting (train/val/test with stratification)
- Dataset comparison (diff two versions)
- Export to common formats (COCO, KITTI, YOLO, ROS2 bag)

Usage:
    from cli.data_management import DataManager

    dm = DataManager("my_dataset")
    dm.version("v1.0", message="Initial training set")
    dm.clean(remove_outliers=True, deduplicate=True)
    dm.quality_report()
    dm.split(train_ratio=0.7, val_ratio=0.15, test_ratio=0.15)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import numpy as np
import yaml

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.tree import Tree

console = Console()


# ============================================================================
# Data Models
# ============================================================================

class DataType(Enum):
    IMAGE = "image"
    POINT_CLOUD = "point_cloud"
    TRAJECTORY = "trajectory"
    AUDIO = "audio"
    TEXT = "text"
    SENSOR = "sensor"
    ANNOTATION = "annotation"
    CALIBRATION = "calibration"


class AnnotationFormat(Enum):
    COCO = "coco"
    YOLO = "yolo"
    KITTI = "kitti"
    QOOBOT = "qoobot"
    CUSTOM = "custom"


class SplitStrategy(Enum):
    RANDOM = "random"
    STRATIFIED = "stratified"
    TEMPORAL = "temporal"
    SCENE_BASED = "scene_based"


@dataclass
class DatasetMeta:
    """Dataset metadata."""
    name: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: str = "0.0.0"
    description: str = ""
    data_types: List[DataType] = field(default_factory=list)
    total_samples: int = 0
    total_size_bytes: int = 0
    annotation_format: AnnotationFormat = AnnotationFormat.QOOBOT
    tags: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    license: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
            "description": self.description,
            "data_types": [dt.value for dt in self.data_types],
            "total_samples": self.total_samples,
            "total_size_bytes": self.total_size_bytes,
            "annotation_format": self.annotation_format.value,
            "tags": self.tags,
            "sources": self.sources,
            "license": self.license,
        }


@dataclass
class DataSample:
    """A single data sample."""
    id: str
    file_path: Path
    data_type: DataType
    size_bytes: int = 0
    hash_sha256: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    quality_score: float = 1.0
    tags: List[str] = field(default_factory=list)


@dataclass
class DatasetVersion:
    """A version snapshot of the dataset."""
    version: str
    message: str
    created_at: str
    parent_version: str = ""
    sample_count: int = 0
    sample_ids: List[str] = field(default_factory=list)
    checksum: str = ""


@dataclass
class QualityReport:
    """Dataset quality assessment report."""
    dataset_name: str
    version: str
    total_samples: int
    total_size_bytes: int

    # Completeness
    missing_files: int = 0
    missing_annotations: int = 0
    corrupted_files: int = 0
    completeness_score: float = 1.0

    # Distribution
    class_distribution: Dict[str, int] = field(default_factory=dict)
    data_type_distribution: Dict[str, int] = field(default_factory=dict)

    # Quality
    low_quality_samples: int = 0
    duplicate_samples: int = 0
    outlier_samples: int = 0
    quality_score: float = 1.0

    # Bias
    class_imbalance_ratio: float = 0.0
    potential_biases: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "dataset_name": self.dataset_name,
            "version": self.version,
            "total_samples": self.total_samples,
            "total_size_bytes": self.total_size_bytes,
            "missing_files": self.missing_files,
            "missing_annotations": self.missing_annotations,
            "corrupted_files": self.corrupted_files,
            "completeness_score": self.completeness_score,
            "class_distribution": self.class_distribution,
            "data_type_distribution": self.data_type_distribution,
            "low_quality_samples": self.low_quality_samples,
            "duplicate_samples": self.duplicate_samples,
            "outlier_samples": self.outlier_samples,
            "quality_score": self.quality_score,
            "class_imbalance_ratio": self.class_imbalance_ratio,
            "potential_biases": self.potential_biases,
        }


# ============================================================================
# Data Manager
# ============================================================================

class DataManager:
    """Dataset version management, cleaning, and quality reporting.

    Manages the complete lifecycle of robot perception datasets:
    1. Create/load dataset
    2. Add/remove samples
    3. Version snapshot
    4. Clean (deduplicate, remove outliers, validate)
    5. Quality report generation
    6. Train/val/test split
    7. Export to standard formats
    """

    _SUPPORTED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    _SUPPORTED_POINTCLOUD_EXT = {".pcd", ".ply", ".bin", ".npy", ".npz", ".las", ".laz"}
    _SUPPORTED_ANNOTATION_EXT = {".json", ".yaml", ".yml", ".xml", ".txt"}
    _SUPPORTED_TRAJECTORY_EXT = {".csv", ".json", ".bag"}

    def __init__(self, dataset_path: str, create: bool = False):
        self.root = Path(dataset_path)
        self._samples: Dict[str, DataSample] = {}
        self._versions: List[DatasetVersion] = []
        self._meta: Optional[DatasetMeta] = None

        if create:
            self._init_new_dataset()
        else:
            self._load_existing()

    # ── Dataset Initialization ──────────────────────────────────────────────

    def _init_new_dataset(self) -> None:
        """Initialize a new dataset directory structure."""
        self.root.mkdir(parents=True, exist_ok=True)

        # Create standard directories
        dirs = ["images", "pointclouds", "trajectories", "annotations", "calibrations", ".versions"]
        for d in dirs:
            (self.root / d).mkdir(exist_ok=True)

        self._meta = DatasetMeta(name=self.root.name)
        self._save_meta()
        console.print(f"[green]✓[/green] Created new dataset: [bold]{self.root.name}[/bold]")

    def _load_existing(self) -> None:
        """Load an existing dataset."""
        meta_path = self.root / "dataset.yaml"
        if meta_path.exists():
            data = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            self._meta = DatasetMeta(
                name=data.get("name", self.root.name),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
                version=data.get("version", "0.0.0"),
                description=data.get("description", ""),
                data_types=[DataType(dt) for dt in data.get("data_types", [])],
                total_samples=data.get("total_samples", 0),
                total_size_bytes=data.get("total_size_bytes", 0),
                annotation_format=AnnotationFormat(data.get("annotation_format", "qoobot")),
                tags=data.get("tags", []),
                sources=data.get("sources", []),
                license=data.get("license", ""),
            )
            console.print(f"[green]✓[/green] Loaded dataset: [bold]{self._meta.name}[/bold] v{self._meta.version}")

        # Load versions
        versions_dir = self.root / ".versions"
        if versions_dir.exists():
            for vf in sorted(versions_dir.glob("*.json")):
                vdata = json.loads(vf.read_text(encoding="utf-8"))
                self._versions.append(DatasetVersion(**vdata))

        # Index samples
        self._index_samples()

    def _save_meta(self) -> None:
        """Save dataset metadata."""
        if self._meta:
            meta_path = self.root / "dataset.yaml"
            meta_path.write_text(
                yaml.dump(self._meta.to_dict(), default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )

    # ── Sample Management ──────────────────────────────────────────────────

    def _index_samples(self) -> None:
        """Index all data samples in the dataset directory."""
        self._samples.clear()

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Indexing samples...", total=None)

            for dt, extensions, dir_name in [
                (DataType.IMAGE, self._SUPPORTED_IMAGE_EXT, "images"),
                (DataType.POINT_CLOUD, self._SUPPORTED_POINTCLOUD_EXT, "pointclouds"),
                (DataType.TRAJECTORY, self._SUPPORTED_TRAJECTORY_EXT, "trajectories"),
                (DataType.ANNOTATION, self._SUPPORTED_ANNOTATION_EXT, "annotations"),
            ]:
                data_dir = self.root / dir_name
                if not data_dir.exists():
                    continue

                for file_path in data_dir.rglob("*"):
                    if file_path.suffix.lower() in extensions:
                        sample_id = str(file_path.relative_to(self.root))
                        size = file_path.stat().st_size
                        sha = self._compute_hash(file_path)
                        self._samples[sample_id] = DataSample(
                            id=sample_id,
                            file_path=file_path,
                            data_type=dt,
                            size_bytes=size,
                            hash_sha256=sha,
                        )

        if self._meta:
            self._meta.total_samples = len(self._samples)
            self._meta.total_size_bytes = sum(s.size_bytes for s in self._samples.values())
            self._save_meta()

        console.print(f"  [dim]Indexed {len(self._samples)} samples[/dim]")

    def add_samples(self, source_dir: str, data_type: Optional[DataType] = None) -> int:
        """Add samples from a directory."""
        src = Path(source_dir)
        if not src.exists():
            raise FileNotFoundError(f"Source directory not found: {src}")

        added = 0
        for file_path in src.rglob("*"):
            if not file_path.is_file():
                continue

            ext = file_path.suffix.lower()
            if data_type is None:
                if ext in self._SUPPORTED_IMAGE_EXT:
                    dt = DataType.IMAGE
                    dest_dir = self.root / "images"
                elif ext in self._SUPPORTED_POINTCLOUD_EXT:
                    dt = DataType.POINT_CLOUD
                    dest_dir = self.root / "pointclouds"
                elif ext in self._SUPPORTED_TRAJECTORY_EXT:
                    dt = DataType.TRAJECTORY
                    dest_dir = self.root / "trajectories"
                elif ext in self._SUPPORTED_ANNOTATION_EXT:
                    dt = DataType.ANNOTATION
                    dest_dir = self.root / "annotations"
                else:
                    continue
            else:
                dt = data_type
                dest_dir = self.root / dt.value + "s"

            dest_dir.mkdir(exist_ok=True)
            dest = dest_dir / file_path.name
            if not dest.exists():
                shutil.copy2(file_path, dest)
                added += 1

        self._index_samples()
        console.print(f"[green]✓[/green] Added [bold]{added}[/bold] samples")
        return added

    def remove_sample(self, sample_id: str) -> bool:
        """Remove a sample from the dataset."""
        if sample_id not in self._samples:
            return False

        sample = self._samples[sample_id]
        if sample.file_path.exists():
            sample.file_path.unlink()

        del self._samples[sample_id]
        self._save_meta()
        return True

    # ── Versioning ──────────────────────────────────────────────────────────

    def version(self, version_tag: str, message: str = "") -> DatasetVersion:
        """Create a version snapshot of the current dataset state."""
        if not self._meta:
            raise RuntimeError("Dataset not initialized")

        # Compute checksum
        sample_ids = sorted(self._samples.keys())
        checksum = hashlib.sha256(
            "".join(sample_ids).encode()
        ).hexdigest()[:16]

        parent = self._versions[-1].version if self._versions else ""

        dv = DatasetVersion(
            version=version_tag,
            message=message,
            created_at=datetime.now(timezone.utc).isoformat(),
            parent_version=parent,
            sample_count=len(sample_ids),
            sample_ids=sample_ids,
            checksum=checksum,
        )

        # Save version file
        versions_dir = self.root / ".versions"
        versions_dir.mkdir(exist_ok=True)
        vf = versions_dir / f"{version_tag}.json"
        vf.write_text(json.dumps({
            "version": dv.version,
            "message": dv.message,
            "created_at": dv.created_at,
            "parent_version": dv.parent_version,
            "sample_count": dv.sample_count,
            "sample_ids": dv.sample_ids,
            "checksum": dv.checksum,
        }, indent=2), encoding="utf-8")

        self._versions.append(dv)
        self._meta.version = version_tag
        self._meta.updated_at = dv.created_at
        self._save_meta()

        console.print(Panel.fit(
            f"[bold green]✓ Version Created[/bold green]\n"
            f"Tag: [cyan]{version_tag}[/cyan]  "
            f"Samples: {dv.sample_count}  "
            f"Checksum: [dim]{checksum}[/dim]\n"
            f"[dim]{message}[/dim]" if message else "",
            border_style="green",
        ))
        return dv

    def list_versions(self) -> Table:
        """List all dataset versions."""
        table = Table(title=f"Dataset Versions — {self.root.name}")
        table.add_column("Version", style="cyan")
        table.add_column("Date", style="dim")
        table.add_column("Samples")
        table.add_column("Parent")
        table.add_column("Checksum", style="dim")
        table.add_column("Message")

        for dv in self._versions:
            table.add_row(
                dv.version,
                dv.created_at[:19],
                str(dv.sample_count),
                dv.parent_version or "—",
                dv.checksum,
                dv.message or "—",
            )

        console.print(table)
        return table

    def diff_versions(self, v1: str, v2: str) -> dict:
        """Compute diff between two versions."""
        ver1 = next((v for v in self._versions if v.version == v1), None)
        ver2 = next((v for v in self._versions if v.version == v2), None)

        if not ver1 or not ver2:
            raise ValueError(f"Version not found: {v1 if not ver1 else v2}")

        ids1 = set(ver1.sample_ids)
        ids2 = set(ver2.sample_ids)

        diff = {
            "v1": v1, "v2": v2,
            "added": sorted(ids2 - ids1),
            "removed": sorted(ids1 - ids2),
            "unchanged": sorted(ids1 & ids2),
            "added_count": len(ids2 - ids1),
            "removed_count": len(ids1 - ids2),
            "unchanged_count": len(ids1 & ids2),
        }

        table = Table(title=f"Diff: {v1} → {v2}")
        table.add_column("Change", style="cyan")
        table.add_column("Count", style="bold")

        table.add_row("[green]+ Added[/green]", str(diff["added_count"]))
        table.add_row("[red]- Removed[/red]", str(diff["removed_count"]))
        table.add_row("[dim]= Unchanged[/dim]", str(diff["unchanged_count"]))

        console.print(table)
        return diff

    # ── Data Cleaning ──────────────────────────────────────────────────────

    def clean(
        self,
        remove_duplicates: bool = True,
        remove_outliers: bool = True,
        remove_corrupted: bool = True,
        validate_annotations: bool = True,
        dry_run: bool = False,
    ) -> Dict[str, int]:
        """Clean the dataset by removing problematic samples.

        Args:
            remove_duplicates: Remove exact duplicates (same hash)
            remove_outliers: Remove statistical outliers
            remove_corrupted: Remove corrupted/unreadable files
            validate_annotations: Validate annotation format
            dry_run: If True, only report what would be removed

        Returns:
            Dictionary with counts of removed samples by category.
        """
        results = {"duplicates": 0, "outliers": 0, "corrupted": 0, "invalid_annotations": 0}
        to_remove: Set[str] = set()

        # Detect duplicates
        if remove_duplicates:
            hash_map: Dict[str, str] = {}
            for sid, sample in self._samples.items():
                if sample.hash_sha256 in hash_map:
                    to_remove.add(sid)
                    results["duplicates"] += 1
                else:
                    hash_map[sample.hash_sha256] = sid

        # Detect corrupted files
        if remove_corrupted:
            for sid, sample in self._samples.items():
                if sample.data_type == DataType.IMAGE:
                    if not self._is_image_valid(sample.file_path):
                        to_remove.add(sid)
                        results["corrupted"] += 1
                elif sample.data_type == DataType.ANNOTATION:
                    if not self._is_annotation_valid(sample.file_path):
                        to_remove.add(sid)
                        results["invalid_annotations"] += 1

        # Detect outliers (file size based)
        if remove_outliers:
            sizes = [s.size_bytes for s in self._samples.values() if s.id not in to_remove]
            if sizes:
                mean = np.mean(sizes)
                std = np.std(sizes)
                threshold = 3.0 * std

                for sid, sample in self._samples.items():
                    if sid in to_remove:
                        continue
                    if abs(sample.size_bytes - mean) > threshold:
                        to_remove.add(sid)
                        results["outliers"] += 1

        # Execute removal
        if not dry_run:
            for sid in to_remove:
                self.remove_sample(sid)
            self._index_samples()

        # Report
        total = sum(results.values())
        action = "Would remove" if dry_run else "Removed"

        table = Table(title=f"Data Cleaning Results ({action})")
        table.add_column("Category", style="cyan")
        table.add_column("Count", style="bold")

        for cat, count in results.items():
            if count > 0:
                table.add_row(cat.replace("_", " ").title(), str(count))

        table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]")

        console.print(table)
        return results

    def _is_image_valid(self, path: Path) -> bool:
        """Check if an image file is valid."""
        try:
            from PIL import Image
            with Image.open(path) as img:
                img.verify()
            return True
        except Exception:
            return False

    def _is_annotation_valid(self, path: Path) -> bool:
        """Check if an annotation file is valid JSON/YAML."""
        try:
            if path.suffix in (".json",):
                json.loads(path.read_text(encoding="utf-8"))
            elif path.suffix in (".yaml", ".yml"):
                yaml.safe_load(path.read_text(encoding="utf-8"))
            return True
        except Exception:
            return False

    # ── Quality Report ─────────────────────────────────────────────────────

    def quality_report(self) -> QualityReport:
        """Generate a comprehensive quality assessment report."""
        if not self._samples:
            console.print("[yellow]⚠[/yellow] No samples in dataset")
            return QualityReport(
                dataset_name=self.root.name,
                version=self._meta.version if self._meta else "0.0.0",
                total_samples=0,
                total_size_bytes=0,
            )

        total = len(self._samples)
        total_size = sum(s.size_bytes for s in self._samples.values())

        # Check missing files
        missing = sum(1 for s in self._samples.values() if not s.file_path.exists())
        corrupted = sum(
            1 for s in self._samples.values()
            if s.data_type == DataType.IMAGE and s.file_path.exists() and not self._is_image_valid(s.file_path)
        )

        # Class distribution
        class_dist: Dict[str, int] = defaultdict(int)
        for s in self._samples.values():
            for ann in s.annotations:
                cls = ann.get("category", ann.get("class", "unknown"))
                class_dist[cls] += 1

        # Data type distribution
        type_dist = Counter(s.data_type.value for s in self._samples.values())

        # Quality scores
        low_quality = sum(1 for s in self._samples.values() if s.quality_score < 0.5)

        # Completeness
        completeness = 1.0 - (missing + corrupted) / max(total, 1)

        # Class imbalance
        if class_dist:
            counts = list(class_dist.values())
            class_imbalance = max(counts) / (sum(counts) / len(counts)) if counts else 0
        else:
            class_imbalance = 0

        # Potential biases
        biases = []
        if class_imbalance > 5:
            biases.append(f"Severe class imbalance (ratio: {class_imbalance:.1f}x)")
        if missing > 0:
            biases.append(f"{missing} missing files detected")
        if low_quality > total * 0.1:
            biases.append(f"{low_quality} low-quality samples ({low_quality/total:.1%})")

        report = QualityReport(
            dataset_name=self.root.name,
            version=self._meta.version if self._meta else "0.0.0",
            total_samples=total,
            total_size_bytes=total_size,
            missing_files=missing,
            corrupted_files=corrupted,
            completeness_score=completeness,
            class_distribution=dict(class_dist),
            data_type_distribution=dict(type_dist),
            low_quality_samples=low_quality,
            quality_score=1.0 - low_quality / max(total, 1),
            class_imbalance_ratio=class_imbalance,
            potential_biases=biases,
        )

        self._print_quality_report(report)
        return report

    def _print_quality_report(self, report: QualityReport) -> None:
        """Print quality report in a formatted panel."""
        # Overall score
        score = (report.completeness_score + report.quality_score) / 2
        if score >= 0.9:
            score_color = "green"
            score_label = "Excellent"
        elif score >= 0.7:
            score_color = "yellow"
            score_label = "Good"
        elif score >= 0.5:
            score_color = "yellow"
            score_label = "Fair"
        else:
            score_color = "red"
            score_label = "Poor"

        console.print(Panel.fit(
            f"[bold {score_color}]Quality Score: {score:.1%} — {score_label}[/bold {score_color}]\n\n"
            f"Completeness: {report.completeness_score:.1%}  |  "
            f"Quality: {report.quality_score:.1%}",
            title=f"📊 Quality Report — {report.dataset_name} v{report.version}",
            border_style=score_color,
        ))

        # Stats table
        stats = Table(show_header=False, box=None, padding=(0, 1))
        stats.add_column(style="bold cyan")
        stats.add_column()

        size_mb = report.total_size_bytes / (1024 * 1024)
        stats.add_row("Total Samples", str(report.total_samples))
        stats.add_row("Total Size", f"{size_mb:.1f} MB")
        stats.add_row("Missing Files", f"[red]{report.missing_files}[/red]" if report.missing_files else "0")
        stats.add_row("Corrupted Files", f"[red]{report.corrupted_files}[/red]" if report.corrupted_files else "0")
        stats.add_row("Low Quality", f"[yellow]{report.low_quality_samples}[/yellow]" if report.low_quality_samples else "0")
        stats.add_row("Class Imbalance", f"{report.class_imbalance_ratio:.2f}x" if report.class_imbalance_ratio else "N/A")
        console.print(stats)

        # Class distribution
        if report.class_distribution:
            dist_table = Table(title="Class Distribution")
            dist_table.add_column("Class", style="cyan")
            dist_table.add_column("Count", style="bold")
            dist_table.add_column("Percentage")

            total = report.total_samples
            for cls, count in sorted(report.class_distribution.items(), key=lambda x: -x[1])[:20]:
                dist_table.add_row(cls, str(count), f"{count/total:.1%}")

            console.print(dist_table)

        # Warnings
        if report.potential_biases:
            console.print("\n[bold yellow]⚠ Potential Issues:[/bold yellow]")
            for bias in report.potential_biases:
                console.print(f"  [yellow]•[/yellow] {bias}")

    # ── Data Splitting ─────────────────────────────────────────────────────

    def split(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        strategy: SplitStrategy = SplitStrategy.RANDOM,
        seed: int = 42,
    ) -> Dict[str, List[str]]:
        """Split dataset into train/val/test sets.

        Args:
            train_ratio: Proportion for training set
            val_ratio: Proportion for validation set
            test_ratio: Proportion for test set
            strategy: Splitting strategy
            seed: Random seed for reproducibility

        Returns:
            Dictionary with 'train', 'val', 'test' keys mapping to sample ID lists.
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.001, "Ratios must sum to 1.0"

        rng = np.random.RandomState(seed)
        sample_ids = list(self._samples.keys())
        n = len(sample_ids)

        if strategy == SplitStrategy.RANDOM:
            indices = rng.permutation(n)
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)

            splits = {
                "train": [sample_ids[i] for i in indices[:train_end]],
                "val": [sample_ids[i] for i in indices[train_end:val_end]],
                "test": [sample_ids[i] for i in indices[val_end:]],
            }

        elif strategy == SplitStrategy.STRATIFIED:
            # Stratify by class
            class_samples: Dict[str, List[str]] = defaultdict(list)
            for sid, sample in self._samples.items():
                for ann in sample.annotations:
                    cls = ann.get("category", ann.get("class", "unknown"))
                    class_samples[cls].append(sid)
                    break  # Use first annotation class

            splits = {"train": [], "val": [], "test": []}
            for cls, ids in class_samples.items():
                indices = rng.permutation(len(ids))
                train_end = int(len(ids) * train_ratio)
                val_end = train_end + int(len(ids) * val_ratio)

                splits["train"].extend(ids[i] for i in indices[:train_end])
                splits["val"].extend(ids[i] for i in indices[train_end:val_end])
                splits["test"].extend(ids[i] for i in indices[val_end:])

        elif strategy == SplitStrategy.TEMPORAL:
            # Sort by timestamp and split chronologically
            sorted_ids = sorted(sample_ids, key=lambda sid: self._samples[sid].metadata.get("timestamp", ""))
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)

            splits = {
                "train": sorted_ids[:train_end],
                "val": sorted_ids[train_end:val_end],
                "test": sorted_ids[val_end:],
            }

        else:
            splits = {"train": sample_ids, "val": [], "test": []}

        # Save split files
        splits_dir = self.root / "splits"
        splits_dir.mkdir(exist_ok=True)
        for name, ids in splits.items():
            (splits_dir / f"{name}.txt").write_text("\n".join(ids), encoding="utf-8")

        # Report
        table = Table(title=f"Dataset Split — {strategy.value}")
        table.add_column("Set", style="cyan")
        table.add_column("Samples", style="bold")
        table.add_column("Percentage")

        for name, ids in splits.items():
            table.add_row(name.title(), str(len(ids)), f"{len(ids)/n:.1%}")

        console.print(table)
        return splits

    # ── Export ──────────────────────────────────────────────────────────────

    def export_coco(self, output_path: str) -> Path:
        """Export dataset to COCO JSON format."""
        images = []
        annotations = []
        categories = []
        cat_name_to_id: Dict[str, int] = {}
        ann_id = 0

        for i, (sid, sample) in enumerate(self._samples.items()):
            if sample.data_type != DataType.IMAGE:
                continue

            images.append({
                "id": i,
                "file_name": str(sample.file_path.relative_to(self.root)),
                "width": sample.metadata.get("width", 0),
                "height": sample.metadata.get("height", 0),
            })

            for ann in sample.annotations:
                cat_name = ann.get("category", "unknown")
                if cat_name not in cat_name_to_id:
                    cat_id = len(categories)
                    cat_name_to_id[cat_name] = cat_id
                    categories.append({"id": cat_id, "name": cat_name, "supercategory": "object"})

                annotations.append({
                    "id": ann_id,
                    "image_id": i,
                    "category_id": cat_name_to_id[cat_name],
                    "bbox": ann.get("bbox", [0, 0, 0, 0]),
                    "area": ann.get("area", 0),
                    "iscrowd": ann.get("iscrowd", 0),
                })
                ann_id += 1

        coco = {
            "images": images,
            "annotations": annotations,
            "categories": categories,
        }

        output = Path(output_path)
        output.write_text(json.dumps(coco, indent=2), encoding="utf-8")
        console.print(f"[green]✓[/green] Exported COCO format to: [bold]{output}[/bold]")
        return output

    def export_yolo(self, output_dir: str) -> Path:
        """Export dataset to YOLO format."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "images").mkdir(exist_ok=True)
        (out / "labels").mkdir(exist_ok=True)

        # Build class mapping
        class_names: List[str] = []
        class_to_id: Dict[str, int] = {}

        for sample in self._samples.values():
            for ann in sample.annotations:
                cls = ann.get("category", "unknown")
                if cls not in class_to_id:
                    class_to_id[cls] = len(class_names)
                    class_names.append(cls)

        # Export labels
        exported = 0
        for sample in self._samples.values():
            if sample.data_type != DataType.IMAGE:
                continue

            # Copy image
            img_dest = out / "images" / sample.file_path.name
            if sample.file_path.exists() and not img_dest.exists():
                shutil.copy2(sample.file_path, img_dest)

            # Write YOLO label
            stem = sample.file_path.stem
            label_path = out / "labels" / f"{stem}.txt"
            lines = []
            img_w = sample.metadata.get("width", 1)
            img_h = sample.metadata.get("height", 1)

            for ann in sample.annotations:
                cls_id = class_to_id.get(ann.get("category", "unknown"), 0)
                bbox = ann.get("bbox", [0, 0, 0, 0])
                # COCO bbox to YOLO normalized format
                x_center = (bbox[0] + bbox[2] / 2) / img_w
                y_center = (bbox[1] + bbox[3] / 2) / img_h
                width = bbox[2] / img_w
                height = bbox[3] / img_h
                lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

            label_path.write_text("\n".join(lines), encoding="utf-8")
            exported += 1

        # Write data.yaml
        data_yaml = {
            "path": str(out.resolve()),
            "train": "images",
            "val": "images",
            "nc": len(class_names),
            "names": class_names,
        }
        (out / "data.yaml").write_text(yaml.dump(data_yaml, default_flow_style=False), encoding="utf-8")

        console.print(f"[green]✓[/green] Exported YOLO format ({exported} samples) to: [bold]{out}[/bold]")
        return out

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _compute_hash(self, path: Path) -> str:
        """Compute SHA-256 hash of a file."""
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return sha.hexdigest()

    def summary(self) -> Table:
        """Print dataset summary."""
        if not self._meta:
            console.print("[dim]No dataset loaded[/dim]")
            return Table()

        table = Table(title=f"📦 {self._meta.name} v{self._meta.version}")
        table.add_column("Property", style="bold cyan")
        table.add_column("Value")

        table.add_row("Samples", str(len(self._samples)))
        table.add_row("Size", f"{self._meta.total_size_bytes / (1024*1024):.1f} MB")
        table.add_row("Versions", str(len(self._versions)))
        table.add_row("Data Types", ", ".join(dt.value for dt in self._meta.data_types))
        table.add_row("Tags", ", ".join(self._meta.tags) if self._meta.tags else "—")
        table.add_row("Created", self._meta.created_at[:19])
        table.add_row("Updated", self._meta.updated_at[:19])

        console.print(table)
        return table
