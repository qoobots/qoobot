"""
qoodev data augmentation — auto label correction, few-shot augmentation, synthetic data generation.

对标：Albumentations + NVIDIA Data Loading Library (DALI)
提供标注纠错、少样本增强、合成数据生成流水线。
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AugmentationType(str, Enum):
    GEOMETRIC = "geometric"  # rotate, flip, crop, scale, translate
    PHOTOMETRIC = "photometric"  # brightness, contrast, saturation, noise
    SENSOR = "sensor"  # sensor noise, dropout, blur
    PHYSICAL = "physical"  # domain randomization (texture, lighting)
    MIXUP = "mixup"  # mixup / cutmix
    CUSTOM = "custom"


class SensorNoiseType(str, Enum):
    GAUSSIAN = "gaussian"
    SALT_PEPPER = "salt_pepper"
    POISSON = "poisson"
    SPECKLE = "speckle"
    DROPOUT = "dropout"  # random pixel dropout


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AugmentationConfig:
    """Configuration for a single augmentation."""
    name: str
    aug_type: AugmentationType
    probability: float = 0.5
    params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.probability = max(0.0, min(1.0, self.probability))


@dataclass
class AugmentationPipeline:
    """Ordered sequence of augmentations."""
    name: str
    steps: List[AugmentationConfig] = field(default_factory=list)
    seed: Optional[int] = None
    _rng: Optional[np.random.Generator] = None

    def __post_init__(self):
        self._rng = np.random.default_rng(self.seed)

    def add_step(self, step: AugmentationConfig) -> None:
        self.steps.append(step)

    def apply(self, data: np.ndarray, labels: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """Apply pipeline to data, optionally transforming labels."""
        result = data.copy()
        result_labels = labels.copy() if labels is not None else None

        for step in self.steps:
            if self._rng.random() > step.probability:
                continue

            if step.aug_type == AugmentationType.GEOMETRIC:
                result, result_labels = self._apply_geometric(result, step.params, result_labels)
            elif step.aug_type == AugmentationType.PHOTOMETRIC:
                result = self._apply_photometric(result, step.params)
            elif step.aug_type == AugmentationType.SENSOR:
                result = self._apply_sensor_noise(result, step.params)
            elif step.aug_type == AugmentationType.PHYSICAL:
                result = self._apply_physical(result, step.params)
            elif step.aug_type == AugmentationType.MIXUP:
                result, result_labels = self._apply_mixup(result, step.params, result_labels)

        return result, result_labels

    # -- geometric ----------------------------------------------------------

    def _apply_geometric(
        self, data: np.ndarray, params: Dict[str, Any], labels: Optional[np.ndarray]
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        h, w = data.shape[-2], data.shape[-1]

        # rotation
        angle = params.get("angle", self._rng.uniform(-15, 15))
        if abs(angle) > 0.01 and len(data.shape) >= 3:
            from scipy.ndimage import rotate  # type: ignore
            data = rotate(data, angle, axes=(-2, -1), reshape=False)

        # horizontal flip
        if params.get("horizontal_flip", False) and self._rng.random() > 0.5:
            data = np.flip(data, axis=-1)
            if labels is not None and len(labels.shape) >= 2:
                labels = np.flip(labels, axis=-1)

        # vertical flip
        if params.get("vertical_flip", False) and self._rng.random() > 0.5:
            data = np.flip(data, axis=-2)
            if labels is not None and len(labels.shape) >= 2:
                labels = np.flip(labels, axis=-2)

        # random crop + resize
        crop_ratio = params.get("crop_ratio", None)
        if crop_ratio is not None:
            ch, cw = int(h * crop_ratio), int(w * crop_ratio)
            y0 = self._rng.integers(0, h - ch + 1)
            x0 = self._rng.integers(0, w - cw + 1)
            data = data[..., y0:y0 + ch, x0:x0 + cw]
            # resize back
            from scipy.ndimage import zoom  # type: ignore
            scale = np.array([1] * (len(data.shape) - 2) + [h / ch, w / cw])
            data = zoom(data, scale)
            if labels is not None:
                labels = labels[..., y0:y0 + ch, x0:x0 + cw]
                scale_l = np.array([1] * (len(labels.shape) - 2) + [h / ch, w / cw])
                labels = zoom(labels, scale_l)

        return data, labels

    # -- photometric --------------------------------------------------------

    def _apply_photometric(self, data: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        result = data.astype(np.float32)

        # brightness
        brightness_delta = params.get("brightness_delta", 0.0)
        if abs(brightness_delta) > 0.001:
            result += brightness_delta

        # contrast
        contrast_alpha = params.get("contrast_alpha", 1.0)
        if abs(contrast_alpha - 1.0) > 0.001:
            mean = result.mean()
            result = contrast_alpha * (result - mean) + mean

        # saturation (RGB images only)
        saturation = params.get("saturation", 1.0)
        if abs(saturation - 1.0) > 0.001 and result.shape[-3] == 3:
            gray = result.mean(axis=-3, keepdims=True)
            result = saturation * result + (1 - saturation) * gray

        return np.clip(result, 0, 255 if data.dtype == np.uint8 else None)

    # -- sensor noise -------------------------------------------------------

    def _apply_sensor_noise(self, data: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        noise_type = SensorNoiseType(params.get("noise_type", "gaussian"))
        std = params.get("std", 0.05)
        result = data.astype(np.float32)

        if noise_type == SensorNoiseType.GAUSSIAN:
            noise = self._rng.normal(0, std * result.std(), result.shape)
            result += noise
        elif noise_type == SensorNoiseType.SALT_PEPPER:
            prob = params.get("prob", 0.02)
            mask = self._rng.random(result.shape) < prob
            salt = self._rng.random(result.shape) < 0.5
            result[mask & salt] = result.max()
            result[mask & ~salt] = result.min()
        elif noise_type == SensorNoiseType.POISSON:
            result = self._rng.poisson(np.maximum(result, 0)) / result.max() * result.max()
        elif noise_type == SensorNoiseType.SPECKLE:
            noise = self._rng.normal(0, std, result.shape)
            result += result * noise
        elif noise_type == SensorNoiseType.DROPOUT:
            prob = params.get("prob", 0.05)
            mask = self._rng.random(result.shape) > prob
            result *= mask

        # blur
        if params.get("blur_sigma", 0) > 0:
            from scipy.ndimage import gaussian_filter  # type: ignore
            result = gaussian_filter(result, sigma=params["blur_sigma"])

        return np.clip(result, 0, 255 if data.dtype == np.uint8 else None)

    # -- physical (domain randomization) ------------------------------------

    def _apply_physical(self, data: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        result = data.astype(np.float32)

        # lighting variation (simulate different illumination)
        lighting_scale = params.get("lighting_scale", (0.5, 2.0))
        if isinstance(lighting_scale, (list, tuple)):
            scale = self._rng.uniform(*lighting_scale)
            result *= scale

        # shadow simulation
        if params.get("shadow", False) and self._rng.random() > 0.5:
            h, w = result.shape[-2:]
            shadow_mask = np.ones((h, w), dtype=np.float32)
            # random shadow bar
            y0 = self._rng.integers(0, h)
            shadow_h = self._rng.integers(h // 8, h // 3)
            shadow_mask[y0:min(y0 + shadow_h, h), :] = self._rng.uniform(0.3, 0.7)
            result = result * shadow_mask[..., np.newaxis] if result.ndim == 3 else result * shadow_mask

        # texture randomization placeholder
        if params.get("texture_noise", 0.0) > 0:
            noise = self._rng.normal(0, params["texture_noise"], result.shape)
            result += noise

        return np.clip(result, 0, 255 if data.dtype == np.uint8 else None)

    # -- mixup --------------------------------------------------------------

    def _apply_mixup(
        self, data: np.ndarray, params: Dict[str, Any], labels: Optional[np.ndarray]
    ) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        # mixup requires a second sample — use self-mixup with shifted version
        alpha = params.get("alpha", 0.2)
        lam = self._rng.beta(alpha, alpha) if alpha > 0 else 1.0

        # create shifted version
        shift = self._rng.integers(1, max(1, data.shape[-1] // 4))
        shifted = np.roll(data, shift, axis=-1)

        result = lam * data + (1 - lam) * shifted
        if labels is not None:
            shifted_labels = np.roll(labels, shift, axis=-1)
            labels = lam * labels + (1 - lam) * shifted_labels

        return result, labels


# ---------------------------------------------------------------------------
# Few-shot augmentation
# ---------------------------------------------------------------------------

class FewShotAugmenter:
    """Generate augmented samples for few-shot learning scenarios."""

    def __init__(self, pipeline: AugmentationPipeline, n_augmentations: int = 10):
        self.pipeline = pipeline
        self.n_augmentations = n_augmentations

    def augment(
        self, sample: np.ndarray, label: Optional[np.ndarray] = None
    ) -> List[Tuple[np.ndarray, Optional[np.ndarray]]]:
        """Generate n augmented variants of a single sample."""
        variants: List[Tuple[np.ndarray, Optional[np.ndarray]]] = []
        for i in range(self.n_augmentations):
            aug, aug_label = self.pipeline.apply(sample, label)
            variants.append((aug, aug_label))
        return variants


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------

class SyntheticDataGenerator:
    """Generate synthetic training data via procedural methods."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = np.random.default_rng(seed)

    def generate_image_classification(
        self,
        n_samples: int,
        image_size: Tuple[int, int] = (224, 224),
        n_classes: int = 10,
        channels: int = 3,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic image classification dataset."""
        images = self._rng.uniform(0, 255, (n_samples, channels, *image_size)).astype(np.uint8)
        labels = self._rng.integers(0, n_classes, n_samples)
        # add class-conditional structure
        for c in range(n_classes):
            mask = labels == c
            images[mask] = images[mask] * 0.5 + c * 25
        return images, labels

    def generate_trajectory_data(
        self,
        n_trajectories: int,
        length: int = 100,
        dim: int = 6,
        noise_std: float = 0.01,
    ) -> np.ndarray:
        """Generate synthetic robot trajectories (e.g. end-effector poses)."""
        trajectories = np.zeros((n_trajectories, length, dim))

        for i in range(n_trajectories):
            # random start and goal
            start = self._rng.uniform(-1, 1, dim)
            goal = self._rng.uniform(-1, 1, dim)

            # linear interpolation with sinusoidal perturbations
            for t in range(length):
                alpha = t / (length - 1)
                base = start * (1 - alpha) + goal * alpha
                perturbation = 0.1 * np.sin(self._rng.uniform(1, 5) * alpha * np.pi + self._rng.uniform(0, 2 * np.pi))
                noise = self._rng.normal(0, noise_std, dim)
                trajectories[i, t] = base + perturbation + noise

        return trajectories

    def generate_lidar_pointcloud(
        self,
        n_points: int = 50000,
        range_m: float = 100.0,
    ) -> np.ndarray:
        """Generate synthetic LiDAR point cloud."""
        # spherical coordinates
        theta = self._rng.uniform(0, 2 * np.pi, n_points)
        phi = self._rng.uniform(-np.pi / 6, np.pi / 6, n_points)  # ±30° vertical FOV
        r = self._rng.uniform(0.5, range_m, n_points)

        # convert to Cartesian
        x = r * np.cos(phi) * np.cos(theta)
        y = r * np.cos(phi) * np.sin(theta)
        z = r * np.sin(phi)

        return np.stack([x, y, z], axis=1)

    def generate_imu_stream(
        self,
        duration_s: float = 10.0,
        sample_rate_hz: float = 200.0,
    ) -> Dict[str, np.ndarray]:
        """Generate synthetic IMU data stream."""
        n = int(duration_s * sample_rate_hz)
        t = np.linspace(0, duration_s, n)

        # accelerometer (m/s²)
        accel = np.column_stack([
            self._rng.normal(0, 0.01, n) + 0.1 * np.sin(2 * np.pi * 1.0 * t),  # x
            self._rng.normal(0, 0.01, n) + 0.1 * np.cos(2 * np.pi * 1.0 * t),  # y
            self._rng.normal(0, 0.01, n) + 9.81,  # z (gravity)
        ])

        # gyroscope (rad/s)
        gyro = np.column_stack([
            self._rng.normal(0, 0.005, n),  # x
            self._rng.normal(0, 0.005, n),  # y
            self._rng.normal(0, 0.005, n),  # z
        ])

        return {"timestamp": t, "accel": accel, "gyro": gyro}


# ---------------------------------------------------------------------------
# Auto label correction
# ---------------------------------------------------------------------------

class LabelCorrector:
    """Detect and correct annotation errors using consensus methods."""

    @staticmethod
    def detect_outliers(
        embeddings: np.ndarray,
        labels: np.ndarray,
        n_std: float = 3.0,
    ) -> np.ndarray:
        """Detect samples whose embeddings are outliers within their class."""
        outlier_mask = np.zeros(len(labels), dtype=bool)

        for c in np.unique(labels):
            class_mask = labels == c
            class_embeddings = embeddings[class_mask]

            if len(class_embeddings) < 3:
                continue

            centroid = class_embeddings.mean(axis=0)
            distances = np.linalg.norm(class_embeddings - centroid, axis=1)
            threshold = distances.mean() + n_std * distances.std()

            class_outliers = distances > threshold
            outlier_mask[class_mask] = class_outliers

        return outlier_mask

    @staticmethod
    def cross_validation_consensus(
        predictions_list: List[np.ndarray],
        threshold: float = 0.8,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Find samples where multiple models disagree — candidates for re-labeling."""
        n_samples = len(predictions_list[0])
        consensus_labels = np.zeros(n_samples, dtype=np.int64)
        confidence = np.zeros(n_samples)

        for i in range(n_samples):
            votes: Dict[int, int] = {}
            for preds in predictions_list:
                label = int(np.argmax(preds[i]))
                votes[label] = votes.get(label, 0) + 1

            best_label = max(votes, key=votes.get)
            consensus_labels[i] = best_label
            confidence[i] = votes[best_label] / len(predictions_list)

        uncertain_mask = confidence < threshold
        return consensus_labels, uncertain_mask
