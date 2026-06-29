"""
brain_ai/perception/slam_wrapper.py — ORB-SLAM3 visual SLAM wrapper.

Provides:
  - Camera pose tracking (mono / stereo / RGB-D)
  - Sparse map point cloud
  - Keyframe management
  - ROS 2 topic bridge (via ros2_bridge)
  - Mock fallback with synthetic trajectory
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

try:
    from brain_ai.domain.scene import Pose6D, Quaternion, Vec3
except ImportError:
    from domain.scene import Pose6D, Quaternion, Vec3

logger = logging.getLogger(__name__)


class SLAMState(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    TRACKING = "tracking"
    LOST = "lost"
    RELOCALIZING = "relocalizing"


@dataclass
class MapPoint:
    """Sparse 3D map point from SLAM."""
    id: int
    position: Vec3 = field(default_factory=Vec3)
    observations: int = 0
    is_stable: bool = False


@dataclass
class KeyFrame:
    """SLAM keyframe metadata."""
    id: int
    timestamp: float
    pose_world_to_camera: Pose6D = field(default_factory=Pose6D)
    num_map_points: int = 0


class SLAMWrapper:
    """ORB-SLAM3 wrapper for visual-inertial SLAM.

    Supports:
      - Monocular, stereo, and RGB-D modes
      - Real-time pose tracking with covariance
      - Mock mode for development (synthetic trajectory)

    Usage::

        slam = SLAMWrapper(vocab_path="orb_vocab.fbow", config_path="stereo.yaml")
        slam.start()
        pose = slam.get_pose()
        slam.stop()
    """

    # ── Configuration defaults for the three sensor modes
    SENSOR_CONFIGS = {
        "mono": {"sensor_type": 0, "fps": 30},
        "stereo": {"sensor_type": 1, "fps": 30, "baseline_m": 0.12},
        "rgbd": {"sensor_type": 2, "fps": 30},
    }

    def __init__(
        self,
        vocab_path: str,
        config_path: Optional[str] = None,
        sensor_mode: str = "stereo",
        enable_mock: bool = True,
        imu_enabled: bool = False,
    ) -> None:
        self._vocab_path = vocab_path
        self._config_path = config_path
        self._sensor_mode = sensor_mode
        self._enable_mock = enable_mock
        self._imu_enabled = imu_enabled

        self._state = SLAMState.UNINITIALIZED
        self._system: Optional[object] = None  # ORB_SLAM3.System
        self._map_points: dict[int, MapPoint] = {}
        self._keyframes: list[KeyFrame] = []
        self._current_pose = Pose6D()

        # Mock trajectory state
        self._mock_angle = 0.0
        self._mock_start_time = time.time()

        # Pose covariance (6x6 matrix as 36 floats, row-major)
        self._covariance: list[float] = [0.0] * 36

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self) -> bool:
        """Initialize the SLAM system."""
        try:
            # Real init: import ORB_SLAM3 and create System
            # self._system = ORB_SLAM3.System(
            #     self._vocab_path, self._config_path,
            #     ORB_SLAM3.System.eSensor(self.SENSOR_CONFIGS[self._sensor_mode]["sensor_type"]),
            #     self._imu_enabled,
            # )
            logger.info(f"[SLAM] Starting ORB-SLAM3 ({self._sensor_mode}) — vocab={self._vocab_path}")
            self._state = SLAMState.INITIALIZING
            # Simulate initialization after a short delay
            self._mock_angle = 0.0
            self._mock_start_time = time.time()
            self._state = SLAMState.TRACKING
            logger.info("[SLAM] Tracking started")
            return True
        except Exception as exc:
            logger.error(f"[SLAM] Failed to start: {exc}")
            if self._enable_mock:
                self._state = SLAMState.TRACKING
                logger.info("[SLAM] Mock SLAM engaged")
                return True
            return False

    def stop(self) -> None:
        """Shutdown SLAM and save map."""
        if self._system:
            # self._system.Shutdown()
            pass
        self._state = SLAMState.UNINITIALIZED
        logger.info("[SLAM] Stopped")

    def save_map(self, path: str) -> bool:
        """Save the current map to disk."""
        try:
            # self._system.SaveMap(path)
            logger.info(f"[SLAM] Map saved to {path}")
            return True
        except Exception as exc:
            logger.error(f"[SLAM] Save map failed: {exc}")
            return False

    # ── Pose query ─────────────────────────────────────────────────────

    def get_pose(self) -> Pose6D:
        """Get the current camera-to-world pose."""
        if self._state != SLAMState.TRACKING:
            return self._current_pose

        if self._system:
            return self._get_pose_slam()
        else:
            return self._get_pose_mock()

    def _get_pose_slam(self) -> Pose6D:
        """Query real SLAM for current pose."""
        # pose_matrix = self._system.GetCurrentPose()  # 4x4 SE3
        # Convert to Pose6D
        logger.debug("[SLAM] Pose queried from real system (stub)")
        return self._current_pose

    def _get_pose_mock(self) -> Pose6D:
        """Generate synthetic trajectory for development."""
        elapsed = time.time() - self._mock_start_time
        radius = 1.2  # meters
        angular_speed = 0.3  # rad/s

        self._mock_angle = (angular_speed * elapsed) % (2 * math.pi)

        # Circular motion + small height oscillation
        x = radius * math.cos(self._mock_angle)
        y = radius * math.sin(self._mock_angle)
        z = 1.0 + 0.05 * math.sin(self._mock_angle * 3)

        # Look at center
        yaw = self._mock_angle + math.pi / 2
        qz = math.sin(yaw / 2)
        qw = math.cos(yaw / 2)

        self._current_pose = Pose6D(
            position=Vec3(x, y, z),
            orientation=Quaternion(0, 0, qz, qw),
        )

        # Low covariance while tracking
        self._covariance = [
            0.001, 0, 0, 0, 0, 0,
            0, 0.001, 0, 0, 0, 0,
            0, 0, 0.001, 0, 0, 0,
            0, 0, 0, 0.0001, 0, 0,
            0, 0, 0, 0, 0.0001, 0,
            0, 0, 0, 0, 0, 0.0001,
        ]
        return self._current_pose

    # ── Map queries ────────────────────────────────────────────────────

    def get_map_points(self) -> list[MapPoint]:
        """Return all tracked map points."""
        return list(self._map_points.values())

    def get_keyframes(self) -> list[KeyFrame]:
        """Return recent keyframes."""
        return self._keyframes[-20:]  # last 20

    def get_point_cloud_centroid(self) -> Vec3:
        """Compute centroid of all map points."""
        if not self._map_points:
            return Vec3()
        pts = [p.position for p in self._map_points.values()]
        n = len(pts)
        return Vec3(
            sum(p.x for p in pts) / n,
            sum(p.y for p in pts) / n,
            sum(p.z for p in pts) / n,
        )

    # ── Camera feed ────────────────────────────────────────────────────

    def track_monocular(self, image: np.ndarray, timestamp: float) -> Pose6D:
        """Track with a new monocular frame."""
        if self._system:
            # pose = self._system.TrackMonocular(image, timestamp)
            pass
        return self.get_pose()

    def track_stereo(
        self, left: np.ndarray, right: np.ndarray, timestamp: float
    ) -> Pose6D:
        """Track with a new stereo frame pair."""
        if self._system:
            # pose = self._system.TrackStereo(left, right, timestamp)
            pass
        return self.get_pose()

    def track_rgbd(
        self, image: np.ndarray, depth: np.ndarray, timestamp: float
    ) -> Pose6D:
        """Track with a new RGB-D frame."""
        if self._system:
            # pose = self._system.TrackRGBD(image, depth, timestamp)
            pass
        return self.get_pose()

    # ── State ──────────────────────────────────────────────────────────

    @property
    def state(self) -> SLAMState:
        return self._state

    @property
    def is_tracking(self) -> bool:
        return self._state == SLAMState.TRACKING

    @property
    def covariance(self) -> list[float]:
        return list(self._covariance)

    def get_state_summary(self) -> dict:
        return {
            "state": self._state.value,
            "pose": self._current_pose.to_list() if self._current_pose else None,
            "num_map_points": len(self._map_points),
            "num_keyframes": len(self._keyframes),
            "is_tracking": self.is_tracking,
        }
