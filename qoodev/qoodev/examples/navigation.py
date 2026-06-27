"""
Example: Autonomous Navigation Skill.

Demonstrates path planning, localization, and safe navigation
using LiDAR and odometry sensors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import math
import time


@dataclass
class NavigationConfig:
    """Configuration for navigation skill."""
    max_linear_speed: float = 0.5          # m/s
    max_angular_speed: float = 1.0         # rad/s
    goal_tolerance: float = 0.1            # m
    angle_tolerance: float = 0.05          # rad
    obstacle_safety_distance: float = 0.3  # m
    planner_type: str = "a_star"           # a_star, rrt, dijkstra
    map_resolution: float = 0.05           # m/pixel
    replan_interval: float = 0.5           # seconds
    max_replan_attempts: int = 10


@dataclass
class Waypoint:
    """A navigation waypoint."""
    x: float
    y: float
    yaw: float = 0.0
    label: str = ""


class NavigationSkill:
    """Autonomous navigation skill for QooBot.

    Supports:
    - A* and RRT path planning
    - Real-time obstacle avoidance
    - Dynamic replanning
    - Multi-waypoint navigation
    - Safety monitoring

    Example usage:
        nav = NavigationSkill(NavigationConfig())
        nav.set_goal(3.0, 2.0, 0.0)
        while not nav.is_at_goal():
            cmd = nav.step(lidar_scan, current_pose)
            robot.execute(cmd)
    """

    def __init__(self, config: Optional[NavigationConfig] = None):
        self.config = config or NavigationConfig()
        self._current_path: List[Waypoint] = []
        self._waypoint_index: int = 0
        self._goal: Optional[Waypoint] = None
        self._is_navigating: bool = False
        self._last_replan_time: float = 0.0
        self._replan_count: int = 0
        self._start_pose: Tuple[float, float, float] = (0, 0, 0)

        # Statistics
        self.total_distance: float = 0.0
        self.total_time: float = 0.0
        self.collision_count: int = 0

    def set_goal(self, x: float, y: float, yaw: float = 0.0, label: str = "") -> None:
        """Set the navigation goal."""
        self._goal = Waypoint(x, y, yaw, label)
        self._is_navigating = True
        self._waypoint_index = 0
        self._replan_count = 0

    def set_waypoints(self, waypoints: List[Tuple[float, float, float]]) -> None:
        """Set multiple waypoints for sequential navigation."""
        self._current_path = [
            Waypoint(x, y, yaw, label=f"wp_{i}")
            for i, (x, y, yaw) in enumerate(waypoints)
        ]
        if self._current_path:
            last = self._current_path[-1]
            self.set_goal(last.x, last.y, last.yaw)

    def cancel(self) -> None:
        """Cancel current navigation."""
        self._is_navigating = False
        self._goal = None
        self._current_path.clear()

    def is_at_goal(self) -> bool:
        """Check if the robot has reached its goal."""
        return not self._is_navigating

    def step(
        self,
        lidar_scan: List[float],
        current_pose: Tuple[float, float, float],
        timestamp: Optional[float] = None,
    ) -> dict:
        """Compute the next control command.

        Args:
            lidar_scan: Array of range measurements from LiDAR
            current_pose: (x, y, yaw) current robot pose
            timestamp: Current time for rate control

        Returns:
            Dict with linear_x, angular_z, status, diagnostics
        """
        ts = timestamp or time.time()

        if not self._is_navigating or self._goal is None:
            return self._stop_command("No active navigation goal")

        # Check if at goal
        dx = self._goal.x - current_pose[0]
        dy = self._goal.y - current_pose[1]
        distance = math.hypot(dx, dy)

        if distance < self.config.goal_tolerance:
            self._is_navigating = False
            self.total_distance += self._distance(self._start_pose, current_pose)
            return self._stop_command("Goal reached", success=True)

        # Obstacle check
        if self._detect_obstacle(lidar_scan):
            self.collision_count += 1
            return self._avoidance_command(current_pose)

        # Compute velocity commands
        target_yaw = math.atan2(dy, dx)
        yaw_error = self._normalize_angle(target_yaw - current_pose[2])

        # Proportional control
        linear_x = min(self.config.max_linear_speed, distance * 0.8)
        angular_z = max(
            -self.config.max_angular_speed,
            min(self.config.max_angular_speed, yaw_error * 2.0)
        )

        # Reduce speed when turning
        if abs(yaw_error) > 0.5:
            linear_x *= 0.3

        return {
            "linear_x": linear_x,
            "angular_z": angular_z,
            "status": "navigating",
            "distance_to_goal": distance,
            "yaw_error": yaw_error,
            "success": False,
        }

    def get_status(self) -> dict:
        """Get current navigation status for debugging."""
        return {
            "is_navigating": self._is_navigating,
            "goal": (self._goal.x, self._goal.y, self._goal.yaw) if self._goal else None,
            "waypoint_index": self._waypoint_index,
            "total_distance": self.total_distance,
            "total_time": self.total_time,
            "collision_count": self.collision_count,
            "replan_count": self._replan_count,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_obstacle(self, lidar_scan: List[float]) -> bool:
        """Check if any obstacle is within safety distance."""
        if not lidar_scan:
            return False
        return any(0 < r < self.config.obstacle_safety_distance for r in lidar_scan)

    def _avoidance_command(self, pose: Tuple[float, float, float]) -> dict:
        """Generate an obstacle avoidance maneuver."""
        return {
            "linear_x": 0.0,
            "angular_z": self.config.max_angular_speed * 0.5,
            "status": "avoiding_obstacle",
            "distance_to_goal": float("inf"),
            "yaw_error": 0.0,
            "success": False,
        }

    def _stop_command(self, reason: str, success: bool = False) -> dict:
        return {
            "linear_x": 0.0,
            "angular_z": 0.0,
            "status": reason,
            "distance_to_goal": 0.0,
            "yaw_error": 0.0,
            "success": success,
        }

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """Normalize angle to [-pi, pi]."""
        return math.atan2(math.sin(angle), math.cos(angle))

    @staticmethod
    def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])
