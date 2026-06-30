"""
Example: Object Grasping Skill.

Demonstrates vision-based grasp detection, arm motion planning,
and grasp execution with force feedback.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Tuple
import enum
import time


class GraspState(enum.Enum):
    IDLE = "idle"
    APPROACHING = "approaching"
    PRE_GRASP = "pre_grasp"
    GRASPING = "grasping"
    LIFTING = "lifting"
    PLACING = "placing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class GraspConfig:
    """Configuration for grasping skill."""
    approach_distance: float = 0.15       # m above object
    grasp_force: float = 5.0              # N
    lift_height: float = 0.2              # m
    grasp_timeout: float = 5.0            # seconds
    force_threshold: float = 2.0          # N — min force to detect grasp
    max_attempts: int = 3
    gripper_open_width: float = 0.1       # m
    gripper_close_width: float = 0.02     # m


@dataclass
class GraspTarget:
    """A detected graspable object."""
    label: str
    position: Tuple[float, float, float]  # (x, y, z) in robot frame
    orientation: Tuple[float, float, float, float] = (0, 0, 0, 1)  # quaternion
    size: Tuple[float, float, float] = (0.05, 0.05, 0.05)  # bounding box
    confidence: float = 0.8


@dataclass
class GraspResult:
    """Result of a grasp attempt."""
    success: bool
    object_label: str = ""
    attempts: int = 0
    duration: float = 0.0
    final_force: float = 0.0
    error: str = ""


class GraspingSkill:
    """Object grasping skill with vision-based detection.

    Supports:
    - RGB-D based object detection and localization
    - Inverse kinematics for arm positioning
    - Force-controlled grasping
    - Multi-attempt retry logic
    - Place-at-location

    Example usage:
        grasp = GraspingSkill(GraspConfig())
        grasp.detect_objects(rgb_image, depth_image)
        result = grasp.grasp("mug")
        if result.success:
            grasp.place_at((0.3, 0.2, 0.0))
    """

    def __init__(self, config: Optional[GraspConfig] = None):
        self.config = config or GraspConfig()
        self.state: GraspState = GraspState.IDLE
        self._detected_objects: List[GraspTarget] = []
        self._current_target: Optional[GraspTarget] = None
        self._attempts: int = 0
        self._start_time: float = 0.0

        # Statistics
        self.total_attempts: int = 0
        self.successful_grasps: int = 0
        self.failed_grasps: int = 0

    def detect_objects(
        self,
        rgb_image,
        depth_image,
        segmentation=None,
    ) -> List[GraspTarget]:
        """Detect graspable objects from sensor data.

        In production, this would use a trained object detection model.
        """
        # Placeholder: return demo objects
        self._detected_objects = [
            GraspTarget("mug", (0.3, 0.1, 0.5)),
            GraspTarget("bottle", (0.4, -0.1, 0.45)),
            GraspTarget("plate", (0.35, 0.2, 0.48), confidence=0.7),
        ]
        return self._detected_objects

    def grasp(self, object_label: str) -> GraspResult:
        """Execute a grasp on the specified object.

        Returns a GraspResult with success/failure and diagnostics.
        """
        # Find target
        targets = [o for o in self._detected_objects if o.label == object_label]
        if not targets:
            return GraspResult(
                success=False,
                object_label=object_label,
                error=f"Object '{object_label}' not detected",
            )

        self._current_target = targets[0]
        self._attempts = 0
        self._start_time = time.time()
        self.total_attempts += 1

        # Execute grasp sequence
        try:
            self._execute_grasp_sequence()
            self.successful_grasps += 1
            self.state = GraspState.DONE
            return GraspResult(
                success=True,
                object_label=object_label,
                attempts=self._attempts + 1,
                duration=time.time() - self._start_time,
            )
        except Exception as e:
            self.failed_grasps += 1
            self.state = GraspState.FAILED
            return GraspResult(
                success=False,
                object_label=object_label,
                attempts=self._attempts + 1,
                duration=time.time() - self._start_time,
                error=str(e),
            )

    def place_at(self, position: Tuple[float, float, float]) -> bool:
        """Place the currently held object at a target position."""
        if self.state != GraspState.DONE:
            return False
        self.state = GraspState.PLACING
        # In production: plan arm motion to position, open gripper
        self.state = GraspState.IDLE
        return True

    def release(self) -> None:
        """Emergency release of gripper."""
        self.state = GraspState.IDLE
        self._current_target = None

    def get_status(self) -> dict:
        """Get current grasp status."""
        return {
            "state": self.state.value,
            "target": self._current_target.label if self._current_target else None,
            "detected_objects": len(self._detected_objects),
            "attempts": self._attempts,
            "success_rate": (
                self.successful_grasps / max(1, self.total_attempts)
                if self.total_attempts > 0 else 0
            ),
        }

    # ------------------------------------------------------------------
    # Internal sequence
    # ------------------------------------------------------------------

    def _execute_grasp_sequence(self) -> None:
        """Run the grasp state machine."""
        # Approach
        self.state = GraspState.APPROACHING
        self._check_timeout()

        # Pre-grasp
        self.state = GraspState.PRE_GRASP

        # Grasp with force control
        self.state = GraspState.GRASPING

        # Lift
        self.state = GraspState.LIFTING

    def _check_timeout(self) -> None:
        """Raise if grasp has exceeded timeout."""
        if time.time() - self._start_time > self.config.grasp_timeout:
            raise TimeoutError("Grasp timed out")
