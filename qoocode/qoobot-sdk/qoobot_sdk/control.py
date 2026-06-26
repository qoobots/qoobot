"""
Control API - Robot control interfaces.

Provides command types for controlling the robot:
- Joint position/velocity/torque commands
- End-effector pose commands
- Gripper commands
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union

import numpy as np


@dataclass
class JointCommand:
    """Command for a single joint.

    Attributes:
        name: Joint name
        position: Target position in radians (optional)
        velocity: Target velocity in rad/s (optional)
        torque: Target torque in Nm (optional)
    """
    name: str
    position: Optional[float] = None
    velocity: Optional[float] = None
    torque: Optional[float] = None


@dataclass
class JointGroupCommand:
    """Command for a group of joints.

    Attributes:
        joints: List of joint commands
        timestamp: Command timestamp
    """
    joints: List[JointCommand] = field(default_factory=list)
    timestamp: float = 0.0

    @classmethod
    def position_control(
        cls, positions: dict, timestamp: float = 0.0
    ) -> "JointGroupCommand":
        """Create position control command from dict."""
        joints = [
            JointCommand(name=name, position=pos)
            for name, pos in positions.items()
        ]
        return cls(joints=joints, timestamp=timestamp)

    @classmethod
    def velocity_control(
        cls, velocities: dict, timestamp: float = 0.0
    ) -> "JointGroupCommand":
        """Create velocity control command from dict."""
        joints = [
            JointCommand(name=name, velocity=vel)
            for name, vel in velocities.items()
        ]
        return cls(joints=joints, timestamp=timestamp)


@dataclass
class Pose:
    """6-DOF pose.

    Attributes:
        position: (x, y, z) in meters
        orientation: (x, y, z, w) quaternion
    """
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)

    @classmethod
    def identity(cls) -> "Pose":
        """Create identity pose."""
        return cls()

    @classmethod
    def from_matrix(cls, matrix: np.ndarray) -> "Pose":
        """Create pose from 4x4 transformation matrix."""
        from scipy.spatial.transform import Rotation
        position = tuple(matrix[:3, 3])
        rot = Rotation.from_matrix(matrix[:3, :3])
        orientation = tuple(rot.as_quat())  # xyzw
        return cls(position=position, orientation=orientation)


@dataclass
class EndEffectorCommand:
    """End-effector pose command.

    Attributes:
        name: End-effector name (e.g., "left_hand", "right_hand")
        pose: Target pose
    """
    name: str
    pose: Pose = field(default_factory=Pose)


@dataclass
class GripperCommand:
    """Gripper command.

    Attributes:
        name: Gripper name
        position: Gripper opening (0=closed, 1=open)
        force: Gripping force in N
    """
    name: str
    position: float = 0.0
    force: float = 0.0
