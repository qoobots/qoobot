"""
brain_ai/perception/detector.py — Object detection via YOLOv11 ONNX.

Supports:
  - YOLOv11 ONNX runtime (via OnnxAdapter)
  - Mock fallback for development/testing
  - Batch inference with confidence filtering
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Single detection result."""
    label: str
    confidence: float        # [0, 1]
    bbox_xyxy: tuple[float, float, float, float]  # x1, y1, x2, y2 (normalized)
    class_id: int = 0
    mask: Optional[np.ndarray] = None  # instance mask (H, W)


class YOLODetector:
    """YOLOv11 object detector with ONNX backend and mock fallback.

    Usage::

        # 使用默认 ONNX 模型 (通过 model_registry 自动解析)
        det = YOLODetector()  # 自动查找 yolo11n.onnx
        # 或显式指定路径
        det = YOLODetector(model_path="/path/to/yolo11n.onnx")
        detections = det.detect(image_rgb, conf_threshold=0.5)
    """

    # COCO class labels (subset used by our simulated tabletop scene)
    COCO_LABELS: list[str] = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
        "truck", "boat", "traffic_light", "fire_hydrant", "stop_sign",
        "parking_meter", "bench", "bird", "cat", "dog", "horse", "sheep",
        "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
        "sports_ball", "kite", "baseball_bat", "baseball_glove", "skateboard",
        "surfboard", "tennis_racket", "bottle", "wine_glass", "cup", "fork",
        "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot_dog", "pizza", "donut", "cake", "chair",
        "couch", "potted_plant", "bed", "dining_table", "toilet", "tv",
        "laptop", "mouse", "remote", "keyboard", "cell_phone", "microwave",
        "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
        "scissors", "teddy_bear", "hair_drier", "toothbrush",
    ]

    def __init__(
        self,
        model_path: Optional[str] = None,
        conf_threshold: float = 0.5,
        nms_iou: float = 0.45,
        input_size: tuple[int, int] = (640, 640),
    ) -> None:
        self._model_path = model_path
        self._conf_threshold = conf_threshold
        self._nms_iou = nms_iou
        self._input_size = input_size
        self._model: Optional[object] = None  # OnnxModel when loaded

        if model_path:
            self._load_model(model_path)

    # ── Model management ────────────────────────────────────────────────

    def _load_model(self, path: str) -> None:
        """Load ONNX model via OnnxAdapter."""
        try:
            from brain_ai.model_runtime.onnx_adapter import OnnxAdapter

            adapter = OnnxAdapter()
            self._model = adapter.load_model("yolo_detector", path)
            if self._model.is_loaded:
                logger.info(f"[Detector] YOLO model loaded: {path}")
            else:
                logger.warning(f"[Detector] YOLO model failed to load: {path}")
        except ImportError:
            logger.warning("[Detector] onnxruntime not available — using mock")
        except Exception as exc:
            logger.warning(f"[Detector] Model load error: {exc}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._model.is_loaded

    # ── Inference ───────────────────────────────────────────────────────

    def detect(
        self,
        image: np.ndarray,
        conf_threshold: Optional[float] = None,
    ) -> list[Detection]:
        """Run detection on an RGB image (H, W, 3).

        Args:
            image: uint8 RGB image (H, W, 3)
            conf_threshold: override confidence threshold

        Returns:
            List of Detection objects sorted by confidence (desc)
        """
        thresh = conf_threshold if conf_threshold is not None else self._conf_threshold

        if self.is_ready:
            return self._detect_onnx(image, thresh)
        else:
            return self._detect_mock(image, thresh)

    def _detect_onnx(self, image: np.ndarray, thresh: float) -> list[Detection]:
        """Real ONNX inference path."""
        # Preprocess: resize, normalize, NCHW
        import cv2

        img = cv2.resize(image, self._input_size)
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)  # HWC → CHW
        img = np.expand_dims(img, axis=0)  # (1, 3, 640, 640)

        start = time.perf_counter()
        outputs = self._model.infer(img)  # type: ignore[union-attr]
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"[Detector] ONNX inference: {elapsed_ms:.1f}ms")

        return self._parse_yolo_output(outputs[0], thresh)

    def _detect_mock(self, image: np.ndarray, thresh: float) -> list[Detection]:
        """Mock detection — returns synthetic tabletop detections."""
        _ = image, thresh
        dets = [
            Detection("cup", 0.92, (0.3, 0.5, 0.5, 0.7), class_id=41),
            Detection("bottle", 0.88, (0.6, 0.55, 0.75, 0.72), class_id=40),
            Detection("bowl", 0.85, (0.15, 0.6, 0.35, 0.75), class_id=46),
            Detection("dining_table", 0.99, (0.0, 0.4, 1.0, 1.0), class_id=67),
        ]
        return sorted(dets, key=lambda d: d.confidence, reverse=True)

    def _parse_yolo_output(
        self, output: np.ndarray, thresh: float
    ) -> list[Detection]:
        """Parse YOLO raw output (N, 6) or (N, 85) format.

        Typical YOLO output shape: (N, 4 + 1 + num_classes)
        [cx, cy, w, h, obj_conf, cls_0, cls_1, ...]
        """
        detections: list[Detection] = []

        if output.ndim == 2 and output.shape[1] >= 6:
            for row in output:
                obj_conf = float(row[4])
                if obj_conf < thresh:
                    continue
                # Max class probability
                cls_probs = row[5:]
                cls_id = int(np.argmax(cls_probs))
                cls_conf = float(cls_probs[cls_id])
                conf = obj_conf * cls_conf
                if conf < thresh:
                    continue

                # cx, cy, w, h → xyxy
                cx, cy, w, h = row[:4]
                x1 = max(0.0, cx - w / 2)
                y1 = max(0.0, cy - h / 2)
                x2 = min(1.0, cx + w / 2)
                y2 = min(1.0, cy + h / 2)

                label = self.COCCO_LABELS[cls_id] if cls_id < len(self.COCCO_LABELS) else f"cls_{cls_id}"
                detections.append(Detection(
                    label=label, confidence=round(float(conf), 4),
                    bbox_xyxy=(x1, y1, x2, y2), class_id=int(cls_id),
                ))

        return sorted(detections, key=lambda d: d.confidence, reverse=True)

    def detect_batch(
        self, images: list[np.ndarray], conf_threshold: Optional[float] = None
    ) -> list[list[Detection]]:
        """Batch detection for multiple images."""
        return [self.detect(img, conf_threshold) for img in images]


class DetectorRegistry:
    """Registry for multiple detector backends (e.g. YOLO + custom)."""

    def __init__(self) -> None:
        self._detectors: dict[str, YOLODetector] = {}

    def register(self, name: str, detector: YOLODetector) -> None:
        self._detectors[name] = detector

    def get(self, name: str = "default") -> Optional[YOLODetector]:
        return self._detectors.get(name)

    @classmethod
    def create_default(cls, model_path: Optional[str] = None) -> DetectorRegistry:
        reg = cls()
        reg.register("default", YOLODetector(model_path=model_path))
        return reg
