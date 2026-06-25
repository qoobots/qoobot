"""
brain_ai/perception/gs_reconstructor.py — 3D Gaussian Splatting scene reconstruction.

Provides:
  - 3DGS training from multi-view images
  - Real-time splat rendering
  - Novel-view synthesis for HITL preview
  - Mock fallback with simple point cloud
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

try:
    from brain_ai.domain.scene import Vec3
except ImportError:
    from domain.scene import Vec3

logger = logging.getLogger(__name__)


@dataclass
class GaussianSplat:
    """Single 3D Gaussian primitive."""
    position: tuple[float, float, float] = (0, 0, 0)
    covariance: tuple[float, ...] = (1, 0, 0, 0, 1, 0, 0, 0, 1)  # 3x3 matrix
    color: tuple[float, float, float] = (0.5, 0.5, 0.5)
    opacity: float = 1.0
    scale: tuple[float, float, float] = (0.05, 0.05, 0.05)


@dataclass
class SplatCloud:
    """Collection of 3D Gaussian splats forming a scene."""
    splats: list[GaussianSplat] = field(default_factory=list)
    bounds: tuple[Vec3, Vec3] = field(default_factory=lambda: (
        Vec3(-1, -1, 0), Vec3(1, 1, 2)
    ))
    training_iterations: int = 0
    loss: float = float("inf")

    @property
    def num_splats(self) -> int:
        return len(self.splats)

    def to_numpy(self) -> dict[str, np.ndarray]:
        """Export splats as numpy arrays for rendering."""
        if not self.splats:
            return {}
        n = len(self.splats)
        return {
            "positions": np.array([s.position for s in self.splats], dtype=np.float32),
            "colors": np.array([s.color for s in self.splats], dtype=np.float32),
            "opacities": np.array([s.opacity for s in self.splats], dtype=np.float32),
            "scales": np.array([s.scale for s in self.splats], dtype=np.float32),
        }


class GSReconstructor:
    """3D Gaussian Splatting scene reconstructor.

    Reconstructs dense 3D scenes from multi-view RGB images and poses.
    Used for high-fidelity scene visualization in brain_viz.

    Usage::

        recon = GSReconstructor()
        splat_cloud = recon.train(images, poses, intrinsics)
        novel_view = recon.render(splat_cloud, target_pose)
    """

    def __init__(
        self,
        num_iterations: int = 7000,
        densify_interval: int = 100,
        device: str = "cuda",
        enable_mock: bool = True,
    ) -> None:
        self._num_iterations = num_iterations
        self._densify_interval = densify_interval
        self._device = device
        self._enable_mock = enable_mock
        self._latest_cloud: Optional[SplatCloud] = None

    # ── Training ──────────────────────────────────────────────────────

    def train(
        self,
        images: list[np.ndarray],
        poses: list[list[float]],  # each is 4x4 SE3 matrix as 16 floats
        intrinsics: Optional[dict] = None,
        initial_points: Optional[np.ndarray] = None,
    ) -> SplatCloud:
        """Train 3DGS from multi-view images and camera poses.

        Args:
            images: list of RGB images (H, W, 3)
            poses: list of camera-to-world 4x4 SE3 matrices (flattened)
            intrinsics: camera intrinsics dict {fx, fy, cx, cy, w, h}
            initial_points: optional initial point cloud (N, 3) for initialization

        Returns:
            Trained SplatCloud
        """
        n_views = len(images)
        logger.info(f"[GSReconstructor] Training from {n_views} views")

        if n_views < 2:
            logger.warning("[GSReconstructor] Need at least 2 views for 3DGS")
            return self._mock_cloud()

        # In production: actual 3DGS training loop
        # from gsplat import GaussianModel, Trainer
        # model = GaussianModel(...)
        # trainer = Trainer(model, ...)
        # trainer.train(images, poses)

        logger.info(f"[GSReconstructor] Stub training: {self._num_iterations} iters")
        return self._mock_cloud(initial_points)

    def incremental_update(
        self,
        image: np.ndarray,
        pose: list[float],
        intrinsics: Optional[dict] = None,
    ) -> SplatCloud:
        """Incremental update with a single new view (streaming mode)."""
        logger.debug("[GSReconstructor] Incremental update")
        # In production: few-shot fine-tuning
        return self._mock_cloud()

    # ── Rendering ─────────────────────────────────────────────────────

    def render(
        self,
        cloud: Optional[SplatCloud] = None,
        target_pose: Optional[list[float]] = None,
        resolution: tuple[int, int] = (640, 480),
    ) -> Optional[np.ndarray]:
        """Render novel view of the 3DGS scene.

        Args:
            cloud: SplatCloud to render (uses latest if None)
            target_pose: camera pose for the novel view (4x4 SE3)
            resolution: output image size (W, H)

        Returns:
            Rendered RGB image (H, W, 3)
        """
        cloud = cloud or self._latest_cloud
        if cloud is None or not cloud.splats:
            logger.warning("[GSReconstructor] No splat cloud to render")
            return None

        # In production: splat rendering
        # rendered = rasterize_splats(cloud.splats, target_pose, resolution)
        h, w = resolution[1], resolution[0]
        # Return a gray placeholder
        return np.full((h, w, 3), 128, dtype=np.uint8)

    # ── Mock ──────────────────────────────────────────────────────────

    def _mock_cloud(
        self, seed_points: Optional[np.ndarray] = None,
    ) -> SplatCloud:
        """Generate a synthetic splat cloud for tabletop scene."""
        splats = []

        # Table surface: small splats forming a plane
        for x in np.linspace(-0.6, 0.6, 13):
            for y in np.linspace(0.2, 1.0, 9):
                splats.append(GaussianSplat(
                    position=(float(x), float(y), 0.70),
                    covariance=(0.02, 0, 0, 0, 0.02, 0, 0, 0, 0.005),
                    color=(0.6, 0.5, 0.4),
                    opacity=0.95,
                    scale=(0.04, 0.04, 0.01),
                ))

        # Cup: cylinder at (-0.3, 0.5)
        for z in np.linspace(0.72, 0.82, 5):
            for angle in np.linspace(0, 2 * np.pi, 12):
                r = 0.04
                splats.append(GaussianSplat(
                    position=(-0.3 + r * np.cos(angle), 0.5 + r * np.sin(angle), float(z)),
                    color=(0.9, 0.2, 0.2),  # red
                    opacity=0.9,
                    scale=(0.02, 0.02, 0.02),
                ))

        # Bottle at (0.2, 0.6)
        for z in np.linspace(0.72, 0.90, 6):
            r = 0.03
            for angle in np.linspace(0, 2 * np.pi, 8):
                splats.append(GaussianSplat(
                    position=(0.2 + r * np.cos(angle), 0.6 + r * np.sin(angle), float(z)),
                    color=(0.2, 0.6, 0.9),  # blue
                    opacity=0.9,
                    scale=(0.02, 0.02, 0.02),
                ))

        cloud = SplatCloud(
            splats=splats,
            bounds=(Vec3(-1, 0, 0), Vec3(1, 1.5, 1.2)),
            training_iterations=0,
            loss=0.0,
        )
        self._latest_cloud = cloud
        logger.info(f"[GSReconstructor] Mock cloud: {cloud.num_splats} splats")
        return cloud

    # ── Export ────────────────────────────────────────────────────────

    def export_ply(self, cloud: Optional[SplatCloud] = None, path: str = "") -> Optional[str]:
        """Export splat cloud as PLY file for visualization."""
        cloud = cloud or self._latest_cloud
        if cloud is None:
            return None
        # In production: write PLY with xyz + f_dc + opacity + scale + rot
        logger.info(f"[GSReconstructor] PLY export stub: {cloud.num_splats} splats")
        return path

    @property
    def latest_cloud(self) -> Optional[SplatCloud]:
        return self._latest_cloud
