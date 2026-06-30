#!/usr/bin/env python3
"""验证 qooremote 所有模块可正常导入 — v0.5.0 Immersive"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def test(name, code):
    try:
        code()
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False

def _test_exporter():
    from console.core.recording import Recorder, Exporter, ExportFormat
    r = Recorder()
    r.start('r1')
    r.record_frame({'j1': 0.3, 'j2': -0.5})
    r.stop()
    e = Exporter()
    for fmt in [ExportFormat.JSONL, ExportFormat.CSV, ExportFormat.QOORLOG, ExportFormat.HDF5]:
        result = e.export(r.get_frames(), r.metadata)
        assert result.frame_count == 1, f"{fmt}: frame_count={result.frame_count}"
        assert result.format == fmt

def _test_mocap():
    from console.core.teleop.mocap import (
        MocapToRobotMapper, MocapFrame, SkeletonBone, HUMANOID_DEFAULT_MAPPING
    )
    mapper = MocapToRobotMapper(HUMANOID_DEFAULT_MAPPING)
    frame = MocapFrame()
    bone = SkeletonBone('RightUpperArm', rotation=[0.707, 0.0, 0.707, 0.0])
    frame.bones['RightUpperArm'] = bone
    targets = mapper.map_to_joint_targets(frame)
    assert len(targets) >= 1, f"Expected at least 1 target, got {len(targets)}"

def _test_pointcloud():
    from console.core.twins import PointCloudManager, PointCloud, Point, PointCloudColorMode
    mgr = PointCloudManager()
    cloud = PointCloud(frame_id='scan1')
    for i in range(100):
        val = i % 10
        cloud.points.append(Point(i * 0.1, 0, i * 0.05, intensity=val / 10.0))
    mgr.add_frame(cloud)
    v, c, n = mgr.get_vertex_buffer()
    assert n > 0
    assert len(v) == n * 3
    stats = mgr.get_statistics()
    assert stats['frames_buffered'] == 1

passed = 0
total = 0

# --- Core Models ---
total += 1; passed += test("models: RobotState/JointState/Alert/Session/RobotRegistry",
    lambda: [__import__("console.core.models", fromlist=["RobotState"]),
             __import__("console.core.models", fromlist=["JointState"]),
             __import__("console.core.models", fromlist=["AlertManager"]),
             __import__("console.core.models", fromlist=["SessionManager"]),
             __import__("console.core.models", fromlist=["RobotRegistry"])])

# --- Signaling ---
total += 1; passed += test("signaling: client/messages/heartbeat",
    lambda: [__import__("console.core.signaling", fromlist=["SignalingClient"]),
             __import__("console.core.signaling", fromlist=["MessageType"]),
             __import__("console.core.signaling", fromlist=["HeartbeatManager"])])

# --- WebRTC ---
total += 1; passed += test("webrtc: peer/video_track/audio_track/data_channel",
    lambda: [__import__("console.core.webrtc", fromlist=["PeerConnection"]),
             __import__("console.core.webrtc", fromlist=["VideoTrackManager"]),
             __import__("console.core.webrtc", fromlist=["AudioTrack"]),
             __import__("console.core.webrtc", fromlist=["DataChannelManager"])])

# --- Teleop ---
total += 1; passed += test("teleop: controller/gamepad/keyboard/mocap/vr",
    lambda: [__import__("console.core.teleop", fromlist=["TeleopController"]),
             __import__("console.core.teleop", fromlist=["GamepadDriver"]),
             __import__("console.core.teleop", fromlist=["KeyboardDriver"]),
             __import__("console.core.teleop", fromlist=["MocapInterface"]),
             __import__("console.core.teleop", fromlist=["VrInterface"]),
             __import__("console.core.teleop", fromlist=["VrTeleopBridge"])])

# --- Recording ---
total += 1; passed += test("recording: recorder/player/exporter",
    lambda: [__import__("console.core.recording", fromlist=["Recorder"]),
             __import__("console.core.recording", fromlist=["Player"]),
             __import__("console.core.recording", fromlist=["Exporter"])])

# --- Utils ---
total += 1; passed += test("utils: units/interpolation/timer",
    lambda: [__import__("console.core.utils", fromlist=["units"]),
             __import__("console.core.utils", fromlist=["interpolation"]),
             __import__("console.core.utils", fromlist=["timer"])])

# --- Digital Twins (v0.5.0) ---
total += 1; passed += test("twins: urdf_loader/skeleton_driver/collision/pointcloud/slam",
    lambda: [__import__("console.core.twins", fromlist=["URDFLoader"]),
             __import__("console.core.twins", fromlist=["SkeletonDriver"]),
             __import__("console.core.twins", fromlist=["CollisionVisualizer"]),
             __import__("console.core.twins", fromlist=["PointCloudManager"]),
             __import__("console.core.twins", fromlist=["SLAMMap"])])

# --- Video Recorder/Player (v0.5.0) ---
total += 1; passed += test("video: recorder/player",
    lambda: [__import__("console.core.video", fromlist=["VideoRecorder"]),
             __import__("console.core.video.player", fromlist=["VideoPlayer"])])

# --- Alert History (v0.5.0) ---
total += 1; passed += test("alert_history: store/service",
    lambda: [__import__("console.core.models.alert_history", fromlist=["AlertHistoryStore"]),
             __import__("console.core.models.alert_history", fromlist=["AlertHistoryService"]),
             __import__("console.core.models.alert_history", fromlist=["AlertStatistics"])])

# --- VR Plugins (v0.5.0) ---
total += 1; passed += test("vr_plugins: meta_quest/htc_vive",
    lambda: [__import__("console.plugins.vr", fromlist=["MetaQuestDriver"]),
             __import__("console.plugins.vr.htc_vive", fromlist=["HtcViveDriver"])])

# --- UI Panels ---
total += 1; passed += test("panels: dash/video/control/voice/viewport3d/recording/pip/alert_history",
    lambda: [__import__("console.ui.panels.dash_panel"),
             __import__("console.ui.panels.video_panel"),
             __import__("console.ui.panels.control_panel"),
             __import__("console.ui.panels.voice_panel"),
             __import__("console.ui.panels.viewport_3d"),
             __import__("console.ui.panels.recording_panel"),
             __import__("console.ui.panels.video_pip"),
             __import__("console.ui.panels.alert_history_panel")])

# --- UI Widgets ---
total += 1; passed += test("widgets: status_card/battery/joint/sensor/alert/connection/emergency",
    lambda: [__import__("console.ui.widgets.status_card"),
             __import__("console.ui.widgets.battery_gauge"),
             __import__("console.ui.widgets.joint_table"),
             __import__("console.ui.widgets.sensor_chart"),
             __import__("console.ui.widgets.alert_list"),
             __import__("console.ui.widgets.connection_indicator"),
             __import__("console.ui.widgets.emergency_button")])

# --- ViewModels ---
total += 1; passed += test("viewmodels: robot/video/teleop/voice/recording/alert_history",
    lambda: [__import__("console.ui.viewmodels.robot_vm"),
             __import__("console.ui.viewmodels.video_vm"),
             __import__("console.ui.viewmodels.teleop_vm"),
             __import__("console.ui.viewmodels.voice_vm"),
             __import__("console.ui.viewmodels.recording_vm"),
             __import__("console.ui.viewmodels.alert_history_vm")])

# --- Dialogs ---
total += 1; passed += test("dialogs: connection/settings/about/recording/alert_history",
    lambda: [__import__("console.ui.dialogs.connection_dialog"),
             __import__("console.ui.dialogs.settings_dialog"),
             __import__("console.ui.dialogs.about_dialog"),
             __import__("console.ui.dialogs.recording_manager"),
             __import__("console.ui.dialogs.alert_history_dialog")])

# --- Plugins ---
total += 1; passed += test("plugins: base/plugin_manager",
    lambda: [__import__("console.plugins.base", fromlist=["BasePlugin"]),
             __import__("console.plugins.base", fromlist=["PluginManager"])])

# --- Functional Tests ---
total += 1; passed += test("Recorder basic flow",
    lambda: exec("from console.core.recording import Recorder; "
                 "r = Recorder(); "
                 "m = r.start('robot-01'); "
                 "r.record_frame({'joint_1': 0.5}); "
                 "r.add_marker('test point'); "
                 "r.stop(); "
                 "assert r.frame_count == 1"))

total += 1; passed += test("Exporter formats", _test_exporter)

total += 1; passed += test("Session & Multi-Robot",
    lambda: exec("from console.core.models import SessionManager, RobotRegistry, RobotInfo; "
                 "mgr = SessionManager(); "
                 "s = mgr.create_session('r1'); "
                 "assert s.robot_id == 'r1'; "
                 "mgr.close_current(); "
                 "assert mgr.active_session is None; "
                 "reg = RobotRegistry(); "
                 "reg.add_robot(RobotInfo('r1', 'Bot1')); "
                 "reg.select('r1'); "
                 "assert reg.selected_id == 'r1'"))

total += 1; passed += test("Mocap mapper",
    lambda: _test_mocap())

# --- v0.5.0 Functional Tests ---
total += 1; passed += test("URDF Loader (simple robot)",
    lambda: exec("from console.core.twins import URDFLoader; "
                 "xml = '<robot name=\"test\">"
                 "<link name=\"base\"/><link name=\"arm\"/>"
                 "<joint name=\"j1\" type=\"revolute\"><parent link=\"base\"/><child link=\"arm\"/>"
                 "<axis xyz=\"0 0 1\"/><limit lower=\"-1.57\" upper=\"1.57\"/></joint>"
                 "</robot>'; "
                 "m = URDFLoader.from_string(xml); "
                 "assert m.name == 'test'; "
                 "assert len(m.links) == 2; "
                 "assert len(m.joints) == 1; "
                 "assert m.root_link == 'base'"))

total += 1; passed += test("Skeleton FK computation",
    lambda: exec("from console.core.twins import URDFLoader, SkeletonDriver; "
                 "xml = '<robot name=\"test\">"
                 "<link name=\"base\"/><link name=\"arm\"/>"
                 "<joint name=\"j1\" type=\"revolute\"><parent link=\"base\"/><child link=\"arm\"/>"
                 "<axis xyz=\"0 1 0\"/><limit lower=\"-3.14\" upper=\"3.14\"/></joint>"
                 "</robot>'; "
                 "model = URDFLoader.from_string(xml); "
                 "driver = SkeletonDriver(model); "
                 "driver.set_joint_position('j1', 0.785); "  # 45°
                 "poses = driver.compute_forward_kinematics(); "
                 "assert 'base' in poses; "
                 "assert 'arm' in poses; "
                 "assert poses['base'].transform.translation == (0, 0, 0)"))

total += 1; passed += test("Collision Visualizer",
    lambda: exec("from console.core.twins import CollisionVisualizer, SafetyZone, CollisionPair, CollisionShape; "
                 "viz = CollisionVisualizer(); "
                 "viz.add_safety_zone(SafetyZone('safe', CollisionShape.SPHERE, (0,0,0), [1.0])); "
                 "p = CollisionPair(id='c1', link_a='arm', link_b='table'); "
                 "from console.core.twins.collision_viewer import ContactPoint; "
                 "p.contacts = [ContactPoint(position=(0.1,0,0), penetration_depth=0.01)]; "
                 "viz.update_collision(p); "
                 "prims = viz.get_render_primitives(); "
                 "assert len(prims) == 2; "  # 1 contact + 1 safety zone
                 "stats = viz.get_statistics(); "
                 "assert stats['active_pairs'] == 1"))

total += 1; passed += test("PointCloud Manager", _test_pointcloud)

total += 1; passed += test("SLAM Map",
    lambda: exec("from console.core.twins import SLAMMap, OccupancyGrid; "
                 "slam = SLAMMap(); "
                 "grid = OccupancyGrid(width=4, height=4, resolution=0.1); "
                 "grid.data = [0, -1, 80, 0,  0, 40, -1, 0,  0, 0, 100, 0,  0, 0, 0, -1]; "
                 "slam.occupancy_grid = grid; "
                 "v, c, n = slam.occupancy_grid_to_quads(); "
                 "assert n > 0"))

total += 1; passed += test("VR Bridge + Mock Driver",
    lambda: exec("from console.core.teleop.vr import VrTeleopBridge, VrHand; "
                 "from console.plugins.vr import MetaQuestDriver; "
                 "bridge = VrTeleopBridge(); "
                 "driver = MetaQuestDriver(); "
                 "driver.connect(); "
                 "frame = driver.poll(); "
                 "assert frame is not None; "
                 "assert frame.hmd.is_mounted; "
                 "ee = bridge.compute_end_effector_target(frame, VrHand.RIGHT); "
                 "assert isinstance(ee, dict); "
                 "driver.disconnect()"))

total += 1; passed += test("Alert History Store (SQLite)",
    lambda: exec("import tempfile, os; "
                 "from console.core.models.alert_history import AlertHistoryStore, AlertQuery; "
                 "from console.core.models.alert import Alert, AlertLevel, AlertType; "
                 "tmp = tempfile.mktemp(suffix='.db'); "
                 "s = AlertHistoryStore(tmp); "
                 "a = Alert.create(AlertLevel.CRITICAL, AlertType.COLLISION_DETECTED, 'Test collision'); "
                 "s.insert_alert(a); "
                 "results = s.query(AlertQuery(levels=[AlertLevel.CRITICAL], limit=10)); "
                 "assert len(results) == 1; "
                 "assert results[0]['level'] == 'critical'; "
                 "stats = s.get_statistics(); "
                 "assert stats.total_count == 1; "
                 "s.close(); "
                 "os.unlink(tmp)"))

print(f"\n{'='*50}")
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("✅ ALL TESTS PASSED")
else:
    print(f"❌ {total - passed} FAILURES")
    sys.exit(1)
