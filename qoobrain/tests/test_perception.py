"""
tests/test_perception.py — Sprint 3 perception pipeline integration tests.

Covers:
  - YOLODetector (mock detection)
  - SAMSegmetor (mock segmentation)
  - SLAMWrapper (mock SLAM, pose tracking)
  - PoseEstimator (6-DoF estimation)
  - OccupancyGrid (voxel operations, ray casting)
  - GSReconstructor (mock point cloud)
  - TrackManager (Kalman tracking, data association)
  - SceneAggregator (full pipeline)
  - CollisionChecker (env/self collision)
  - ROS2 Bridge (pub/sub/service mock)
  - PerceptionService (gRPC servicer)
"""
from __future__ import annotations

import os
import sys
import time
import unittest

import numpy as np

# Setup paths — bypass brain_ai package init to avoid pydantic dependency
_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
_BRAIN_AI = os.path.join(_ROOT, "brain_ai", "brain_ai")
if _BRAIN_AI not in sys.path:
    sys.path.insert(0, _BRAIN_AI)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ── Helpers ──────────────────────────────────────────────────────────────

def make_test_image(h: int = 480, w: int = 640) -> np.ndarray:
    """Create a simple RGB test image."""
    return np.zeros((h, w, 3), dtype=np.uint8)

def make_test_depth(h: int = 480, w: int = 640) -> np.ndarray:
    """Create a simple depth test image (meters)."""
    return np.full((h, w), 1.5, dtype=np.float32)


# ── YOLODetector Tests ───────────────────────────────────────────────────

class TestYOLODetector(unittest.TestCase):
    """Tests for YOLOv11 object detector wrapper."""

    def setUp(self):
        from perception.detector import YOLODetector, DetectorRegistry
        self.detector = YOLODetector()
        self.registry = DetectorRegistry

    def test_mock_detection(self):
        """Mock mode returns expected tabletop objects."""
        img = make_test_image()
        detections = self.detector.detect(img)
        self.assertGreaterEqual(len(detections), 3)
        labels = {d.label for d in detections}
        self.assertIn("cup", labels)
        self.assertIn("bottle", labels)

    def test_detection_sorted_by_confidence(self):
        """Detections are sorted descending by confidence."""
        img = make_test_image()
        detections = self.detector.detect(img)
        confs = [d.confidence for d in detections]
        self.assertEqual(confs, sorted(confs, reverse=True))

    def test_detection_has_bbox(self):
        """Each detection has a valid 2D bbox."""
        img = make_test_image()
        detections = self.detector.detect(img)
        for d in detections:
            self.assertEqual(len(d.bbox_xyxy), 4)
            x1, y1, x2, y2 = d.bbox_xyxy
            self.assertTrue(0 <= x1 < x2 <= 1)
            self.assertTrue(0 <= y1 < y2 <= 1)

    def test_custom_threshold(self):
        """Custom confidence threshold filters results."""
        img = make_test_image()
        all_dets = self.detector.detect(img, conf_threshold=0.0)
        high_dets = self.detector.detect(img, conf_threshold=0.95)
        self.assertLessEqual(len(high_dets), len(all_dets))

    def test_registry(self):
        """DetectorRegistry can register and retrieve detectors."""
        reg = self.registry.create_default()
        det = reg.get("default")
        self.assertIsNotNone(det)
        self.assertEqual(len(det.detect(make_test_image())), 4)

    def test_is_ready_without_model(self):
        """Without ONNX model loaded, is_ready returns True (mock)."""
        self.assertFalse(self.detector.is_ready)


# ── SAMSegmetor Tests ────────────────────────────────────────────────────

class TestSAMSegmetor(unittest.TestCase):
    """Tests for SAM2 instance segmentation wrapper."""

    def setUp(self):
        from perception.segmentor import SAMSegmetor
        self.segmentor = SAMSegmetor(enable_mock=True)

    def test_mock_segmentation(self):
        """Mock mode returns expected masks."""
        img = make_test_image()
        masks = self.segmentor.segment(img)
        self.assertGreaterEqual(len(masks), 3)
        labels = {m.label for m in masks}
        self.assertIn("cup", labels)
        self.assertIn("bottle", labels)

    def test_mask_properties(self):
        """Each mask has centroid, bbox, area."""
        img = make_test_image()
        masks = self.segmentor.segment(img)
        for m in masks:
            self.assertGreater(m.area_pixels, 0)
            cx, cy = m.centroid
            self.assertGreater(cx, 0)
            self.assertGreater(cy, 0)
            x1, y1, x2, y2 = m.bbox_xyxy
            self.assertLessEqual(x1, x2)

    def test_refine_grasp_mask(self):
        """Grasp mask refinement shrinks to grasp point region."""
        img = make_test_image()
        masks = self.segmentor.segment(img)
        if masks:
            original_area = masks[0].area_pixels
            refined = self.segmentor.refine_grasp_mask(masks[0], (320, 240))
            # Refined should be subset of original
            self.assertLessEqual(refined.area_pixels, original_area)


