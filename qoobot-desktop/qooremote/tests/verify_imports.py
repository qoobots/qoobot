"""导入验证脚本 — 确认所有模块可正常导入"""
import sys
sys.path.insert(0, '.')

# Core models
from console.core.models import RobotState, JointState, Alert, AlertManager, AlertLevel, AlertType
print("[OK] core.models")

# Core signaling
from console.core.signaling import SignalingClient, ConnectionState, HeartbeatManager, SignalingMessage, MessageType
print("[OK] core.signaling")

# Core teleop
from console.core.teleop.controller import TeleopCommand, JointCommand, EmergencyStopCommand, ModeSwitchCommand, ControlMode, Pose, TeleopController
print("[OK] core.teleop.controller")
from console.core.teleop.gamepad import GamepadDriver, GamepadMapping
print("[OK] core.teleop.gamepad")
from console.core.teleop.keyboard import KeyboardDriver, KeyboardMapping, KeyCode
print("[OK] core.teleop.keyboard")

# Core utils
from console.core.utils import units
print(f"[OK] core.utils (rad_to_deg: {units.rad_to_deg(3.14):.0f})")

# Functional verification
rs = RobotState()
assert len(rs.to_json()) > 100, "RobotState serialization failed"
print(f"[OK] RobotState serialized: {len(rs.to_json())} bytes")

a = Alert.create(AlertLevel.CRITICAL, AlertType.COLLISION_DETECTED, "Test collision")
assert a.id, "Alert creation failed"
mgr = AlertManager()
mgr.add_alert(a)
assert len(mgr.active_alerts) == 1, "AlertManager failed"
print(f"[OK] Alert + AlertManager: {len(mgr.active_alerts)} active")

msg = SignalingMessage.auth("test_token")
assert "auth" in msg.to_json(), "SignalingMessage failed"
print(f"[OK] SignalingMessage auth serialized: {len(msg.to_json())} bytes")

cmd = TeleopCommand(mode=ControlMode.END_EFFECTOR, target_frame="base_link")
assert "teleop_command" in cmd.to_json(), "TeleopCommand failed"
print(f"[OK] TeleopCommand serialized: {len(cmd.to_json())} bytes")

ecmd = EmergencyStopCommand(reason="test")
assert "emergency_stop" in ecmd.to_json(), "EmergencyStopCommand failed"
print(f"[OK] EmergencyStopCommand serialized: {len(ecmd.to_json())} bytes")

jcmd = JointCommand(mode=ControlMode.JOINT_POSITION)
assert "joint_command" in jcmd.to_json(), "JointCommand failed"
print(f"[OK] JointCommand serialized: {len(jcmd.to_json())} bytes")

mcmd = ModeSwitchCommand(from_mode="autonomous", to_mode="manual")
assert "mode_switch" in mcmd.to_json(), "ModeSwitchCommand failed"
print(f"[OK] ModeSwitchCommand serialized: {len(mcmd.to_json())} bytes")

kbd = KeyboardDriver()
assert kbd.selected_joint == 0
print(f"[OK] KeyboardDriver ready (joints: default)")

print("\n=== ALL 12 TESTS PASSED ===")
