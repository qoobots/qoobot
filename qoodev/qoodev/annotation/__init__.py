"""
qoodev Data Annotation Toolkit — v1.5+

Tools for annotating robot perception data:
- 2D annotation: bounding boxes, keypoints, segmentation masks
- 3D annotation: point cloud labeling, 3D bounding boxes
- Semantic segmentation: per-pixel/pixel-group labeling
- Trajectory annotation: action labeling on recorded trajectories
- Quality review: annotation consistency check, inter-annotator agreement

Usage:
    from qoodev.annotation import (
        AnnotationProject, Labeler2D, Labeler3D, TrajectoryLabeler
    )

    project = AnnotationProject("my_dataset")
    project.add_images("data/images/")
    labeler = Labeler2D(project)
    labeler.annotate_bboxes()
"""

from __future__ import annotations

import dataclasses
import json
import os
import uuid
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# ============================================================================
# Data Models
# ============================================================================

class AnnotationType(Enum):
    BBOX_2D = "bbox_2d"
    BBOX_3D = "bbox_3d"
    KEYPOINT = "keypoint"
    SEGMENTATION = "segmentation"
    SEMANTIC = "semantic"
    INSTANCE = "instance"
    PANOPTIC = "panoptic"
    TRAJECTORY = "trajectory"
    TEXT = "text"


class LabelClass(Enum):
    """Common robot perception label classes."""
    PERSON = "person"
    ROBOT = "robot"
    HAND = "hand"
    OBJECT = "object"
    TOOL = "tool"
    FURNITURE = "furniture"
    DOOR = "door"
    WALL = "wall"
    FLOOR = "floor"
    TABLE = "table"
    CHAIR = "chair"
    CUP = "cup"
    BOTTLE = "bottle"
    FOOD = "food"
    ELECTRONICS = "electronics"
    OBSTACLE = "obstacle"
    PATH = "path"
    UNKNOWN = "unknown"


@dataclasses.dataclass
class Point2D:
    x: float
    y: float

    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y}


@dataclasses.dataclass
class Point3D:
    x: float
    y: float
    z: float

    def to_dict(self) -> Dict:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclasses.dataclass
class BBox2D:
    """2D bounding box annotation."""
    x: float
    y: float
    width: float
    height: float
    label: str
    confidence: float = 1.0
    attributes: Dict[str, str] = dataclasses.field(default_factory=dict)

    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> Dict:
        return {
            "x": self.x, "y": self.y, "width": self.width, "height": self.height,
            "label": self.label, "confidence": self.confidence,
            "attributes": self.attributes,
        }


@dataclasses.dataclass
class BBox3D:
    """3D bounding box annotation."""
    center: Point3D
    dimensions: Point3D  # width, height, depth
    rotation: Point3D    # roll, pitch, yaw (radians)
    label: str
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "center": self.center.to_dict(),
            "dimensions": self.dimensions.to_dict(),
            "rotation": self.rotation.to_dict(),
            "label": self.label,
            "confidence": self.confidence,
        }


@dataclasses.dataclass
class Keypoint:
    """Single keypoint annotation."""
    point: Point2D
    name: str
    visibility: float = 1.0  # 0=occluded, 1=visible

    def to_dict(self) -> Dict:
        return {"x": self.point.x, "y": self.point.y, "name": self.name,
                "visibility": self.visibility}


@dataclasses.dataclass
class SegmentationMask:
    """Segmentation mask annotation (RLE or polygon)."""
    label: str
    mask_type: str = "polygon"  # polygon, rle, bitmap
    points: List[Point2D] = dataclasses.field(default_factory=list)
    rle: str = ""  # Run-length encoding string
    area: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "mask_type": self.mask_type,
            "points": [p.to_dict() for p in self.points],
            "rle": self.rle,
            "area": self.area,
        }


@dataclasses.dataclass
class TrajectoryLabel:
    """Action label on a trajectory segment."""
    start_frame: int
    end_frame: int
    action_type: str  # grasp, place, push, pull, navigate, etc.
    parameters: Dict[str, Any] = dataclasses.field(default_factory=dict)
    success: Optional[bool] = None

    def to_dict(self) -> Dict:
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "success": self.success,
        }


@dataclasses.dataclass
class ImageAnnotation:
    """Complete annotation for a single image."""
    image_id: str
    image_path: str
    width: int = 0
    height: int = 0
    bboxes: List[BBox2D] = dataclasses.field(default_factory=list)
    keypoints: List[Keypoint] = dataclasses.field(default_factory=list)
    masks: List[SegmentationMask] = dataclasses.field(default_factory=list)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "image_id": self.image_id,
            "image_path": self.image_path,
            "width": self.width,
            "height": self.height,
            "bboxes": [b.to_dict() for b in self.bboxes],
            "keypoints": [k.to_dict() for k in self.keypoints],
            "masks": [m.to_dict() for m in self.masks],
            "metadata": self.metadata,
        }