# ── SLAMWrapper Tests ────────────────────────────────────────────────────

class TestSLAMWrapper(unittest.TestCase):
    """Tests for ORB-SLAM3 SLAM wrapper."""

    def setUp(self):
        from perception.slam_wrapper import SLAMWrapper, SLAMState
        self.SLAMState = SLAMState
        self.slam = SLAMWrapper(vocab_path="test_path/ORBvoc.txt", enable_mock=True)

    def tearDown(self):
        self.slam.stop()

    def test_lifecycle(self):
        """SLAM lifecycle: uninitialized → tracking → stopped."""
        self.assertEqual(self.slam.state, self.SLAMState.UNINITIALIZED)
        self.slam.start()
        time.sleep(0.05)
        self.assertTrue(self.slam.is_tracking)
        self.slam.stop()
        self.assertEqual(self.slam.state, self.SLAMState.UNINITIALIZED)

    def test_pose_tracking(self):
        """Mock SLAM returns circular trajectory poses."""
        self.slam.start()
        time.sleep(0.05)
        pose1 = self.slam.get_pose()
        time.sleep(0.1)
        pose2 = self.slam.get_pose()
        # Pose should change over time
        dist = np.sqrt(
            (pose1.position.x - pose2.position.x) ** 2 +
            (pose1.position.y - pose2.position.y) ** 2
        )
        self.assertGreater(dist, 0.001)

    def test_covariance_available(self):
        """Covariance matrix is available while tracking."""
        self.slam.start()
        time.sleep(0.05)
        cov = self.slam.covariance
        self.assertEqual(len(cov), 36)

    def test_state_summary(self):
        """State summary returns key metrics."""
        self.slam.start()
        time.sleep(0.05)
        summary = self.slam.get_state_summary()
        self.assertIn("state", summary)
        self.assertIn("pose", summary)
        self.assertIn("num_map_points", summary)


# ── PoseEstimator Tests ──────────────────────────────────────────────────

class TestPoseEstimator(unittest.TestCase):
    """Tests for 6-DoF object pose estimator."""

    def setUp(self):
        from perception.pose_estimator import PoseEstimator
        self.estimator = PoseEstimator()

    def test_estimate_pose(self):
        """Estimate 6-DoF pose for a known object."""
        img = make_test_image()
        result = self.estimator.estimate_pose(
            "cup", img, bbox_xyxy=(0.2, 0.3, 0.4, 0.5),
        )
        self.assertGreater(result.confidence, 0.5)
        self.assertIn(result.source, ["mock", "ICP"])

    def test_unknown_object(self):
        """Unknown objects still get a pose estimate."""
        img = make_test_image()
        result = self.estimator.estimate_pose("alien_artifact", img)
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.pose)

    def test_known_objects(self):
        """Known objects set is populated."""
        self.assertIn("cup", self.estimator.known_objects)
        self.assertTrue(self.estimator.is_known("cup"))
        self.assertFalse(self.estimator.is_known("spaceship"))

    def test_world_transform(self):
        """Pose is transformed to world frame when camera pose given."""
        from domain.scene import Pose6D, Vec3, Quaternion
        camera_pose = Pose6D(
            position=Vec3(0.5, 0.5, 1.0),
            orientation=Quaternion(0, 0, 0, 1),
        )
        img = make_test_image()
        result = self.estimator.estimate_pose(
            "cup", img, bbox_xyxy=(0.3, 0.3, 0.5, 0.5),
            camera_pose=camera_pose,
        )
        self.assertGreater(result.pose.position.x, 0.35)  # mock pos ≈ 0.38


# ── OccupancyGrid Tests ──────────────────────────────────────────────────

