"""
brain_ai/perception/track_manager.py — Multi-frame object tracking.

Supports:
  - Kalman filter tracking (constant velocity model)
  - IoU-based data association
  - Track lifecycle (born → active → lost → dead)
  - Mock fallback for development
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

try:
    from brain_ai.domain.scene import Pose6D, Quaternion, Vec3
except ImportError:
    from domain.scene import Pose6D, Quaternion, Vec3
from .detector import Detection

logger = logging.getLogger(__name__)


class TrackState(Enum):
    BORN = "born"       # newly created, not yet confirmed
    ACTIVE = "active"   # actively tracked
    LOST = "lost"       # temporarily lost (occlusion)
    DEAD = "dead"       # permanently removed


@dataclass
class Track:
    """Single object track across frames."""
    track_id: str
    label: str
    state: TrackState = TrackState.BORN

    # Kalman filter state: [x, y, z, vx, vy, vz]
    state_vector: np.ndarray = field(default_factory=lambda: np.zeros(6))
    covariance: np.ndarray = field(default_factory=lambda: np.eye(6) * 0.1)

    # Pose history (last 30 frames)
    pose_history: list[Pose6D] = field(default_factory=list)
    max_history: int = 30

    # Lifecycle counters
    age: int = 0               # total frames alive
    hits: int = 0              # frames with detection match
    misses: int = 0            # consecutive frames without match
    confidence: float = 0.0

    # Thresholds
    MIN_HITS_TO_ACTIVE: int = 3
    MAX_MISSES_TO_DEAD: int = 10

    def predict(self) -> Vec3:
        """Kalman predict step (constant velocity). dt=1 frame."""
        # Simple constant velocity model
        F = np.array([
            [1, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 1],
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1],
        ])
        Q = np.eye(6) * 0.01  # process noise

        self.state_vector = F @ self.state_vector
        self.covariance = F @ self.covariance @ F.T + Q

        return Vec3(
            float(self.state_vector[0]),
            float(self.state_vector[1]),
            float(self.state_vector[2]),
        )

    def update(self, measurement: Vec3) -> None:
        """Kalman update with position measurement."""
        H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0],
        ])
        R = np.eye(3) * 0.05  # measurement noise

        z = np.array([measurement.x, measurement.y, measurement.z])
        y = z - H @ self.state_vector  # innovation

        S = H @ self.covariance @ H.T + R
        K = self.covariance @ H.T @ np.linalg.inv(S)

        self.state_vector = self.state_vector + K @ y
        self.covariance = (np.eye(6) - K @ H) @ self.covariance

        self.hits += 1
        self.misses = 0
        self.confidence = min(1.0, self.confidence + 0.05)
        self.age += 1

        if self.hits >= self.MIN_HITS_TO_ACTIVE and self.state == TrackState.BORN:
            self.state = TrackState.ACTIVE

    def mark_missed(self) -> None:
        """Called when no detection matches this track."""
        self.misses += 1
        self.age += 1
        self.confidence = max(0.0, self.confidence - 0.1)
        self.predict()  # propagate forward

        if self.state == TrackState.ACTIVE and self.misses >= 3:
            self.state = TrackState.LOST

    @property
    def position(self) -> Vec3:
        return Vec3(
            float(self.state_vector[0]),
            float(self.state_vector[1]),
            float(self.state_vector[2]),
        )

    @property
    def velocity(self) -> Vec3:
        return Vec3(
            float(self.state_vector[3]),
            float(self.state_vector[4]),
            float(self.state_vector[5]),
        )

    @property
    def is_alive(self) -> bool:
        return self.state != TrackState.DEAD


class TrackManager:
    """Multi-object tracker with Kalman filter + IoU data association.

    Usage::

        mgr = TrackManager()
        tracks = mgr.update(detections, camera_pose, depth_img)
    """

    def __init__(
        self,
        iou_threshold: float = 0.3,
        max_age: int = 10,
        min_hits: int = 3,
    ) -> None:
        self._iou_threshold = iou_threshold
        self._max_age = max_age
        self._min_hits = min_hits
        self._tracks: dict[str, Track] = {}

    def update(
        self,
        detections: list[Detection],
        camera_pose: Optional[Pose6D] = None,
        depth_img: Optional[np.ndarray] = None,
    ) -> list[Track]:
        """Update tracks with new detections.

        Args:
            detections: current frame detections
            camera_pose: camera pose for 3D projection
            depth_img: depth image for 3D localization

        Returns:
            List of active tracks
        """
        # Step 1: Predict all existing tracks
        for track in self._tracks.values():
            track.predict()
            track.mark_missed()

        # Step 2: Data association via IoU (2D bbox) or distance (3D)
        matches = self._associate(detections)

        # Step 3: Update matched tracks, create new ones for unmatched
        matched_det_indices = set()
        for det_idx, track_id, iou in matches:
            track = self._tracks[track_id]
            # Estimate 3D position from detection + depth
            pos3d = self._estimate_3d(detections[det_idx], camera_pose, depth_img)
            track.update(pos3d)
            matched_det_indices.add(det_idx)
            logger.debug(f"[TrackManager] Matched {track.label} ({track_id}): IoU={iou:.2f}")

        # Step 4: Create new tracks for unmatched detections
        for i, det in enumerate(detections):
            if i not in matched_det_indices:
                track_id = f"trk_{uuid.uuid4().hex[:8]}"
                pos3d = self._estimate_3d(det, camera_pose, depth_img)
                track = Track(track_id=track_id, label=det.label)
                track.state_vector[:3] = [pos3d.x, pos3d.y, pos3d.z]
                track.confidence = det.confidence
                track.hits = 1
                track.age = 1
                self._tracks[track_id] = track
                logger.debug(f"[TrackManager] New track: {det.label} ({track_id})")

        # Step 5: Remove dead tracks
        dead = [
            tid for tid, t in self._tracks.items()
            if t.misses >= self._max_age or t.state == TrackState.DEAD
        ]
        for tid in dead:
            del self._tracks[tid]

        return self.get_active_tracks()

    def _associate(
        self, detections: list[Detection]
    ) -> list[tuple[int, str, float]]:
        """IoU-based data association between tracks and detections.

        Returns:
            List of (detection_index, track_id, iou_score)
        """
        matches: list[tuple[int, str, float]] = []
        if not detections or not self._tracks:
            return matches

        # Build cost matrix based on 2D IoU between predicted and detected bboxes
        # Simplified: use class match + position proximity
        for i, det in enumerate(detections):
            best_iou = 0.0
            best_tid = ""
            for tid, track in self._tracks.items():
                if track.label != det.label:
                    continue
                # IoU proxy: confidence-weighted label match
                iou = det.confidence * track.confidence
                if iou > best_iou and iou >= self._iou_threshold:
                    best_iou = iou
                    best_tid = tid
            if best_tid:
                matches.append((i, best_tid, best_iou))

        # Greedy: keep only best match per detection
        return matches

    def _estimate_3d(
        self,
        det: Detection,
        camera_pose: Optional[Pose6D],
        depth_img: Optional[np.ndarray],
    ) -> Vec3:
        """Estimate 3D position of a detection."""
        # Mock: convert normalized bbox center to tabletop coordinates
        x1, y1, x2, y2 = det.bbox_xyxy
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

        # Simple projection: map to table surface
        world_x = (cx - 0.5) * 1.5
        world_y = 0.3 + (0.5 - cy) * 1.0
        world_z = 0.08  # typical object height

        if camera_pose:
            world_x += camera_pose.position.x
            world_y += camera_pose.position.y

        # If depth available, use it for more accurate z
        if depth_img is not None and depth_img.size > 0:
            h, w = depth_img.shape
            px = int(cx * w)
            py = int(cy * h)
            if 0 <= px < w and 0 <= py < h:
                d = float(depth_img[py, px])
                if d > 0:
                    world_z = d - 0.65  # subtract table height

        return Vec3(world_x, world_y, world_z)

    # ── Query ─────────────────────────────────────────────────────────

    def get_active_tracks(self) -> list[Track]:
        """Return all active (confirmed) tracks."""
        return [t for t in self._tracks.values() if t.state == TrackState.ACTIVE]

    def get_track_by_id(self, track_id: str) -> Optional[Track]:
        return self._tracks.get(track_id)

    def get_track_by_label(self, label: str) -> Optional[Track]:
        for t in self._tracks.values():
            if t.label == label and t.state == TrackState.ACTIVE:
                return t
        return None

    @property
    def num_tracks(self) -> int:
        return len(self._tracks)

    def reset(self) -> None:
        self._tracks.clear()
        logger.info("[TrackManager] Reset all tracks")
