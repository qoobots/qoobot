"""
Example: Obstacle Avoidance Skill.

Demonstrates reactive obstacle avoidance using LiDAR and
dynamic window approach (DWA) for safe navigation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import math


@dataclass
class AvoidanceConfig:
    """Configuration for obstacle avoidance."""
    safety_distance: float = 0.3         # m — minimum distance to obstacle
    warning_distance: float = 0.6        # m — distance to start slowing
    max_linear_speed: float = 0.8        # m/s
    max_angular_speed: float = 1.5       # rad/s
    linear_accel: float = 0.5            # m/s²
    angular_accel: float = 1.0           # rad/s²
    lidar_sectors: int = 36              # number of angular sectors
    lookahead_time: float = 1.0          # seconds for trajectory prediction
    dwa_samples: int = 50                # DWA trajectory samples
    robot_radius: float = 0.3            # m — robot footprint radius


@dataclass
class VelocityCommand:
    """A velocity command for the robot base."""
    linear_x: float = 0.0
    angular_z: float = 0.0

    def clamp(self, max_linear: float, max_angular: float) -> "VelocityCommand":
        return VelocityCommand(
            linear_x=max(-max_linear, min(max_linear, self.linear_x)),
            angular_z=max(-max_angular, min(max_angular, self.angular_z)),
        )


class ObstacleAvoidanceSkill:
    """Reactive obstacle avoidance for safe navigation.

    Implements Dynamic Window Approach (DWA) for local planning:
    - Samples velocity space for feasible trajectories
    - Scores trajectories based on safety, progress, and smoothness
    - Handles dynamic obstacles with predictive avoidance

    Example usage:
        oa = ObstacleAvoidanceSkill(AvoidanceConfig())
        while True:
            cmd = oa.compute_command(
                lidar_scan, current_pose, target_velocity
            )
            robot.set_velocity(cmd.linear_x, cmd.angular_z)
    """

    def __init__(self, config: Optional[AvoidanceConfig] = None):
        self.config = config or AvoidanceConfig()
        self._current_velocity = VelocityCommand()
        self._safety_breach_count: int = 0
        self._last_lidar: List[float] = []

    def compute_command(
        self,
        lidar_scan: List[float],
        current_pose: Tuple[float, float, float],
        target_velocity: Optional[VelocityCommand] = None,
    ) -> VelocityCommand:
        """Compute a safe velocity command.

        Args:
            lidar_scan: 360-degree LiDAR range measurements
            current_pose: (x, y, yaw) in world frame
            target_velocity: Desired velocity (from higher-level planner)

        Returns:
            Safe velocity command that avoids obstacles.
        """
        self._last_lidar = lidar_scan

        if not lidar_scan:
            return target_velocity or VelocityCommand()

        # Check for immediate danger
        min_distance = min(lidar_scan) if lidar_scan else float("inf")

        if min_distance < self.config.safety_distance:
            self._safety_breach_count += 1
            return self._emergency_stop()

        # Dynamic Window Approach
        return self._dwa_planner(lidar_scan, target_velocity)

    def get_safety_status(self) -> dict:
        """Get current safety status."""
        min_dist = min(self._last_lidar) if self._last_lidar else float("inf")
        status = "safe"
        if min_dist < self.config.safety_distance:
            status = "danger"
        elif min_dist < self.config.warning_distance:
            status = "warning"

        return {
            "status": status,
            "min_distance": min_dist,
            "safety_breaches": self._safety_breach_count,
            "current_velocity": (self._current_velocity.linear_x, self._current_velocity.angular_z),
        }

    def get_obstacle_map(self) -> List[Tuple[float, float]]:
        """Convert LiDAR scan to obstacle points in robot frame."""
        if not self._last_lidar:
            return []

        points = []
        n = len(self._last_lidar)
        for i, r in enumerate(self._last_lidar):
            if r > 0 and r < self.config.warning_distance * 2:
                angle = (2 * math.pi * i / n) - math.pi
                points.append((r * math.cos(angle), r * math.sin(angle)))
        return points

    # ------------------------------------------------------------------
    # DWA Planner
    # ------------------------------------------------------------------

    def _dwa_planner(
        self,
        lidar_scan: List[float],
        target: Optional[VelocityCommand],
    ) -> VelocityCommand:
        """Dynamic Window Approach local planner."""
        # Velocity search space
        v_min, v_max = -self.config.max_linear_speed, self.config.max_linear_speed
        w_min, w_max = -self.config.max_angular_speed, self.config.max_angular_speed

        # Dynamic window from current velocity + acceleration limits
        dw_v_min = self._current_velocity.linear_x - self.config.linear_accel * 0.1
        dw_v_max = self._current_velocity.linear_x + self.config.linear_accel * 0.1
        dw_w_min = self._current_velocity.angular_z - self.config.angular_accel * 0.1
        dw_w_max = self._current_velocity.angular_z + self.config.angular_accel * 0.1

        v_min = max(v_min, dw_v_min)
        v_max = min(v_max, dw_v_max)
        w_min = max(w_min, dw_w_min)
        w_max = min(w_max, dw_w_max)

        # Sample and score
        best_cmd = VelocityCommand()
        best_score = -float("inf")

        n_samples = self.config.dwa_samples
        for i in range(n_samples):
            v = v_min + (v_max - v_min) * i / (n_samples - 1) if n_samples > 1 else 0
            for j in range(max(1, n_samples // 5)):
                w = w_min + (w_max - w_min) * j / max(1, (n_samples // 5 - 1))

                # Check feasibility
                if not self._is_trajectory_safe(lidar_scan, v, w):
                    continue

                score = self._score_trajectory(v, w, target)
                if score > best_score:
                    best_score = score
                    best_cmd = VelocityCommand(v, w)

        self._current_velocity = best_cmd
        return best_cmd

    def _is_trajectory_safe(self, lidar_scan: List[float], v: float, w: float) -> bool:
        """Check if a velocity command would lead to a collision."""
        n = len(lidar_scan)
        dt = 0.1
        t = 0.0

        while t < self.config.lookahead_time:
            # Predicted position at time t
            if abs(w) < 0.001:
                x = v * t
                y = 0.0
                heading = 0.0
            else:
                r = v / w
                heading = w * t
                x = r * math.sin(heading)
                y = r * (1 - math.cos(heading))

            # Check against LiDAR points
            for i, dist in enumerate(lidar_scan):
                if dist <= 0 or dist > 10:
                    continue
                angle = (2 * math.pi * i / n) - math.pi
                ox = dist * math.cos(angle)
                oy = dist * math.sin(angle)

                if math.hypot(x - ox, y - oy) < self.config.safety_distance + self.config.robot_radius:
                    return False

            t += dt

        return True

    def _score_trajectory(
        self,
        v: float,
        w: float,
        target: Optional[VelocityCommand],
    ) -> float:
        """Score a trajectory for DWA."""
        score = 0.0

        # Progress toward target
        if target is not None:
            score += 10.0 * (1.0 - abs(v - target.linear_x) / max(0.01, self.config.max_linear_speed))
            score += 5.0 * (1.0 - abs(w - target.angular_z) / max(0.01, self.config.max_angular_speed))

        # Prefer forward motion
        score += 3.0 * (v / max(0.01, self.config.max_linear_speed))

        # Smoothness: prefer not to change velocity abruptly
        dv = abs(v - self._current_velocity.linear_x)
        dw = abs(w - self._current_velocity.angular_z)
        score -= 2.0 * dv / max(0.01, self.config.max_linear_speed)
        score -= 2.0 * dw / max(0.01, self.config.max_angular_speed)

        return score

    # ------------------------------------------------------------------
    # Emergency
    # ------------------------------------------------------------------

    def _emergency_stop(self) -> VelocityCommand:
        """Immediate stop with maximum deceleration."""
        self._current_velocity = VelocityCommand(0.0, 0.0)
        return self._current_velocity