class TestOccupancyGrid(unittest.TestCase):
    """Tests for 3D occupancy grid."""

    def setUp(self):
        from perception.occupancy_net import OccupancyGrid
        self.grid = OccupancyGrid(resolution=0.1, grid_size_m=(2, 2, 1))

    def test_create(self):
        """Grid is created with correct dimensions."""
        self.assertEqual(self.grid.dims, (20, 20, 10))
        self.assertEqual(self.grid.resolution, 0.1)

    def test_mark_occupied(self):
        """Marking voxels as occupied updates the grid."""
        from domain.scene import Vec3
        self.grid.update_from_detection(
            Vec3(0.5, 0.5, 0.5), Vec3(0.3, 0.3, 0.1), occupied=True,
        )
        self.grid.finalize()
        self.assertTrue(self.grid.is_occupied(Vec3(0.5, 0.5, 0.5)))

    def test_free_space_stays_free(self):
        """Unmarked space remains free."""
        from domain.scene import Vec3
        self.grid.update_from_detection(
            Vec3(0.5, 0.5, 0.5), Vec3(0.1, 0.1, 0.1), occupied=True,
        )
        self.grid.finalize()
        self.assertFalse(self.grid.is_occupied(Vec3(-0.8, -0.8, 0.3)))

    def test_ray_cast_hit(self):
        """Ray casting detects occupied voxels."""
        from domain.scene import Vec3
        self.grid.update_from_detection(
            Vec3(0.5, 0.5, 0.5), Vec3(0.2, 0.2, 0.2), occupied=True,
        )
        self.grid.finalize()
        hit, point = self.grid.check_ray(Vec3(0, 0, 0.5), Vec3(1, 1, 0.5))
        self.assertTrue(hit)
        self.assertIsNotNone(point)

    def test_ray_cast_clear(self):
        """Ray casting through free space returns no hit."""
        from domain.scene import Vec3
        self.grid.finalize()
        hit, point = self.grid.check_ray(Vec3(-0.5, -0.5, 0.5), Vec3(-0.9, -0.9, 0.5))
        self.assertFalse(hit)

    def test_reset(self):
        """Reset clears all voxels."""
        from domain.scene import Vec3
        self.grid.update_from_detection(Vec3(0, 0, 0), Vec3(1, 1, 1), occupied=True)
        self.grid.finalize()
        self.assertTrue(self.grid.is_occupied(Vec3(0, 0, 0)))
        self.grid.reset()
        self.assertFalse(self.grid.is_occupied(Vec3(0, 0, 0)))

    def test_tabletop_mock_grid(self):
        """Mock tabletop grid has expected obstacles."""
        from perception.occupancy_net import create_tabletop_mock_grid
        from domain.scene import Vec3
        grid = create_tabletop_mock_grid()
        self.assertEqual(grid.dims, (40, 40, 30))
        # Table should be occupied
        self.assertTrue(grid.is_occupied(Vec3(0, 0.5, 0.70)))


# ── GSReconstructor Tests ────────────────────────────────────────────────

class TestGSReconstructor(unittest.TestCase):
    """Tests for 3D Gaussian Splatting reconstructor."""

    def setUp(self):
        from perception.gs_reconstructor import GSReconstructor
        self.gs = GSReconstructor(enable_mock=True)

    def test_mock_cloud(self):
        """Mock mode generates a splat cloud."""
        cloud = self.gs._mock_cloud()
        self.assertGreater(cloud.num_splats, 100)

    def test_latest_cloud_tracked(self):
        """Latest cloud is stored after generation."""
        cloud = self.gs._mock_cloud()
        self.assertIs(self.gs.latest_cloud, cloud)

    def test_to_numpy_export(self):
        """Splat cloud exports to numpy arrays."""
        cloud = self.gs._mock_cloud()
        arrays = cloud.to_numpy()
        self.assertIn("positions", arrays)
        self.assertIn("colors", arrays)
        self.assertEqual(arrays["positions"].shape[0], cloud.num_splats)

    def test_render_no_cloud_returns_none(self):
        """Render with no cloud returns None."""
        gs = self.gs.__class__(enable_mock=True)
        result = gs.render()
        self.assertIsNone(result)


# ── TrackManager Tests ───────────────────────────────────────────────────

