"""
brain_ai/perception/scene_aggregator.py — Multi-sensor scene fusion → SceneGraph.

Fuses outputs from:
  - YOLODetector     (object detection)
  - SAMSegmetor      (instance masks)
  - SLAMWrapper      (camera pose + map)
  - PoseEstimator    (per-object 6-DoF pose)
  - OccupancyGrid    (collision map)
  - TrackManager     (temporal tracking)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np

try:
    from brain_ai.domain.scene import (
        BoundingBox3D, DetectedObject, OccupancyVoxelGrid,
        Pose6D, Quaternion, SceneGraph, Vec3,
    )
except ImportError:
    from domain.scene import (
        BoundingBox3D, DetectedObject, OccupancyVoxelGrid,
        Pose6D, Quaternion, SceneGraph, Vec3,
    )
from .detector import YOLODetector, Detection
from .segmentor import SAMSegmetor, SegmentationMask
from .slam_wrapper import SLAMWrapper
from .pose_estimator import PoseEstimator
from .occupancy_net import OccupancyGrid
from .track_manager import TrackManager

logger = logging.getLogger(__name__)


@dataclass
class PerceptionFrame:
    """Snapshot of all raw perception outputs for one frame."""
    timestamp: float = field(default_factory=time.time)
    image_rgb: Optional[np.ndarray] = None
    image_depth: Optional[np.ndarray] = None
    camera_pose: Optional[Pose6D] = None
    detections: list[Detection] = field(default_factory=list)
    masks: list[SegmentationMask] = field(default_factory=list)


class SceneAggregator:
    """Central perception pipeline: raw sensors → SceneGraph.

    Usage::

        agg = SceneAggregator(slam=my_slam, detector=my_detector, ...)
        scene = agg.process_frame(image_rgb, image_depth)
    """

    def __init__(
        self,
        slam: Optional[SLAMWrapper] = None,
        detector: Optional[YOLODetector] = None,
        segmentor: Optional[SAMSegmetor] = None,
        pose_estimator: Optional[PoseEstimator] = None,
        occupancy: Optional[OccupancyGrid] = None,
        tracker: Optional[TrackManager] = None,
        enable_spatial_relations: bool = True,
    ) -> None:
        self._slam = slam or SLAMWrapper(vocab_path="orb_vocab.fbow", enable_mock=True)
        self._detector = detector or YOLODetector()
        self._segmentor = segmentor or SAMSegmetor(enable_mock=True)
        self._pose_estimator = pose_estimator or PoseEstimator()
        self._occupancy = occupancy or OccupancyGrid()
        self._tracker = tracker or TrackManager()

        self._enable_spatial_relations = enable_spatial_relations
        self._frame_count: int = 0

        # Warm up mock sources
        if not isinstance(self._slam, SLAMWrapper):
            self._slam = SLAMWrapper(vocab_path="orb_vocab.fbow", enable_mock=True)
        self._slam.start()

        logger.info("[SceneAggregator] Initialized with all perception modules")

    # ── Main pipeline ──────────────────────────────────────────────────

    def process_frame(
        self,
        image_rgb: np.ndarray,
        image_depth: Optional[np.ndarray] = None,
        timestamp: Optional[float] = None,
    ) -> SceneGraph:
        """Process a single RGB-D frame through the full perception pipeline.

        Pipeline: SLAM → Detector → Segmentor → PoseEstimator → Tracker → SceneGraph

        Args:
            image_rgb: RGB image uint8 (H, W, 3)
            image_depth: optional depth float32 (H, W) in meters
            timestamp: frame timestamp (seconds)

        Returns:
            Aggregated SceneGraph
        """
        ts = timestamp or time.time()
        self._frame_count += 1

        # 1. SLAM: get camera pose
        camera_pose = self._slam.get_pose()

        # 2. Detection: find objects in 2D
        detections = self._detector.detect(image_rgb)
        logger.debug(f"[SceneAggregator] Frame {self._frame_count}: {len(detections)} detections")

        # 3. Segmentation: get instance masks from detection bboxes
        prompts = [
            {"box": d.bbox_xyxy} for d in detections
        ]
        masks = self._segmentor.segment(image_rgb, prompts=prompts)

        # 4. Tracking: associate detections across frames
        raw_frame = PerceptionFrame(
            timestamp=ts, image_rgb=image_rgb, image_depth=image_depth,
            camera_pose=camera_pose, detections=detections, masks=masks,
        )
        tracks = self._tracker.update(detections, camera_pose, image_depth)

        # 5. Pose estimation: 3D pose for each tracked object
        objects: list[DetectedObject] = []
        for track in tracks:
            # Estimate 6-DoF pose
            det_match = self._find_detection(track.label, detections)
            bbox = det_match.bbox_xyxy if det_match else None
            pose_est = self._pose_estimator.estimate_pose(
                track.label, image_rgb, image_depth, bbox, camera_pose,
            )

            # Infer 3D bounding box from class
            bbox3d = self._infer_bbox3d(track.label, pose_est.pose)

            obj = DetectedObject(
                id=track.track_id,
                label=track.label,
                confidence=float(track.confidence),
                pose=pose_est.pose,
                bbox=bbox3d,
                track_id=track.track_id,
                graspable=track.label in {"cup", "bottle", "bowl", "book", "box", "can"},
                attributes={"velocity": track.velocity.to_list()},
            )
            objects.append(obj)

        # 6. Occupancy: update grid from depth
        if image_depth is not None:
            self._occupancy.update_from_depth(
                image_depth, depth_scale=1.0, camera_pose=camera_pose,
            )
            # Mark detected objects as occupied
            for obj in objects:
                self._occupancy.update_from_detection(
                    bbox_center=obj.bbox.center,
                    bbox_size=obj.bbox.size,
                    occupied=True,
                )

        # 7. Build SceneGraph
        occ_grid = self._occupancy.finalize()
        scene = SceneGraph(
            timestamp=datetime.now(),
            objects=objects,
            robot_pose=camera_pose,
            occupancy=occ_grid,
            source_frame="world",
        )

        logger.info(
            f"[SceneAggregator] Frame {self._frame_count}: "
            f"{len(objects)} objects, {len(tracks)} tracks"
        )
        return scene

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _find_detection(
        label: str, detections: list[Detection],
    ) -> Optional[Detection]:
        for d in detections:
            if d.label == label:
                return d
        return None

    @staticmethod
    def _infer_bbox3d(label: str, pose: Pose6D) -> BoundingBox3D:
        """Infer 3D bounding box dimensions from object class."""
        sizes = {
            "cup": Vec3(0.08, 0.08, 0.12),
            "bottle": Vec3(0.06, 0.06, 0.20),
            "bowl": Vec3(0.12, 0.12, 0.06),
            "book": Vec3(0.15, 0.02, 0.22),
            "box": Vec3(0.15, 0.15, 0.15),
            "can": Vec3(0.06, 0.06, 0.10),
            "dining_table": Vec3(1.2, 0.8, 0.05),
            "chair": Vec3(0.4, 0.4, 0.9),
        }
        sz = sizes.get(label, Vec3(0.10, 0.10, 0.10))
        return BoundingBox3D(center=pose.position, size=sz)

    # ── Batch processing ──────────────────────────────────────────────

    def process_batch(
        self, frames: list[tuple[np.ndarray, Optional[np.ndarray], float]]
    ) -> list[SceneGraph]:
        """Process multiple frames (offline)."""
        return [
            self.process_frame(rgb, depth, ts)
            for rgb, depth, ts in frames
        ]

    # ── Accessors ─────────────────────────────────────────────────────

    @property
    def slam(self) -> SLAMWrapper:
        return self._slam

    @property
    def detector(self) -> YOLODetector:
        return self._detector

    @property
    def occupancy_grid(self) -> OccupancyGrid:
        return self._occupancy

    @property
    def tracker(self) -> TrackManager:
        return self._tracker

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def shutdown(self) -> None:
        """Stop all perception modules."""
        self._slam.stop()
        logger.info("[SceneAggregator] Shutdown complete")
