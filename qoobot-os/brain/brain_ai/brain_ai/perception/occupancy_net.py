"""
brain_ai/perception/occupancy_net.py — 3D occupancy grid / voxel map.

Provides:
  - Fused occupancy from depth + stereo + detection
  - Ray-casting for collision checks
  - Mock fallback with synthetic grid
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

try:
    from brain_ai.domain.scene import OccupancyVoxelGrid, Vec3
except ImportError:
    from domain.scene import OccupancyVoxelGrid, Vec3

logger = logging.getLogger(__name__)


class OccupancyGrid:
    """3D voxel occupancy map for navigation and collision avoidance.

    Uses a fixed-size voxel grid centered on the robot.
    Voxel values: 0 = free, 1 = occupied, 255 = unknown.

    Usage::

        grid = OccupancyGrid(resolution=0.05, grid_size_m=(5.0, 5.0, 3.0))
        grid.update_from_depth(depth_img, depth_scale, camera_pose)
        hit = grid.check_ray(start, end)
    """

    UNKNOWN = 255
    FREE = 0
    OCCUPIED = 1

    def __init__(
        self,
        resolution: float = 0.05,  # 5 cm voxels
        grid_size_m: tuple[float, float, float] = (5.0, 5.0, 3.0),
        origin_shift: Optional[Vec3] = None,
        prob_hit: float = 0.70,
        prob_miss: float = 0.35,
        clamp_min: float = 0.12,
        clamp_max: float = 0.97,
    ) -> None:
        self._resolution = resolution
        self._grid_size_m = grid_size_m
        self._origin = origin_shift or Vec3(-grid_size_m[0] / 2, -grid_size_m[1] / 2, 0.0)

        self._dims = (
            int(grid_size_m[0] / resolution),
            int(grid_size_m[1] / resolution),
            int(grid_size_m[2] / resolution),
        )

        # Occupancy probabilities in log-odds
        self._prob_hit = prob_hit
        self._prob_miss = prob_miss
        self._log_hit = np.log(prob_hit / (1.0 - prob_hit))
        self._log_miss = np.log(prob_miss / (1.0 - prob_miss))
        self._clamp_min = np.log(clamp_min / (1.0 - clamp_min))
        self._clamp_max = np.log(clamp_max / (1.0 - clamp_max))

        # Log-odds grid (0 = unknown/0.5 prob)
        self._log_odds = np.zeros(self._dims, dtype=np.float32)
        self._data = np.full(self._dims, self.UNKNOWN, dtype=np.uint8)

        logger.info(
            f"[OccupancyGrid] Created {self._dims} grid "
            f"({resolution}m res, {grid_size_m} m size)"
        )

    # ── Properties ─────────────────────────────────────────────────────

    @property
    def dims(self) -> tuple[int, int, int]:
        return self._dims

    @property
    def resolution(self) -> float:
        return self._resolution

    @property
    def origin(self) -> Vec3:
        return self._origin

    @property
    def data(self) -> np.ndarray:
        return self._data

    # ── Coordinate conversion ─────────────────────────────────────────

    def world_to_voxel(self, pos: Vec3) -> tuple[int, int, int]:
        """Convert world coordinates (meters) to voxel indices."""
        vx = int((pos.x - self._origin.x) / self._resolution)
        vy = int((pos.y - self._origin.y) / self._resolution)
        vz = int((pos.z - self._origin.z) / self._resolution)
        return self._clamp_voxel(vx, vy, vz)

    def voxel_to_world(self, vx: int, vy: int, vz: int) -> Vec3:
        """Convert voxel index to world coordinate (voxel center)."""
        return Vec3(
            self._origin.x + (vx + 0.5) * self._resolution,
            self._origin.y + (vy + 0.5) * self._resolution,
            self._origin.z + (vz + 0.5) * self._resolution,
        )

    def _clamp_voxel(self, vx: int, vy: int, vz: int) -> tuple[int, int, int]:
        dx, dy, dz = self._dims
        return (
            max(0, min(dx - 1, vx)),
            max(0, min(dy - 1, vy)),
            max(0, min(dz - 1, vz)),
        )

    # ── Update from depth ─────────────────────────────────────────────

    def update_from_depth(
        self,
        depth_img: np.ndarray,
        depth_scale: float,
        camera_pose,
        max_range: float = 3.0,
    ) -> None:
        """Update occupancy from a depth image.

        Uses ray-casting: free space along ray, occupied at endpoint.

        Args:
            depth_img: (H, W) depth in raw units (uint16 or float)
            depth_scale: multiplier to convert depth to meters
            camera_pose: Pose6D of camera in world frame
            max_range: max depth range to consider (meters)
        """
        if depth_img is None or depth_img.size == 0:
            return

        depth_m = depth_img.astype(np.float32) * depth_scale
        valid = (depth_m > 0) & (depth_m < max_range)

        # Mark occupied voxels at depth endpoints
        for y, x in zip(*np.where(valid)):
            d = depth_m[y, x]
            # Project ray from camera through pixel
            # Simplified: assume optical-center projection
            px = (x / depth_img.shape[1] - 0.5) * d
            py = (y / depth_img.shape[0] - 0.5) * d
            pz = d

            world_x = camera_pose.position.x + px
            world_y = camera_pose.position.y + py
            world_z = camera_pose.position.z + pz

            vx, vy, vz = self.world_to_voxel(Vec3(world_x, world_y, world_z))
            self._update_voxel(vx, vy, vz, self._log_hit)

        logger.debug(f"[OccupancyGrid] Updated from depth: {np.sum(valid)} points")

    def update_from_detection(
        self, bbox_center: Vec3, bbox_size: Vec3, occupied: bool = True
    ) -> None:
        """Mark all voxels within a 3D bounding box as occupied/free."""
        v_min = self.world_to_voxel(Vec3(
            bbox_center.x - bbox_size.x / 2,
            bbox_center.y - bbox_size.y / 2,
            bbox_center.z - bbox_size.z / 2,
        ))
        v_max = self.world_to_voxel(Vec3(
            bbox_center.x + bbox_size.x / 2,
            bbox_center.y + bbox_size.y / 2,
            bbox_center.z + bbox_size.z / 2,
        ))

        value = self._log_hit if occupied else self._log_miss
        for vx in range(v_min[0], v_max[0] + 1):
            for vy in range(v_min[1], v_max[1] + 1):
                for vz in range(v_min[2], v_max[2] + 1):
                    cvx, cvy, cvz = self._clamp_voxel(vx, vy, vz)
                    self._update_voxel(cvx, cvy, cvz, value)

    def _update_voxel(self, vx: int, vy: int, vz: int, delta: float) -> None:
        """Bayesian update of a single voxel."""
        self._log_odds[vx, vy, vz] = np.clip(
            self._log_odds[vx, vy, vz] + delta,
            self._clamp_min, self._clamp_max,
        )

    # ── Query ─────────────────────────────────────────────────────────

    def is_occupied(self, pos: Vec3) -> bool:
        """Check if a world position is occupied."""
        vx, vy, vz = self.world_to_voxel(pos)
        return bool(self._data[vx, vy, vz] == self.OCCUPIED)

    def check_ray(
        self, start: Vec3, end: Vec3, step_m: float = 0.05
    ) -> tuple[bool, Optional[Vec3]]:
        """Ray-cast: check if line from start to end hits occupied voxels.

        Returns:
            (hit: bool, hit_point: Vec3 or None)
        """
        diff = Vec3(end.x - start.x, end.y - start.y, end.z - start.z)
        dist = diff.norm()
        if dist < 1e-6:
            return (False, None)

        dir_x = diff.x / dist
        dir_y = diff.y / dist
        dir_z = diff.z / dist

        steps = int(dist / step_m)
        for i in range(steps + 1):
            t = i * step_m
            pt = Vec3(
                start.x + t * dir_x,
                start.y + t * dir_y,
                start.z + t * dir_z,
            )
            vx, vy, vz = self.world_to_voxel(pt)
            if self._data[vx, vy, vz] == self.OCCUPIED:
                return (True, pt)

        return (False, None)

    def get_occupancy_probability(self, pos: Vec3) -> float:
        """Get occupancy probability (0..1) at a world position."""
        vx, vy, vz = self.world_to_voxel(pos)
        log_odds = self._log_odds[vx, vy, vz]
        return 1.0 / (1.0 + np.exp(-log_odds))

    def finalize(self) -> OccupancyVoxelGrid:
        """Convert log-odds to discrete occupancy and return domain object."""
        # Threshold: > 0.5 prob → occupied
        self._data = np.where(
            1.0 / (1.0 + np.exp(-self._log_odds)) > 0.5,
            self.OCCUPIED, self.FREE,
        ).astype(np.uint8)

        return OccupancyVoxelGrid(
            resolution_m=self._resolution,
            origin=self._origin,
            dims=self._dims,
            data=self._data.tobytes(),
        )

    def reset(self) -> None:
        """Clear all voxels to unknown."""
        self._log_odds.fill(0.0)
        self._data.fill(self.UNKNOWN)


def create_tabletop_mock_grid() -> OccupancyGrid:
    """Create a mock occupancy grid with a table surface."""
    grid = OccupancyGrid(
        resolution=0.05,
        grid_size_m=(2.0, 2.0, 1.5),
        origin_shift=Vec3(-1.0, -0.5, 0.0),
    )

    # Add table surface (a flat slab at z=0.65~0.72)
    table_top = Vec3(0.0, 0.5, 0.70)
    table_sz = Vec3(1.5, 1.0, 0.05)
    grid.update_from_detection(table_top, table_sz, occupied=True)

    # Add objects on table
    objects = [
        (Vec3(-0.3, 0.4, 0.78), Vec3(0.08, 0.08, 0.12)),  # cup
        (Vec3(0.2, 0.5, 0.80), Vec3(0.06, 0.06, 0.20)),   # bottle
        (Vec3(-0.5, 0.6, 0.77), Vec3(0.12, 0.12, 0.06)),  # bowl
    ]
    for pos, sz in objects:
        grid.update_from_detection(pos, sz, occupied=True)

    grid.finalize()
    logger.info("[OccupancyGrid] Mock tabletop grid created")
    return grid