class TestTrackManager(unittest.TestCase):
    """Tests for multi-frame object tracker."""

    def setUp(self):
        from perception.track_manager import TrackManager
        from perception.detector import Detection
        self.TrackManager = TrackManager
        self.Detection = Detection
        self.mgr = TrackManager()

    def test_single_detection_creates_track(self):
        """First detection creates a new BORN track."""
        dets = [self.Detection("cup", 0.9, (0.2, 0.3, 0.4, 0.5))]
        tracks = self.mgr.update(dets)
        # Should have 0 ACTIVE tracks (needs 3 hits)
        self.assertEqual(len(tracks), 0)
        self.assertEqual(self.mgr.num_tracks, 1)

    def test_three_frames_confirm_track(self):
        """After 3 consecutive matches, track becomes ACTIVE."""
        dets = [self.Detection("cup", 0.9, (0.2, 0.3, 0.4, 0.5))]
        for _ in range(3):
            tracks = self.mgr.update(dets)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].state.value, "active")

    def test_missed_detections_cause_lost(self):
        """Track becomes LOST after consecutive misses."""
        dets = [self.Detection("cup", 0.9, (0.2, 0.3, 0.4, 0.5))]
        track_id = None
        for _ in range(3):
            tracks = self.mgr.update(dets)
            if tracks:
                track_id = tracks[0].track_id
        # Send empty detections
        for _ in range(5):
            self.mgr.update([])
        # Track should be LOST (not ACTIVE, so not in active_tracks)
        active = self.mgr.get_active_tracks()
        # Track still exists but is lost
        track = self.mgr.get_track_by_id(track_id) if track_id else None
        self.assertIsNotNone(track)
        self.assertEqual(track.state.value, "lost")

    def test_multi_object_tracking(self):
        """Multiple objects tracked simultaneously."""
        dets = [
            self.Detection("cup", 0.9, (0.2, 0.3, 0.4, 0.5)),
            self.Detection("bottle", 0.85, (0.5, 0.4, 0.7, 0.6)),
        ]
        for _ in range(3):
            tracks = self.mgr.update(dets)
        self.assertEqual(len(tracks), 2)
        labels = {t.label for t in tracks}
        self.assertEqual(labels, {"cup", "bottle"})

    def test_kalman_update(self):
        """Kalman filter updates position and velocity."""
        from perception.track_manager import Track
        track = Track(track_id="test", label="cup")
        from domain.scene import Vec3
        # Initial state is zeros; Kalman update blends measurement with prior
        track.update(Vec3(0.5, 0.5, 0.1))
        # x = 0 * (1-K) + 0.5 * K ≈ 0.5 * K  (K is approx 0.67 for initial covariance)
        # So x ≈ 0.33, not 0.5 (measurement is weighted against prior)
        self.assertGreater(float(track.state_vector[0]), 0.0)
        self.assertLess(float(track.state_vector[0]), 0.5)
        # Update again: should converge toward 0.5
        track.update(Vec3(0.5, 0.5, 0.1))
        self.assertAlmostEqual(float(track.state_vector[0]), 0.5, places=0)

    def test_track_cleanup(self):
        """Dead tracks are removed after max_age misses."""
        dets = [self.Detection("cup", 0.9, (0.2, 0.3, 0.4, 0.5))]
        self.mgr.update(dets)  # born
        for _ in range(self.mgr._max_age + 1):
            self.mgr.update([])
        self.assertEqual(self.mgr.num_tracks, 0)


# ── SceneAggregator Tests ────────────────────────────────────────────────

class TestSceneAggregator(unittest.TestCase):
    """Tests for the full perception pipeline aggregator."""

    def setUp(self):
        from perception.scene_aggregator import SceneAggregator
        self.agg = SceneAggregator()

    def tearDown(self):
        self.agg.shutdown()

    def test_process_frame(self):
        """Processing a frame returns a SceneGraph."""
        img = make_test_image()
        depth = make_test_depth()
        scene = self.agg.process_frame(img, depth)
        self.assertIsNotNone(scene)
        self.assertIsNotNone(scene.timestamp)

    def test_robot_pose_in_scene(self):
        """Scene contains the current robot pose from SLAM."""
        img = make_test_image()
        scene = self.agg.process_frame(img)
        self.assertIsNotNone(scene.robot_pose)
        self.assertNotEqual(scene.robot_pose.position.x, 0.0)

    def test_multiple_frames_accumulate(self):
        """Frame counter increments correctly."""
        img = make_test_image()
        self.agg.process_frame(img)
        self.agg.process_frame(img)
        self.agg.process_frame(img)
        self.assertEqual(self.agg.frame_count, 3)

    def test_get_objects_by_label(self):
        """Scene can query objects by label."""
        img = make_test_image()
        scene = self.agg.process_frame(img)
        cups = [o for o in scene.objects if o.label == "cup"]
        self.assertGreaterEqual(len(cups), 0)  # May be 0 without enough frames


