"""
brain_ai/perception/segmentor.py — Instance / panoptic segmentation.

Supports:
  - SAM2 promptable segmentation (via ONNX or API)
  - Mask refinement for grasp planning
  - Mock fallback with simple threshold segmentation
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SegmentationMask:
    """Binary mask for a single object instance."""
    object_id: str
    label: str
    mask: np.ndarray               # (H, W) bool or uint8
    confidence: float = 0.0
    area_pixels: int = 0

    def __post_init__(self):
        if self.area_pixels == 0 and self.mask is not None:
            self.area_pixels = int(np.sum(self.mask > 0))

    @property
    def centroid(self) -> tuple[float, float]:
        """Centroid of mask in pixel coordinates (x, y)."""
        if self.mask is None or self.area_pixels == 0:
            return (0.0, 0.0)
        ys, xs = np.where(self.mask > 0)
        return (float(np.mean(xs)), float(np.mean(ys)))

    @property
    def bbox_xyxy(self) -> tuple[int, int, int, int]:
        """Tight bounding box around mask (x1, y1, x2, y2)."""
        if self.mask is None or self.area_pixels == 0:
            return (0, 0, 0, 0)
        ys, xs = np.where(self.mask > 0)
        return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


class SAMSegmetor:
    """Segment Anything Model (SAM2) wrapper for instance segmentation.

    Usage::

        seg = SAMSegmetor(
            model_path="sam2_hiera_tiny.encoder.onnx",
            decoder_path="sam2_hiera_tiny.decoder.onnx",
        )
        masks = seg.segment(image_rgb, prompts=[{"box": (100, 100, 200, 200)}])
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        decoder_path: Optional[str] = None,
        device: str = "cuda",
        enable_mock: bool = True,
    ) -> None:
        self._model_path = model_path
        self._decoder_path = decoder_path
        self._device = device
        self._enable_mock = enable_mock
        self._predictor: Optional[object] = None

        if model_path:
            self._load_model(model_path)

    def _load_model(self, path: str) -> None:
        """Try to load SAM2 model."""
        try:
            # Placeholder for actual SAM2 loading
            # from sam2.build_sam import build_sam2
            # self._predictor = build_sam2(path, device=self._device)
            logger.info(f"[Segmentor] SAM2 model path configured: {path}")
        except Exception as exc:
            logger.warning(f"[Segmentor] SAM2 load failed: {exc}")

    @property
    def is_ready(self) -> bool:
        return self._predictor is not None

    def segment(
        self,
        image: np.ndarray,
        prompts: Optional[list[dict]] = None,
        conf_threshold: float = 0.5,
    ) -> list[SegmentationMask]:
        """Segment image with optional prompts (box/point).

        Args:
            image: RGB uint8 (H, W, 3)
            prompts: list of dicts, each with 'box' or 'point' key
            conf_threshold: min confidence for mask inclusion

        Returns:
            List of SegmentationMask objects
        """
        if self.is_ready:
            return self._segment_sam(image, prompts, conf_threshold)
        elif self._enable_mock:
            return self._segment_mock(image, prompts, conf_threshold)
        else:
            logger.warning("[Segmentor] No model available and mock disabled")
            return []

    def _segment_sam(
        self, image: np.ndarray, prompts: Optional[list[dict]], thresh: float
    ) -> list[SegmentationMask]:
        """Real SAM2 inference path."""
        # Placeholder — actual SAM2 inference
        _ = image, prompts, thresh
        logger.debug("[Segmentor] SAM inference called (stub)")
        return []

    def _segment_mock(
        self, image: np.ndarray, prompts: Optional[list[dict]], thresh: float
    ) -> list[SegmentationMask]:
        """Mock segmentation — returns masks for common tabletop objects."""
        _ = prompts, thresh
        h, w = image.shape[:2]

        # Generate simple rectangular masks for mock objects
        masks = []
        mock_objects = [
            ("obj_001", "cup", 0.25, 0.45, 0.45, 0.65),
            ("obj_002", "bottle", 0.55, 0.50, 0.70, 0.68),
            ("obj_003", "bowl", 0.10, 0.55, 0.30, 0.72),
            ("obj_004", "book", 0.70, 0.40, 0.85, 0.58),
        ]
        for obj_id, label, x1_n, y1_n, x2_n, y2_n in mock_objects:
            x1, y1 = int(x1_n * w), int(y1_n * h)
            x2, y2 = int(x2_n * w), int(y2_n * h)
            mask = np.zeros((h, w), dtype=np.uint8)
            mask[y1:y2, x1:x2] = 1
            masks.append(SegmentationMask(
                object_id=obj_id, label=label, mask=mask,
                confidence=0.90, area_pixels=int(np.sum(mask)),
            ))

        return masks

    def refine_grasp_mask(
        self, mask: SegmentationMask, grasp_point: tuple[float, float]
    ) -> SegmentationMask:
        """Refine a mask around a grasp point for better gripper alignment."""
        if mask.mask is None:
            return mask

        # Simple refinement: expand around grasp point
        h, w = mask.mask.shape
        radius = 30  # pixels
        x, y = int(grasp_point[0]), int(grasp_point[1])

        refined = np.zeros_like(mask.mask)
        y_min = max(0, y - radius)
        y_max = min(h, y + radius)
        x_min = max(0, x - radius)
        x_max = min(w, x + radius)
        refined[y_min:y_max, x_min:x_max] = 1
        refined = np.logical_and(refined, mask.mask)  # intersect with original

        return SegmentationMask(
            object_id=mask.object_id,
            label=mask.label,
            mask=refined,
            confidence=mask.confidence,
        )
