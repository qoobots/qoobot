"""
brain_ai/perception/ — Perception pipeline modules.

Exports:
  - YOLODetector:       object detection (YOLOv11 ONNX)
  - SAMSegmetor:        instance segmentation (SAM2)
  - SLAMWrapper:        visual SLAM (ORB-SLAM3)
  - PoseEstimator:      6-DoF object pose estimation
  - OccupancyGrid:      3D occupancy map
  - GSReconstructor:    3D Gaussian Splatting reconstruction
  - SceneAggregator:    multi-sensor fusion → SceneGraph
  - TrackManager:       multi-frame object tracking
  - CollisionChecker:   collision detection (FCL)
"""
from .detector import (
    Detection,
    YOLODetector,
    DetectorRegistry,
)
from .segmentor import (
    SegmentationMask,
    SAMSegmetor,
)
from .slam_wrapper import (
    SLAMState,
    MapPoint,
    KeyFrame,
    SLAMWrapper,
)
from .pose_estimator import (
    PoseEstimate,
    PoseEstimator,
)
from .occupancy_net import (
    OccupancyGrid,
    create_tabletop_mock_grid,
)
from .gs_reconstructor import (
    GaussianSplat,
    SplatCloud,
    GSReconstructor,
)
from .scene_aggregator import (
    PerceptionFrame,
    SceneAggregator,
)
from .track_manager import (
    TrackState,
    Track,
    TrackManager,
)
from .collision_checker import (
    CollisionShape,
    CollisionGeometry,
    RobotLinkGeometry,
    CollisionResult,
    CollisionChecker,
)

__all__ = [
    # Detector
    "Detection",
    "YOLODetector",
    "DetectorRegistry",
    # Segmentor
    "SegmentationMask",
    "SAMSegmetor",
    # SLAM
    "SLAMState",
    "MapPoint",
    "KeyFrame",
    "SLAMWrapper",
    # Pose
    "PoseEstimate",
    "PoseEstimator",
    # Occupancy
    "OccupancyGrid",
    "create_tabletop_mock_grid",
    # 3DGS
    "GaussianSplat",
    "SplatCloud",
    "GSReconstructor",
    # Aggregation
    "PerceptionFrame",
    "SceneAggregator",
    # Tracking
    "TrackState",
    "Track",
    "TrackManager",
]