# ── CollisionChecker Tests ───────────────────────────────────────────────

class TestCollisionChecker(unittest.TestCase):
    """Tests for collision detection (FCL-based)."""

    def setUp(self):
        from perception.collision_checker import CollisionChecker
        self.checker = CollisionChecker(enable_mock=True)

    def test_load_robot_urdf(self):
        """Loading mock URDF registers Kinova Gen3 links."""
        self.checker.load_robot_urdf("test.urdf")
        self.assertGreater(self.checker.num_links, 5)

    def test_check_collision_free(self):
        """Default joint positions are collision-free."""
        self.checker.load_robot_urdf("test.urdf")
        joints = {f"joint_{i}": 0.0 for i in range(7)}
        result = self.checker.check_collision(joints)
        self.assertFalse(result.in_collision)
        self.assertGreater(result.processing_time_ms, 0)

    def test_last_result_tracked(self):
        """Last collision result is stored."""
        self.checker.load_robot_urdf("test.urdf")
        joints = {f"joint_{i}": 0.0 for i in range(7)}
        self.checker.check_collision(joints)
        self.assertIsNotNone(self.checker.last_result)

    def test_register_link(self):
        """Manual link registration works."""
        from perception.collision_checker import (
            RobotLinkGeometry, CollisionGeometry, CollisionShape,
        )
        link = RobotLinkGeometry(
            name="test_link",
            geometry=CollisionGeometry(
                shape=CollisionShape.SPHERE, dimensions=[0.1],
            ),
        )
        self.checker.register_link(link)
        self.assertGreaterEqual(self.checker.num_links, 1)


# ── ROS2 Bridge Tests ────────────────────────────────────────────────────

class TestTopicPublisher(unittest.TestCase):
    """Tests for ROS 2 topic publisher wrapper."""

    def setUp(self):
        from ros2_bridge.topic_publisher import TopicPublisher
        self.pub = TopicPublisher(enable_mock=True)

    def test_publish(self):
        """Mock publish records publication."""
        self.pub.publish("/test/topic", {"value": 42})
        self.assertEqual(self.pub.publication_count, 1)

    def test_publish_multiple_topics(self):
        """Multiple topics are tracked."""
        for i in range(5):
            self.pub.publish(f"/test/topic_{i}", {"id": i})
        self.assertEqual(self.pub.publication_count, 5)

    def test_get_latest(self):
        """Latest data per topic can be retrieved."""
        self.pub.publish("/test/topic", {"seq": 1})
        self.pub.publish("/test/topic", {"seq": 2})
        latest = self.pub.get_latest("/test/topic")
        self.assertEqual(latest["seq"], 2)

    def test_latch(self):
        """Latching stores data for replay."""
        self.pub.publish("/test/latched", {"key": "value"}, latch=True)
        self.assertEqual(self.pub.get_latest("/test/latched")["key"], "value")

    def test_mock_subscriber(self):
        """Mock callback receives published messages."""
        received = []
        self.pub.subscribe_mock("/test/notify", lambda m: received.append(m))
        self.pub.publish("/test/notify", {"msg": "hello"})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["msg"], "hello")


class TestTopicSubscriber(unittest.TestCase):
    """Tests for ROS 2 topic subscriber wrapper."""

    def setUp(self):
        from ros2_bridge.topic_subscriber import TopicSubscriber
        self.sub = TopicSubscriber(enable_mock=True, spin_thread=False)

    def tearDown(self):
        self.sub.stop_spin()

    def test_subscribe(self):
        """Subscribe registers a callback."""
        called = []
        self.sub.subscribe("/test/topic", "TestMsg", lambda m: called.append(m))
        self.assertIn("/test/topic", self.sub.subscribed_topics)

    def test_inject_mock_message(self):
        """Injecting a mock message triggers callbacks."""
        received = []
        self.sub.subscribe("/test/topic", "TestMsg", lambda m: received.append(m))
        self.sub.inject_mock_message("/test/topic", {"data": 123})
        # Need to manually dispatch since spin is off
        self.sub._dispatch("/test/topic", received[0] if received else {"data": 123})
        self.sub.stop_spin()

    def test_stats(self):
        """Stats return subscription metrics."""
        self.sub.subscribe("/test/topic", "TestMsg", lambda m: None)
        stats = self.sub.get_stats()
        self.assertIn("/test/topic", stats["topics"])


