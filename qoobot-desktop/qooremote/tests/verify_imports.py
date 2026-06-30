#!/usr/bin/env python3
"""验证 qooremote 所有模块可正常导入 — v0.3.0"""

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
total += 1; passed += test("teleop: controller/gamepad/keyboard/mocap",
    lambda: [__import__("console.core.teleop", fromlist=["TeleopController"]),
             __import__("console.core.teleop", fromlist=["GamepadDriver"]),
             __import__("console.core.teleop", fromlist=["KeyboardDriver"]),
             __import__("console.core.teleop", fromlist=["MocapInterface"])])

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

# --- UI Panels ---
total += 1; passed += test("panels: dash/video/control/voice/viewport3d/recording",
    lambda: [__import__("console.ui.panels.dash_panel"),
             __import__("console.ui.panels.video_panel"),
             __import__("console.ui.panels.control_panel"),
             __import__("console.ui.panels.voice_panel"),
             __import__("console.ui.panels.viewport_3d"),
             __import__("console.ui.panels.recording_panel")])

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
total += 1; passed += test("viewmodels: robot/video/teleop/voice/recording",
    lambda: [__import__("console.ui.viewmodels.robot_vm"),
             __import__("console.ui.viewmodels.video_vm"),
             __import__("console.ui.viewmodels.teleop_vm"),
             __import__("console.ui.viewmodels.voice_vm"),
             __import__("console.ui.viewmodels.recording_vm")])

# --- Dialogs ---
total += 1; passed += test("dialogs: connection/settings/about/recording_manager",
    lambda: [__import__("console.ui.dialogs.connection_dialog"),
             __import__("console.ui.dialogs.settings_dialog"),
             __import__("console.ui.dialogs.about_dialog"),
             __import__("console.ui.dialogs.recording_manager")])

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

total += 1; passed += test("Exporter formats",
    lambda: _test_exporter())

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

print(f"\n{'='*50}")
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("✅ ALL TESTS PASSED")
else:
    print(f"❌ {total - passed} FAILURES")
    sys.exit(1)
