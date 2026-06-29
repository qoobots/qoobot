"""
brain_ai/grpc_server/perception_service.py — PerceptionService gRPC implementation.

Implements:
  - GetSceneGraph:     return current SceneGraph
  - GetLocalization:   return robot pose from SLAM
  - QueryObjects:      filter detected objects by class/confidence
  - StreamSceneGraph:  server-side streaming of scene updates
"""
from __future__ import annotations

import logging
import sys
import os
import time
import threading
from typing import Optional

import grpc

# Add proto_gen/ to sys.path
_PROTO_GEN = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "proto_gen")
)
if _PROTO_GEN not in sys.path:
    sys.path.insert(0, _PROTO_GEN)

from brain_os.perception import (
    service_pb2,
    service_pb2_grpc,
)
from brain_os.perception import types_pb2 as perception_types
from brain_os.common import types_pb2 as common_types

logger = logging.getLogger(__name__)


class PerceptionServiceServicer(service_pb2_grpc.PerceptionServiceServicer):
    """gRPC servicer for PerceptionService.

    Backed by the perception pipeline (SceneAggregator / SLAMWrapper / YOLODetector).
    In Sprint 1-3: serves mock data from the perception mock pipeline.
    """

    def __init__(self):
        super().__init__()
        self._scene_aggregator: Optional[object] = None  # SceneAggregator (lazy init)
        self._streaming_contexts: list[grpc.ServicerContext] = []
        self._streaming_lock = threading.Lock()
        logger.info("[PerceptionService] Initialized (gRPC servicer).")

    @property
    def scene_aggregator(self):
        """Lazy-load SceneAggregator when first needed."""
        if self._scene_aggregator is None:
            try:
                from brain_ai.perception.scene_aggregator import SceneAggregator
                import numpy as np
                self._scene_aggregator = SceneAggregator()
                logger.info("[PerceptionService] SceneAggregator initialized")
            except ImportError:
                logger.warning("[PerceptionService] SceneAggregator not available")
        return self._scene_aggregator

    # ── GetSceneGraph ──────────────────────────────────────────────────

    def GetSceneGraph(
        self,
        request: service_pb2.GetSceneGraphRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.GetSceneGraphResponse:
        """Return the current scene graph with all detected objects."""
        robot_id = request.robot_id
        include_summary = request.include_summary

        logger.info(f"[PerceptionService] GetSceneGraph: robot={robot_id}, summary={include_summary}")

        try:
            agg = self.scene_aggregator
            if agg:
                import numpy as np
                mock_img = np.zeros((480, 640, 3), dtype=np.uint8)
                domain_scene = agg.process_frame(mock_img)

                # Convert domain SceneGraph → proto SceneGraph
                proto_scene = self._domain_to_proto_scene(domain_scene)
            else:
                proto_scene = self._mock_scene_graph(robot_id)
        except Exception as exc:
            logger.error(f"[PerceptionService] GetSceneGraph error: {exc}")
            proto_scene = self._mock_scene_graph(robot_id)

        return service_pb2.GetSceneGraphResponse(
            status=common_types.Status(code=0, message="OK"),
            scene_graph=proto_scene,
        )

    # ── GetLocalization ────────────────────────────────────────────────

    def GetLocalization(
        self,
        request: service_pb2.GetLocalizationRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.GetLocalizationResponse:
        """Return robot localization (pose + covariance) from SLAM."""
        robot_id = request.robot_id
        logger.info(f"[PerceptionService] GetLocalization: robot={robot_id}")

        try:
            agg = self.scene_aggregator
            if agg and agg.slam:
                slam_pose = agg.slam.get_pose()
                cov = agg.slam.covariance
                localization = perception_types.RobotLocalization(
                    header=common_types.Header(
                        frame_id="world",
                        stamp=self._make_timestamp(),
                    ),
                    pose=common_types.Pose(
                        position=common_types.Vector3(
                            x=slam_pose.position.x,
                            y=slam_pose.position.y,
                            z=slam_pose.position.z,
                        ),
                        orientation=common_types.Quaternion(
                            x=slam_pose.orientation.x,
                            y=slam_pose.orientation.y,
                            z=slam_pose.orientation.z,
                            w=slam_pose.orientation.w,
                        ),
                    ),
                    covariance=cov,
                )
            else:
                localization = self._mock_localization(robot_id)
        except Exception as exc:
            logger.error(f"[PerceptionService] GetLocalization error: {exc}")
            localization = self._mock_localization(robot_id)

        return service_pb2.GetLocalizationResponse(
            status=common_types.Status(code=0, message="OK"),
            localization=localization,
        )

    # ── QueryObjects ───────────────────────────────────────────────────

    def QueryObjects(
        self,
        request: service_pb2.QueryObjectsRequest,
        context: grpc.ServicerContext,
    ) -> service_pb2.QueryObjectsResponse:
        """Query detected objects by class label and confidence threshold."""
        robot_id = request.robot_id
        class_label = request.class_label
        min_conf = request.min_confidence or 0.5
        max_results = request.max_results or 10

        logger.info(
            f"[PerceptionService] QueryObjects: robot={robot_id}, "
            f"label={class_label}, min_conf={min_conf}, max={max_results}"
        )

        try:
            agg = self.scene_aggregator
            if agg:
                import numpy as np
                mock_img = np.zeros((480, 640, 3), dtype=np.uint8)
                domain_scene = agg.process_frame(mock_img)

                filtered = [
                    obj for obj in domain_scene.objects
                    if obj.confidence >= min_conf
                    and (not class_label or obj.label == class_label)
                ][:max_results]

                proto_objects = [
                    self._domain_object_to_proto(obj)
                    for obj in filtered
                ]
            else:
                proto_objects = []
        except Exception as exc:
            logger.error(f"[PerceptionService] QueryObjects error: {exc}")
            proto_objects = []

        return service_pb2.QueryObjectsResponse(
            status=common_types.Status(code=0, message="OK"),
            objects=proto_objects,
        )

    # ── StreamSceneGraph ───────────────────────────────────────────────

    def StreamSceneGraph(
        self,
        request: service_pb2.StreamSceneGraphRequest,
        context: grpc.ServicerContext,
    ):
        """Server-side streaming: push scene graph updates at specified interval.

        Args:
            request: robot_id and update_interval_ms
            context: gRPC streaming context

        Yields:
            SceneGraph messages at the requested interval
        """
        robot_id = request.robot_id
        interval_ms = request.update_interval_ms or 200  # default 5 Hz
        logger.info(
            f"[PerceptionService] StreamSceneGraph: robot={robot_id}, "
            f"interval={interval_ms}ms"
        )

        # Register context for external push
        with self._streaming_lock:
            self._streaming_contexts.append(context)

        try:
            import numpy as np
            mock_img = np.zeros((480, 640, 3), dtype=np.uint8)

            while context.is_active():
                agg = self.scene_aggregator
                if agg:
                    try:
                        domain_scene = agg.process_frame(mock_img)
                        proto_scene = self._domain_to_proto_scene(domain_scene)
                        yield proto_scene
                    except Exception as exc:
                        logger.error(f"[PerceptionService] Stream error: {exc}")
                        yield self._mock_scene_graph(robot_id)
                else:
                    yield self._mock_scene_graph(robot_id)

                import time
                time.sleep(interval_ms / 1000.0)

        finally:
            with self._streaming_lock:
                if context in self._streaming_contexts:
                    self._streaming_contexts.remove(context)

    def broadcast_scene_graph(self, proto_scene: perception_types.SceneGraph) -> None:
        """External push: broadcast SceneGraph to all streaming clients."""
        with self._streaming_lock:
            dead = []
            for ctx in self._streaming_contexts:
                try:
                    ctx.write(proto_scene)
                except Exception:
                    dead.append(ctx)
            for ctx in dead:
                self._streaming_contexts.remove(ctx)

    # ── Conversion helpers ─────────────────────────────────────────────

    def _domain_to_proto_scene(self, domain_scene) -> perception_types.SceneGraph:
        """Convert domain SceneGraph to proto SceneGraph."""
        proto_objects = [
            self._domain_object_to_proto(obj)
            for obj in domain_scene.objects
        ]

        return perception_types.SceneGraph(
            header=common_types.Header(
                frame_id=domain_scene.source_frame,
                stamp=self._make_timestamp(),
            ),
            objects=proto_objects,
            relations=[],  # spatial relations (future: VLM inference)
            summary=f"Tabletop scene with {len(proto_objects)} objects",
        )

    def _domain_object_to_proto(self, obj) -> perception_types.DetectedObject:
        """Convert domain DetectedObject to proto DetectedObject."""
        import google.protobuf.timestamp_pb2
        ts = google.protobuf.timestamp_pb2.Timestamp()
        ts.GetCurrentTime()

        attrs = ["graspable"] if obj.graspable else []
        if hasattr(obj, "attributes") and obj.attributes:
            for k, v in obj.attributes.items():
                if v:
                    attrs.append(f"{k}:{v}")

        return perception_types.DetectedObject(
            object_id=obj.id,
            class_label=obj.label,
            confidence=float(obj.confidence),
            bbox=common_types.BoundingBox3D(
                center=common_types.Pose(
                    position=common_types.Vector3(x=obj.bbox.center.x, y=obj.bbox.center.y, z=obj.bbox.center.z),
                    orientation=common_types.Quaternion(x=0, y=0, z=0, w=1),
                ),
                dimensions=common_types.Vector3(x=obj.bbox.size.x, y=obj.bbox.size.y, z=obj.bbox.size.z),
            ),
            pose_in_world=common_types.Pose(
                position=common_types.Vector3(
                    x=obj.pose.position.x,
                    y=obj.pose.position.y,
                    z=obj.pose.position.z,
                ),
                orientation=common_types.Quaternion(
                    x=obj.pose.orientation.x,
                    y=obj.pose.orientation.y,
                    z=obj.pose.orientation.z,
                    w=obj.pose.orientation.w,
                ),
            ),
            attributes=attrs,
            detected_at=ts,
        )

    def _domain_to_proto_localization(self, slam) -> perception_types.RobotLocalization:
        """Convert SLAM state to proto RobotLocalization."""
        pose = slam.get_pose()
        return perception_types.RobotLocalization(
            header=common_types.Header(
                frame_id="world",
                stamp=self._make_timestamp(),
            ),
            pose=common_types.Pose(
                position=common_types.Vector3(
                    x=pose.position.x, y=pose.position.y, z=pose.position.z,
                ),
                orientation=common_types.Quaternion(
                    x=pose.orientation.x, y=pose.orientation.y,
                    z=pose.orientation.z, w=pose.orientation.w,
                ),
            ),
            covariance=slam.covariance,
        )

    # ── Mock data ──────────────────────────────────────────────────────

    def _mock_scene_graph(self, robot_id: str) -> perception_types.SceneGraph:
        """Generate mock scene graph for testing."""
        import google.protobuf.timestamp_pb2
        ts = google.protobuf.timestamp_pb2.Timestamp()
        ts.GetCurrentTime()

        mock_objects = []
        specs = [
            ("obj_cup_001", "cup", 0.92, (-0.3, 0.5, 0.08), (0.08, 0.08, 0.12)),
            ("obj_bottle_001", "bottle", 0.88, (0.2, 0.6, 0.10), (0.06, 0.06, 0.20)),
            ("obj_bowl_001", "bowl", 0.85, (-0.5, 0.55, 0.06), (0.12, 0.12, 0.06)),
            ("obj_table_001", "dining_table", 0.99, (0.0, 0.5, 0.0), (1.2, 0.8, 0.05)),
        ]
        for obj_id, label, conf, pos, size in specs:
            mock_objects.append(perception_types.DetectedObject(
                object_id=obj_id,
                class_label=label,
                confidence=conf,
                bbox=common_types.BoundingBox3D(
                    center=common_types.Pose(
                        position=common_types.Vector3(x=pos[0], y=pos[1], z=pos[2]),
                        orientation=common_types.Quaternion(x=0, y=0, z=0, w=1),
                    ),
                    dimensions=common_types.Vector3(x=size[0], y=size[1], z=size[2]),
                ),
                pose_in_world=common_types.Pose(
                    position=common_types.Vector3(x=pos[0], y=pos[1], z=pos[2]),
                    orientation=common_types.Quaternion(x=0, y=0, z=0, w=1),
                ),
                attributes=["graspable"],
                detected_at=ts,
            ))

        return perception_types.SceneGraph(
            header=common_types.Header(
                frame_id="world",
                stamp=ts,
            ),
            objects=mock_objects,
            relations=[],
            summary="Mock tabletop scene for development",
        )

    def _mock_localization(self, robot_id: str) -> perception_types.RobotLocalization:
        """Generate mock localization data."""
        return perception_types.RobotLocalization(
            header=common_types.Header(
                frame_id="world",
                stamp=self._make_timestamp(),
            ),
            pose=common_types.Pose(
                position=common_types.Vector3(x=0.0, y=0.0, z=1.0),
                orientation=common_types.Quaternion(x=0, y=0, z=0, w=1),
            ),
            covariance=[0.001] * 36,
        )

    @staticmethod
    def _make_timestamp():
        import google.protobuf.timestamp_pb2
        ts = google.protobuf.timestamp_pb2.Timestamp()
        ts.GetCurrentTime()
        return ts

    def shutdown(self) -> None:
        """Clean up perception resources."""
        if self._scene_aggregator:
            self._scene_aggregator.shutdown()