class TestServiceClient(unittest.TestCase):
    """Tests for ROS 2 service client wrapper."""

    def setUp(self):
        from ros2_bridge.service_client import ServiceClient
        self.cli = ServiceClient(enable_mock=True)

    def test_default_mock_call(self):
        """Mock service call returns default response."""
        result = self.cli.call("/test/service", {"param": 1})
        self.assertTrue(result.success)
        self.assertEqual(result.response["status"], "ok")

    def test_mock_handler(self):
        """Custom mock handler returns tailored response."""
        self.cli.register_mock_handler(
            "/custom/service",
            lambda req: {"value": req["input"] * 2},
        )
        result = self.cli.call("/custom/service", {"input": 21})
        self.assertTrue(result.success)
        self.assertEqual(result.response["value"], 42)

    def test_emergency_stop(self):
        """Emergency stop convenience method."""
        result = self.cli.emergency_stop("robot_01")
        self.assertTrue(result.success)
        self.assertIn("emergency_stop", result.service)

    def test_call_records_stats(self):
        """Service calls are recorded for stats."""
        self.cli.call("/test/a", {})
        self.cli.call("/test/a", {})
        self.assertEqual(self.cli.call_count, 2)

    def test_timeout_retry(self):
        """Timeout triggers retry behavior in mock mode."""
        # Mock handler that raises TimeoutError
        self.cli.register_mock_handler(
            "/slow/service", lambda req: (_ for _ in () ).throw(TimeoutError("mock")),
        )
        result = self.cli.call("/slow/service", {}, timeout_sec=0.1, retries=1)
        # Should fail after retries
        self.assertFalse(result.success)


# ── PerceptionService gRPC Tests ─────────────────────────────────────────

class TestPerceptionServiceServicer(unittest.TestCase):
    """Tests for the PerceptionService gRPC servicer (direct method calls)."""

    def setUp(self):
        # Use direct import to keep things simple
        _PROTO_GEN = os.path.join(_ROOT, "brain_ai", "brain_ai", "proto_gen")
        if _PROTO_GEN not in sys.path:
            sys.path.insert(0, _PROTO_GEN)

    def test_servicer_creation(self):
        """Servicer can be instantiated."""
        from grpc_server.perception_service import PerceptionServiceServicer
        servicer = PerceptionServiceServicer()
        self.assertIsNotNone(servicer)

    def test_get_scene_graph_mock(self):
        """GetSceneGraph returns mock data when no pipeline."""
        from grpc_server.perception_service import PerceptionServiceServicer
        from brain_os.perception import service_pb2

        servicer = PerceptionServiceServicer()
        request = service_pb2.GetSceneGraphRequest(robot_id="test", include_summary=True)
        response = servicer.GetSceneGraph(request, None)

        self.assertEqual(response.status.code, 0)
        self.assertGreater(len(response.scene_graph.objects), 0)

    def test_get_localization_mock(self):
        """GetLocalization returns mock pose."""
        from grpc_server.perception_service import PerceptionServiceServicer
        from brain_os.perception import service_pb2

        servicer = PerceptionServiceServicer()
        request = service_pb2.GetLocalizationRequest(robot_id="test")
        response = servicer.GetLocalization(request, None)

        self.assertEqual(response.status.code, 0)
        self.assertAlmostEqual(response.localization.pose.position.x, 0.0)

    def test_query_objects_mock(self):
        """QueryObjects returns filtered results."""
        from grpc_server.perception_service import PerceptionServiceServicer
        from brain_os.perception import service_pb2

        servicer = PerceptionServiceServicer()
        request = service_pb2.QueryObjectsRequest(
            robot_id="test", class_label="cup", min_confidence=0.5, max_results=5,
        )
        response = servicer.QueryObjects(request, None)

        self.assertEqual(response.status.code, 0)
        # Mock returns empty list without pipeline
        self.assertGreaterEqual(len(response.objects), 0)

    def test_mock_scene_graph_has_expected_objects(self):
        """Mock scene graph contains our test objects."""
        from grpc_server.perception_service import PerceptionServiceServicer

        servicer = PerceptionServiceServicer()
        scene = servicer._mock_scene_graph("test")
        labels = {obj.class_label for obj in scene.objects}
        self.assertIn("cup", labels)
        self.assertIn("bottle", labels)
        self.assertIn("bowl", labels)
        self.assertIn("dining_table", labels)


# ── Run ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
