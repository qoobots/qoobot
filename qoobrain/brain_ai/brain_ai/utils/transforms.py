"""
brain_ai/utils/transforms.py — Coordinate frame transforms and math utilities.
"""
from __future__ import annotations

import math
from typing import Optional


# ── Type aliases ───────────────────────────────────────────────────────────
Vec3    = tuple[float, float, float]
Quat    = tuple[float, float, float, float]  # x, y, z, w
Pose7   = list[float]                         # [x, y, z, qx, qy, qz, qw]
Mat4    = list[list[float]]                   # 4×4 homogeneous transform


def euler_to_quat(roll: float, pitch: float, yaw: float) -> Quat:
    """Convert Euler angles (RPY, radians) to quaternion (x, y, z, w)."""
    cr = math.cos(roll  / 2); sr = math.sin(roll  / 2)
    cp = math.cos(pitch / 2); sp = math.sin(pitch / 2)
    cy = math.cos(yaw   / 2); sy = math.sin(yaw   / 2)
    return (
        sr * cp * cy - cr * sp * sy,   # x
        cr * sp * cy + sr * cp * sy,   # y
        cr * cp * sy - sr * sp * cy,   # z
        cr * cp * cy + sr * sp * sy,   # w
    )


def quat_to_euler(q: Quat) -> Vec3:
    """Convert quaternion (x, y, z, w) to Euler angles (roll, pitch, yaw) in radians."""
    x, y, z, w = q
    # Roll
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    # Pitch
    sinp = 2 * (w * y - z * x)
    pitch = math.asin(max(-1.0, min(1.0, sinp)))
    # Yaw
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return (roll, pitch, yaw)


def quat_normalize(q: Quat) -> Quat:
    x, y, z, w = q
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if norm < 1e-9:
        return (0.0, 0.0, 0.0, 1.0)
    return (x/norm, y/norm, z/norm, w/norm)


def quat_multiply(q1: Quat, q2: Quat) -> Quat:
    """Hamilton product q1 ⊗ q2."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return (
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    )


def pose7_to_matrix(pose: Pose7) -> Mat4:
    """Convert [x, y, z, qx, qy, qz, qw] to 4×4 homogeneous matrix."""
    tx, ty, tz, qx, qy, qz, qw = pose
    # Rotation matrix from quaternion
    r00 = 1 - 2*(qy*qy + qz*qz); r01 = 2*(qx*qy - qz*qw); r02 = 2*(qx*qz + qy*qw)
    r10 = 2*(qx*qy + qz*qw);     r11 = 1 - 2*(qx*qx + qz*qz); r12 = 2*(qy*qz - qx*qw)
    r20 = 2*(qx*qz - qy*qw);     r21 = 2*(qy*qz + qx*qw); r22 = 1 - 2*(qx*qx + qy*qy)
    return [
        [r00, r01, r02, tx],
        [r10, r11, r12, ty],
        [r20, r21, r22, tz],
        [0.0, 0.0, 0.0, 1.0],
    ]


def distance_3d(a: Vec3, b: Vec3) -> float:
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation."""
    return a + (b - a) * max(0.0, min(1.0, t))
