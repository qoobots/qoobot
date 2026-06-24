"""
brain_ai/utils/ros2three.py — ROS 2 ↔ Three.js coordinate frame conversion.

ROS 2 convention:  X forward, Y left,  Z up
Three.js convention: X right,  Y up,    Z toward viewer

Transform: [x, y, z] → [-y, z, -x]  (approximate, without full TF2)
"""
from __future__ import annotations

from typing import Union

Coords = Union[list[float], tuple[float, float, float]]


def ros_to_threejs_pos(x: float, y: float, z: float) -> tuple[float, float, float]:
    """
    Convert ROS 2 position (X-forward) to Three.js position (Y-up, Z-toward).
    """
    return (-y, z, -x)


def threejs_to_ros_pos(tx: float, ty: float, tz: float) -> tuple[float, float, float]:
    """Inverse: Three.js → ROS 2."""
    return (-tz, -tx, ty)


def ros_quat_to_threejs(qx: float, qy: float, qz: float, qw: float) -> tuple[float, float, float, float]:
    """
    Convert ROS 2 quaternion to Three.js quaternion.
    Three.js uses same XYZW convention but different axes.
    """
    # Axis swap: ROS (x,y,z,w) → Three.js: negate y and z rotation axes
    return (-qy, qz, -qx, qw)


def scene_graph_to_threejs(scene: dict) -> dict:
    """
    Convert full scene graph dict (ROS 2 frame) to Three.js frame for rendering.
    Returns a new dict — does not modify the original.
    """
    result = dict(scene)

    # Convert robot pose
    rp = scene.get("robot_pose", [0.0] * 7)
    if len(rp) >= 7:
        rx, ry, rz = ros_to_threejs_pos(rp[0], rp[1], rp[2])
        result["robot_pose_3js"] = [rx, ry, rz] + rp[3:]

    # Convert object positions
    objects = []
    for obj in scene.get("objects", []):
        new_obj = dict(obj)
        pos = obj.get("position", [0.0, 0.0, 0.0])
        if len(pos) >= 3:
            tx, ty, tz = ros_to_threejs_pos(pos[0], pos[1], pos[2])
            new_obj["position_3js"] = [tx, ty, tz]
        objects.append(new_obj)
    result["objects"] = objects

    return result
