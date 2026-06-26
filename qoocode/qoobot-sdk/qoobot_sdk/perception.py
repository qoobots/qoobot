"""
Perception API - Sensor data types and interfaces.

Provides data structures for common robot sensor data:
- Camera images (RGB, depth)
- LiDAR point clouds
- IMU readings
- Joint states
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple

import numpy as np


@dataclass
class Image:
    """RGB camera image.

    Attributes:
        data: Image pixel data (H, W, 3) uint8
        timestamp: Capture timestamp in seconds
        width: Image width in pixels
        height: Image height in pixels
    """
    data: np.ndarray
    timestamp: float = 0.0
    width: int = 0
    height: int = 0

    def __post_init__(self):
        if self.width == 0 and self.data is not None:
            self.height, self.width = self.data.shape[:2]

    @classmethod
    def from_numpy(cls, data: np.ndarray, timestamp: float = 0.0) -> "Image":
        """Create Image from numpy array."""
        h, w = data.shape[:2]
        return cls(data=data, timestamp=timestamp, width=w, height=h)


@dataclass
class DepthMap:
    """Depth camera image.

    Attributes:
        data: Depth values in meters (H, W) float32
        timestamp: Capture timestamp in seconds
        near: Near clipping plane in meters
        far: Far clipping plane in meters
    """
    data: np.ndarray
    timestamp: float = 0.0
    near: float = 0.1
    far: float = 10.0


@dataclass
class PointCloud:
    """LiDAR point cloud.

    Attributes:
        points: XYZ coordinates (N, 3) float32
        intensities: Intensity values (N,) float32, optional
        timestamp: Capture timestamp in seconds
    """
    points: np.ndarray
    intensities: Optional[np.ndarray] = None
    timestamp: float = 0.0

    @property
    def size(self) -> int:
        """Number of points."""
        return len(self.points)

    @property
    def xyz(self) -> np.ndarray:
        """XYZ coordinates."""
        return self.points

    def filter_range(self, min_range: float, max_range: float) -> "PointCloud":
        """Filter points by range from origin."""
        distances = np.linalg.norm(self.points, axis=1)
        mask = (distances >= min_range) & (distances <= max_range)
        return PointCloud(
            points=self.points[mask],
            intensities=self.intensities[mask] if self.intensities is not None else None,
            timestamp=self.timestamp,
        )


@dataclass
class IMUData:
    """IMU sensor reading.

    Attributes:
        accel: Linear acceleration (x, y, z) in m/s²
        gyro: Angular velocity (x, y, z) in rad/s
        mag: Magnetic field (x, y, z) in μT, optional
        timestamp: Reading timestamp in seconds
    """
    accel: Tuple[float, float, float]
    gyro: Tuple[float, float, float]
    mag: Optional[Tuple[float, float, float]] = None
    timestamp: float = 0.0


@dataclass
class JointState:
    """Single joint state.

    Attributes:
        name: Joint name
        position: Current position in radians
        velocity: Current velocity in rad/s
        torque: Current torque in Nm
    """
    name: str
    position: float = 0.0
    velocity: float = 0.0
    torque: float = 0.0


@dataclass
class JointStates:
    """All joint states for the robot.

    Attributes:
        joints: List of joint states
        timestamp: Reading timestamp in seconds
    """
    joints: List[JointState] = field(default_factory=list)
    timestamp: float = 0.0

    def get(self, name: str) -> Optional[JointState]:
        """Get joint state by name."""
        for j in self.joints:
            if j.name == name:
                return j
        return None

    @property
    def positions(self) -> np.ndarray:
        """All joint positions as numpy array."""
        return np.array([j.position for j in self.joints])

    @property
    def velocities(self) -> np.ndarray:
        """All joint velocities as numpy array."""
        return np.array([j.velocity for j in self.joints])
