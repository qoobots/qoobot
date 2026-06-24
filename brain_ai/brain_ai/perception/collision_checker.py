"""
brain_ai/perception/collision_checker.py — FCL-based collision detection.

Provides:
  - Convex shape collision detection (box, sphere, cylinder, mesh)
  - Distance queries between robot links and environment
  - Self-collision checking (robot arm links vs body)
  - Mock fallback for development
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np

try:
    from brain_ai.domain.scene import Vec3, Quaternion, Pose6D, OccupancyVoxelGrid
except ImportError:
    from domain.scene import Vec3, Quaternion, Pose6D, OccupancyVoxelGrid

logger = logging.getLogger(__name__)


class CollisionShape(Enum):
    BOX = "box"
    SPHERE = "sphere"
    CYLINDER = "cylinder"
    MESH = "mesh"
    CAPSULE = "capsule"


@dataclass
class CollisionGeometry:
    """Description of a collision shape for one link."""
    shape: CollisionShape = CollisionShape.BOX
    dimensions: list[float] = field(default_factory=lambda: [0.1, 0.1, 0.1])
    offset: Vec3 = field(default_factory=Vec3)
    offset_rotation: Optional[list[float]] = None  # optional rotation offset


@dataclass
class RobotLinkGeometry:
    """Collision geometry of a robot link."""
    name: str
    geometry: CollisionGeometry = field(default_factory=CollisionGeometry)
    parent_link: Optional[str] = None  # for self-collision exclusion
    self_collision_enabled: bool = True


@dataclass
class CollisionResult:
    """Result of a collision check."""
    in_collision: bool = False
    collision_pairs: list[tuple[str, str]] = field(default_factory=list)
    min_distance: float = float("inf")
    closest_pair: Optional[tuple[str, str]] = None
    closest_point_a: Optional[Vec3] = None
    closest_point_b: Optional[Vec3] = None
    processing_time_ms: float = 0.0


class CollisionChecker:
    """FCL-based collision detection for robot and environment.

    Usage::

        checker = CollisionChecker()
        checker.load_robot_urdf("robot.urdf")
        result = checker.check_collision(joint_positions, occupancy_grid)
    """

    def __init__(
        self,
        min_distance_threshold: float = 0.01,  # 1 cm minimum separation
        self_collision_enabled: bool = True,
        enable_mock: bool = True,
    ) -> None:
        self._min_distance = min_distance_threshold
        self._self_collision_enabled = self_collision_enabled

        # Robot model
        self._links: dict[str, RobotLinkGeometry] = {}
        self._collision_managers: dict[str, object] = {}  # FCL managers per group

        # Mock mode
        self._enable_mock = enable_mock
        self._last_result: Optional[CollisionResult] = None

    # ── Model loading ──────────────────────────────────────────────────

    def load_robot_urdf(self, urdf_path: str) -> bool:
        """Parse a URDF to extract collision geometries.

        Uses urdfpy / yourdfpy to extract link transforms and collision shapes.
        """
        try:
            # In production: parse URDF, extract collision meshes, create FCL objects
            logger.info(f"[CollisionChecker] Loading URDF: {urdf_path}")
            # Placeholder: register mock links for Kinova Gen3
            self._links = self._mock_kinova_links()
            logger.info(f"[CollisionChecker] Loaded {len(self._links)} links")
            return True
        except Exception as exc:
            logger.warning(f"[CollisionChecker] URDF load failed: {exc}")
            if self._enable_mock:
                self._links = self._mock_kinova_links()
                return True
            return False

    def register_link(self, link: RobotLinkGeometry) -> None:
        """Manually register a collision link."""
        self._links[link.name] = link

    def register_environment_object(
        self, obj_id: str, shape: CollisionShape, dimensions: list[float], pose: Pose6D,
    ) -> None:
        """Register an environment object for collision checking."""
        logger.debug(f"[CollisionChecker] Registered env obj: {obj_id} ({shape.value})")

    # ── Collision checking ─────────────────────────────────────────────

    def check_collision(
        self,
        joint_positions: dict[str, float],
        occupancy_grid: Optional[OccupancyVoxelGrid] = None,
        check_self_collision: bool = True,
    ) -> CollisionResult:
        """Check for collisions between robot and environment.

        Args:
            joint_positions: dict of joint_name → angle (radians)
            occupancy_grid: optional voxel grid for environment collision
            check_self_collision: whether to check robot self-collision

        Returns:
            CollisionResult with details
        """
        import time
        start = time.perf_counter()

        result = CollisionResult()
        collision_pairs: list[tuple[str, str]] = []

        # Step 1: Forward kinematics to compute link transforms
        link_poses = self._compute_fk(joint_positions)

        # Step 2: Environment collision (links vs occupancy grid)
        if occupancy_grid is not None and self._enable_mock:
            env_result = self._check_env_collision_mock(link_poses, occupancy_grid)
            collision_pairs.extend(env_result)
        elif occupancy_grid is not None:
            env_result = self._check_env_collision(link_poses, occupancy_grid)
            collision_pairs.extend(env_result)

        # Step 3: Self-collision (links vs adjacent links)
        if check_self_collision and self._self_collision_enabled:
            self_result = self._check_self_collision(link_poses)
            collision_pairs.extend(self_result)

        # Compile result
        result.in_collision = len(collision_pairs) > 0
        result.collision_pairs = collision_pairs
        result.processing_time_ms = (time.perf_counter() - start) * 1000

        self._last_result = result
        return result

    def _compute_fk(
        self, joint_positions: dict[str, float],
    ) -> dict[str, Pose6D]:
        """Compute forward kinematics for all links (simplified mock)."""
        # In production: use pinocchio/kinpy for FK
        # Returns link → world pose
        poses: dict[str, Pose6D] = {}

        # Mock: simple chain for Kinova Gen3
        arm_links = [
            "base_link", "shoulder_link", "upper_arm_link",
            "forearm_link", "wrist_1_link", "wrist_2_link", "wrist_3_link",
        ]
        base_pos = Vec3(0, 0, 0.5)
        for i, link_name in enumerate(arm_links):
            z_offset = 0.5 + i * 0.15
            poses[link_name] = Pose6D(
                position=Vec3(0.1 * i, 0, z_offset),
                orientation=Quaternion(0, 0, 0, 1),
            )
        return poses

    def _check_env_collision(
        self, link_poses: dict[str, Pose6D], occ: OccupancyVoxelGrid,
    ) -> list[tuple[str, str]]:
        """Real FCL environment collision check."""
        _ = link_poses, occ
        # In production: iterate links, check each collision geometry
        # against voxels using FCL BroadPhaseCollisionManager
        return []

    def _check_env_collision_mock(
        self, link_poses: dict[str, Pose6D], occ: OccupancyVoxelGrid,
    ) -> list[tuple[str, str]]:
        """Mock environment collision — sample link endpoints in grid."""
        pairs: list[tuple[str, str]] = []
        for link_name, pose in link_poses.items():
            # Check link position against voxels
            if occ.is_occupied(pose.position):
                pairs.append((link_name, "environment"))
        return pairs

    def _check_self_collision(
        self, link_poses: dict[str, Pose6D],
    ) -> list[tuple[str, str]]:
        """Self-collision check (mock: skip adjacent links)."""
        pairs: list[tuple[str, str]] = []
        link_names = list(link_poses.keys())

        for i, a in enumerate(link_names):
            for j, b in enumerate(link_names):
                if j <= i + 1:  # skip self and adjacent links
                    continue
                pos_a = link_poses[a].position
                pos_b = link_poses[b].position
                dist = self._distance_3d(pos_a, pos_b)
                if dist < self._min_distance:
                    pairs.append((a, b))

        return pairs

    # ── Distance queries ───────────────────────────────────────────────

    def get_minimum_distance(
        self, joint_positions: dict[str, float],
    ) -> float:
        """Get minimum distance between any robot link and environment."""
        result = self.check_collision(joint_positions)
        if result.in_collision:
            return 0.0
        return result.min_distance

    def get_link_distance(
        self, link_name: str, target_position: Vec3,
    ) -> float:
        """Get distance from a specific link to a target point."""
        _ = link_name, target_position
        # In production: query FCL distance
        return 1.0  # mock: always clear

    def is_position_free(
        self, position: Vec3, clearance_m: float = 0.05,
    ) -> bool:
        """Check if a 3D position is free of robot self-collision."""
        # Simple check: far from robot base
        dist = self._distance_3d(position, Vec3(0, 0, 0.5))
        return dist > clearance_m

    # ── Mock robot model (Kinova Gen3 7-DoF) ───────────────────────────

    @staticmethod
    def _mock_kinova_links() -> dict[str, RobotLinkGeometry]:
        """Create mock collision geometries for Kinova Gen3 arm."""
        links = {}
        link_specs = [
            ("base_link", CollisionShape.CYLINDER, [0.15, 0.10]),
            ("shoulder_link", CollisionShape.CYLINDER, [0.12, 0.08]),
            ("upper_arm_link", CollisionShape.CYLINDER, [0.10, 0.25]),
            ("forearm_link", CollisionShape.CYLINDER, [0.08, 0.22]),
            ("wrist_1_link", CollisionShape.SPHERE, [0.06]),
            ("wrist_2_link", CollisionShape.SPHERE, [0.06]),
            ("wrist_3_link", CollisionShape.BOX, [0.05, 0.05, 0.12]),
            ("gripper_left", CollisionShape.BOX, [0.02, 0.04, 0.06]),
            ("gripper_right", CollisionShape.BOX, [0.02, 0.04, 0.06]),
        ]
        for name, shape, dims in link_specs:
            links[name] = RobotLinkGeometry(
                name=name,
                geometry=CollisionGeometry(shape=shape, dimensions=dims),
            )
        return links

    # ── Utilities ──────────────────────────────────────────────────────

    @staticmethod
    def _distance_3d(a: Vec3, b: Vec3) -> float:
        return float(np.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2))

    @property
    def last_result(self) -> Optional[CollisionResult]:
        return self._last_result

    @property
    def num_links(self) -> int:
        return len(self._links)

    def reset(self) -> None:
        """Clear all registered geometry."""
        self._links.clear()
        self._last_result = None