@dataclasses.dataclass
class PointCloudAnnotation:
    """Annotation for a point cloud frame."""
    frame_id: str
    cloud_path: str
    num_points: int = 0
    bboxes_3d: List[BBox3D] = dataclasses.field(default_factory=list)
    semantic_labels: Dict[int, str] = dataclasses.field(default_factory=dict)  # point_idx → label
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "frame_id": self.frame_id,
            "cloud_path": self.cloud_path,
            "num_points": self.num_points,
            "bboxes_3d": [b.to_dict() for b in self.bboxes_3d],
            "semantic_labels": self.semantic_labels,
            "metadata": self.metadata,
        }


@dataclasses.dataclass
class AnnotationStats:
    """Statistics for an annotation project."""
    total_images: int = 0
    total_frames: int = 0
    total_bboxes: int = 0
    total_keypoints: int = 0
    total_masks: int = 0
    label_distribution: Dict[str, int] = dataclasses.field(default_factory=dict)
    annotated_pct: float = 0.0
    avg_bboxes_per_image: float = 0.0


# ============================================================================
# Annotation Project
# ============================================================================

class AnnotationProject:
    """Manage an annotation project: load, annotate, export."""

    SUPPORTED_FORMATS = {".json", ".coco.json", ".yolo", ".qooannot"}

    def __init__(self, name: str, data_dir: Optional[Union[str, Path]] = None):
        self.name = name
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / "data" / name
        self.created_at = datetime.now()
        self._images: Dict[str, ImageAnnotation] = {}
        self._pointclouds: Dict[str, PointCloudAnnotation] = {}
        self._trajectories: List[TrajectoryLabel] = []
        self._label_set: Set[str] = set()
        self._annotators: Set[str] = set()

    def add_images(self, image_dir: Union[str, Path], pattern: str = "*.{jpg,jpeg,png,bmp}") -> int:
        """Add images to the project."""
        import glob as _glob

        img_dir = Path(image_dir)
        count = 0
        for ext in ["jpg", "jpeg", "png", "bmp"]:
            for img_path in img_dir.glob(f"*.{ext}"):
                img_id = img_path.stem
                if img_id not in self._images:
                    self._images[img_id] = ImageAnnotation(
                        image_id=img_id,
                        image_path=str(img_path),
                    )
                    count += 1
        return count

    def add_pointcloud(self, cloud_path: Union[str, Path]) -> str:
        """Add a point cloud file."""
        path = Path(cloud_path)
        frame_id = path.stem
        self._pointclouds[frame_id] = PointCloudAnnotation(
            frame_id=frame_id,
            cloud_path=str(path),
        )
        return frame_id

    def add_bbox(self, image_id: str, bbox: BBox2D) -> None:
        """Add a 2D bounding box to an image."""
        if image_id in self._images:
            self._images[image_id].bboxes.append(bbox)
            self._label_set.add(bbox.label)

    def add_keypoint(self, image_id: str, kp: Keypoint) -> None:
        """Add a keypoint to an image."""
        if image_id in self._images:
            self._images[image_id].keypoints.append(kp)

    def add_mask(self, image_id: str, mask: SegmentationMask) -> None:
        """Add a segmentation mask to an image."""
        if image_id in self._images:
            self._images[image_id].masks.append(mask)
            self._label_set.add(mask.label)

    def add_bbox_3d(self, frame_id: str, bbox: BBox3D) -> None:
        """Add a 3D bounding box to a point cloud."""
        if frame_id in self._pointclouds:
            self._pointclouds[frame_id].bboxes_3d.append(bbox)
            self._label_set.add(bbox.label)

    def add_trajectory_label(self, label: TrajectoryLabel) -> None:
        """Add a trajectory action label."""
        self._trajectories.append(label)

    def stats(self) -> AnnotationStats:
        """Compute annotation statistics."""
        total_bboxes = sum(len(img.bboxes) for img in self._images.values())
        total_kps = sum(len(img.keypoints) for img in self._images.values())
        total_masks = sum(len(img.masks) for img in self._images.values())

        # Label distribution
        label_dist: Dict[str, int] = defaultdict(int)
        for img in self._images.values():
            for b in img.bboxes:
                label_dist[b.label] += 1
            for m in img.masks:
                label_dist[m.label] += 1

        # Annotation coverage
        annotated = sum(1 for img in self._images.values()
                        if img.bboxes or img.keypoints or img.masks)

        return AnnotationStats(
            total_images=len(self._images),
            total_frames=len(self._pointclouds),
            total_bboxes=total_bboxes,
            total_keypoints=total_kps,
            total_masks=total_masks,
            label_distribution=dict(label_dist),
            annotated_pct=annotated / len(self._images) * 100 if self._images else 0,
            avg_bboxes_per_image=total_bboxes / len(self._images) if self._images else 0,
        )

    def export_coco(self, output_path: Union[str, Path]) -> Path:
        """Export annotations in COCO JSON format."""
        output = Path(output_path)

        # Build category mapping
        categories = [{"id": i + 1, "name": name, "supercategory": "object"}
                      for i, name in enumerate(sorted(self._label_set))]
        cat_name_to_id = {c["name"]: c["id"] for c in categories}

        images = []
        annotations = []
        ann_id = 1

        for img_id, img_ann in self._images.items():
            images.append({
                "id": img_id,
                "file_name": img_ann.image_path,
                "width": img_ann.width,
                "height": img_ann.height,
            })

            for bbox in img_ann.bboxes:
                if bbox.label in cat_name_to_id:
                    annotations.append({
                        "id": ann_id,
                        "image_id": img_id,
                        "category_id": cat_name_to_id[bbox.label],
                        "bbox": [bbox.x, bbox.y, bbox.width, bbox.height],
                        "area": bbox.area(),
                        "iscrowd": 0,
                    })
                    ann_id += 1

        coco = {
            "info": {"description": self.name, "date_created": self.created_at.isoformat()},
            "categories": categories,
            "images": images,
            "annotations": annotations,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(coco, indent=2), encoding="utf-8")
        return output

    def export_yolo(self, output_dir: Union[str, Path]) -> Path:
        """Export annotations in YOLO format."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Classes file
        classes = sorted(self._label_set)
        (out / "classes.txt").write_text("\n".join(classes), encoding="utf-8")

        # Per-image label files
        for img_id, img_ann in self._images.items():
            if not img_ann.bboxes or img_ann.width == 0 or img_ann.height == 0:
                continue
            lines = []
            for bbox in img_ann.bboxes:
                if bbox.label not in classes:
                    continue
                cls_id = classes.index(bbox.label)
                # YOLO: normalized center_x, center_y, width, height
                cx = (bbox.x + bbox.width / 2) / img_ann.width
                cy = (bbox.y + bbox.height / 2) / img_ann.height
                w = bbox.width / img_ann.width
                h = bbox.height / img_ann.height
                lines.append(f"{cls_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            (out / f"{img_id}.txt").write_text("\n".join(lines), encoding="utf-8")

        return out

    def export_qooannot(self, output_path: Union[str, Path]) -> Path:
        """Export in qoodev native annotation format."""
        output = Path(output_path)
        data = {
            "project": self.name,
            "created_at": self.created_at.isoformat(),
            "version": "1.0",
            "label_set": sorted(self._label_set),
            "images": {k: v.to_dict() for k, v in self._images.items()},
            "pointclouds": {k: v.to_dict() for k, v in self._pointclouds.items()},
            "trajectories": [t.to_dict() for t in self._trajectories],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return output

    def import_coco(self, coco_path: Union[str, Path]) -> int:
        """Import COCO JSON annotations."""
        path = Path(coco_path)
        data = json.loads(path.read_text(encoding="utf-8"))

        cat_id_to_name = {c["id"]: c["name"] for c in data.get("categories", [])}
        img_id_to_info = {img["id"]: img for img in data.get("images", [])}

        count = 0
        for ann in data.get("annotations", []):
            img_info = img_id_to_info.get(ann["image_id"])
            if not img_info:
                continue
            img_id = str(img_info["id"])
            bbox = ann["bbox"]  # COCO: [x, y, w, h]
            self.add_bbox(img_id, BBox2D(
                x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3],
                label=cat_id_to_name.get(ann["category_id"], "unknown"),
            ))
            count += 1

        return count


# ============================================================================
# Quality Review
# ============================================================================

class QualityReviewer:
    """Annotation quality review and inter-annotator agreement."""

    @staticmethod
    def compute_iou(a: BBox2D, b: BBox2D) -> float:
        """Compute Intersection over Union for two bboxes."""
        x1 = max(a.x, b.x)
        y1 = max(a.y, b.y)
        x2 = min(a.x + a.width, b.x + b.width)
        y2 = min(a.y + a.height, b.y + b.height)

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        union = a.area() + b.area() - intersection
        return intersection / union if union > 0 else 0.0

    @classmethod
    def compare_annotations(cls, ann_a: ImageAnnotation,
                            ann_b: ImageAnnotation,
                            iou_threshold: float = 0.5) -> Dict[str, Any]:
        """Compare two annotations of the same image."""
        matched = 0
        unmatched_a = len(ann_a.bboxes)
        unmatched_b = len(ann_b.bboxes)

        for ba in ann_a.bboxes:
            for bb in ann_b.bboxes:
                if ba.label == bb.label and cls.compute_iou(ba, bb) >= iou_threshold:
                    matched += 1
                    unmatched_a -= 1
                    unmatched_b -= 1
                    break

        total = len(ann_a.bboxes) + len(ann_b.bboxes)
        return {
            "matched": matched,
            "unmatched_a": unmatched_a,
            "unmatched_b": unmatched_b,
            "agreement": (2 * matched) / total if total > 0 else 1.0,
        }

    @classmethod
    def review_project(cls, project: AnnotationProject) -> List[Dict[str, Any]]:
        """Run quality checks on the project."""
        issues = []

        for img_id, ann in project._images.items():
            # Check for very small bboxes (possible misclicks)
            for i, bbox in enumerate(ann.bboxes):
                if bbox.area() < 100:  # Less than 10x10 pixels
                    issues.append({
                        "type": "small_bbox",
                        "image_id": img_id,
                        "bbox_index": i,
                        "message": f"BBox area {bbox.area():.0f}px² < 100px² threshold",
                    })

            # Check for overlapping same-class bboxes (duplicates)
            for i in range(len(ann.bboxes)):
                for j in range(i + 1, len(ann.bboxes)):
                    bi, bj = ann.bboxes[i], ann.bboxes[j]
                    if bi.label == bj.label:
                        iou = cls.compute_iou(bi, bj)
                        if iou > 0.9:
                            issues.append({
                                "type": "duplicate_bbox",
                                "image_id": img_id,
                                "bbox_indices": [i, j],
                                "message": f"Duplicate bboxes with IoU={iou:.2f}",
                            })

            # Check for unlabeled images
            if not ann.bboxes and not ann.keypoints and not ann.masks:
                issues.append({
                    "type": "unlabeled",
                    "image_id": img_id,
                    "message": "Image has no annotations",
                })

        return issues


# ============================================================================
# Labeler Utilities
# ============================================================================

class Labeler2D:
    """Programmatic 2D annotation utilities."""

    def __init__(self, project: AnnotationProject):
        self.project = project

    def auto_label_bboxes(self, image_id: str, detections: List[Tuple[str, float, float, float, float]]):
        """Apply automatic detection results as bbox annotations."""
        for label, conf, x, y, w, h in detections:
            self.project.add_bbox(image_id, BBox2D(
                x=x, y=y, width=w, height=h,
                label=label, confidence=conf,
            ))

    def label_keypoints(self, image_id: str, keypoints: List[Tuple[str, float, float]]):
        """Apply keypoint annotations."""
        for name, x, y in keypoints:
            self.project.add_keypoint(image_id, Keypoint(
                point=Point2D(x=x, y=y), name=name,
            ))


class Labeler3D:
    """Programmatic 3D annotation utilities."""

    def __init__(self, project: AnnotationProject):
        self.project = project

    def label_bbox_3d(self, frame_id: str, label: str, center: Tuple[float, float, float],
                      dims: Tuple[float, float, float], rotation: Tuple[float, float, float] = (0, 0, 0)):
        """Add a 3D bounding box."""
        self.project.add_bbox_3d(frame_id, BBox3D(
            center=Point3D(*center),
            dimensions=Point3D(*dims),
            rotation=Point3D(*rotation),
            label=label,
        ))


class TrajectoryLabeler:
    """Programmatic trajectory labeling."""

    def __init__(self, project: AnnotationProject):
        self.project = project

    def label_segment(self, start: int, end: int, action: str, **params):
        """Label a trajectory segment with an action."""
        self.project.add_trajectory_label(TrajectoryLabel(
            start_frame=start,
            end_frame=end,
            action_type=action,
            parameters=params,
        ))


__all__ = [
    "AnnotationProject",
    "QualityReviewer",
    "Labeler2D",
    "Labeler3D",
    "TrajectoryLabeler",
    "AnnotationType",
    "LabelClass",
    "ImageAnnotation",
    "PointCloudAnnotation",
    "BBox2D",
    "BBox3D",
    "Keypoint",
    "SegmentationMask",
    "TrajectoryLabel",
    "Point2D",
    "Point3D",
    "AnnotationStats",
]
