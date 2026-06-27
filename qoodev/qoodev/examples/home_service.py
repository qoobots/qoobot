"""
Example: Home Service Skill — composite skill combining navigation, grasping, and interaction.

Demonstrates how to compose multiple skills into a higher-level
home service behavior (e.g., tidying up, serving drinks).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import enum
import time

from qoodev.examples.navigation import NavigationSkill, NavigationConfig
from qoodev.examples.grasping import GraspingSkill, GraspConfig
from qoodev.examples.voice_control import VoiceControlSkill, VoiceConfig, IntentType
from qoodev.examples.obstacle_avoidance import ObstacleAvoidanceSkill, AvoidanceConfig


class ServiceState(enum.Enum):
    IDLE = "idle"
    RECEIVING_COMMAND = "receiving_command"
    NAVIGATING_TO_OBJECT = "navigating_to_object"
    DETECTING_OBJECT = "detecting_object"
    GRASPING_OBJECT = "grasping_object"
    NAVIGATING_TO_DESTINATION = "navigating_to_destination"
    PLACING_OBJECT = "placing_object"
    RETURNING = "returning"
    DONE = "done"
    FAILED = "failed"


@dataclass
class ServiceTask:
    """A home service task definition."""
    task_id: str
    command: str                        # Natural language command
    target_object: str = ""             # Object to interact with
    source_location: str = ""           # Where to find the object
    destination_location: str = ""      # Where to bring/place it
    action: str = "fetch_and_deliver"   # fetch_and_deliver, tidy, serve


@dataclass
class ServiceConfig:
    """Configuration for home service skill."""
    default_navigation: NavigationConfig = field(default_factory=NavigationConfig)
    default_grasp: GraspConfig = field(default_factory=GraspConfig)
    default_voice: VoiceConfig = field(default_factory=VoiceConfig)
    default_avoidance: AvoidanceConfig = field(default_factory=AvoidanceConfig)
    task_timeout: float = 120.0         # seconds
    max_retries: int = 2
    known_locations: Dict[str, tuple] = field(default_factory=lambda: {
        "kitchen": (3.0, 2.0, 0.0),
        "living_room": (-2.0, 1.0, 0.0),
        "dining_table": (0.0, 1.5, 0.0),
        "coffee_table": (-1.0, 0.5, 0.0),
        "charging_station": (0.0, 0.0, 0.0),
    })
    known_objects: Dict[str, Dict] = field(default_factory=lambda: {
        "mug": {"location": "kitchen", "graspable": True},
        "bottle": {"location": "kitchen", "graspable": True},
        "book": {"location": "living_room", "graspable": True},
        "remote": {"location": "coffee_table", "graspable": True},
    })


class HomeServiceSkill:
    """Composite home service skill.

    Combines navigation, grasping, voice control, and obstacle avoidance
    to perform household tasks like:
    - "Bring me a mug from the kitchen"
    - "Tidy up the living room"
    - "Serve drinks to the dining table"

    Example usage:
        service = HomeServiceSkill(ServiceConfig())
        service.initialize()

        task = ServiceTask(
            task_id="task_001",
            command="bring me a mug from the kitchen",
            target_object="mug",
            source_location="kitchen",
            destination_location="dining_table",
        )
        result = service.execute_task(task)
    """

    def __init__(self, config: Optional[ServiceConfig] = None):
        self.config = config or ServiceConfig()
        self.state: ServiceState = ServiceState.IDLE

        # Sub-skills
        self.navigation = NavigationSkill(self.config.default_navigation)
        self.grasping = GraspingSkill(self.config.default_grasp)
        self.voice = VoiceControlSkill(self.config.default_voice)
        self.avoidance = ObstacleAvoidanceSkill(self.config.default_avoidance)

        # State
        self._current_task: Optional[ServiceTask] = None
        self._task_start_time: float = 0.0
        self._retries: int = 0

        # History
        self.completed_tasks: List[Dict[str, Any]] = []
        self.failed_tasks: List[Dict[str, Any]] = []

    def initialize(self) -> None:
        """Initialize all sub-skills and register voice handlers."""
        self.voice.register_handler(IntentType.MOVE, self._handle_move_command)
        self.voice.register_handler(IntentType.GRASP, self._handle_grasp_command)
        self.voice.register_handler(IntentType.STOP, self._handle_stop_command)
        self.state = ServiceState.IDLE

    def execute_task(self, task: ServiceTask) -> Dict[str, Any]:
        """Execute a complete home service task.

        Returns a result dict with success, duration, and diagnostics.
        """
        self._current_task = task
        self._task_start_time = time.time()
        self._retries = 0

        try:
            result = self._run_task_pipeline(task)
            self.completed_tasks.append(result)
            self.state = ServiceState.DONE
            return result
        except Exception as e:
            result = {
                "task_id": task.task_id,
                "success": False,
                "error": str(e),
                "duration": time.time() - self._task_start_time,
                "state": self.state.value,
            }
            self.failed_tasks.append(result)
            self.state = ServiceState.FAILED
            return result

    def get_status(self) -> dict:
        """Get comprehensive service status."""
        return {
            "state": self.state.value,
            "current_task": self._current_task.task_id if self._current_task else None,
            "completed": len(self.completed_tasks),
            "failed": len(self.failed_tasks),
            "success_rate": (
                len(self.completed_tasks) / max(1, len(self.completed_tasks) + len(self.failed_tasks))
            ),
            "sub_skills": {
                "navigation": self.navigation.get_status(),
                "grasping": self.grasping.get_status(),
                "avoidance": self.avoidance.get_safety_status(),
            },
        }

    def shutdown(self) -> None:
        """Graceful shutdown of all sub-skills."""
        self.navigation.cancel()
        self.grasping.release()
        self.voice.stop_listening()
        self.state = ServiceState.IDLE

    # ------------------------------------------------------------------
    # Task Pipeline
    # ------------------------------------------------------------------

    def _run_task_pipeline(self, task: ServiceTask) -> Dict[str, Any]:
        """Execute the full task pipeline."""
        start = time.time()

        # Step 1: Navigate to source
        self.state = ServiceState.NAVIGATING_TO_OBJECT
        source_pos = self.config.known_locations.get(task.source_location)
        if source_pos:
            self.navigation.set_goal(*source_pos)
            # In production: actually navigate with sensor loop

        # Step 2: Detect object
        self.state = ServiceState.DETECTING_OBJECT
        # In production: use camera to detect target object

        # Step 3: Grasp
        self.state = ServiceState.GRASPING_OBJECT
        grasp_result = self.grasping.grasp(task.target_object)
        if not grasp_result.success and self._retries < self.config.max_retries:
            self._retries += 1
            # Retry logic

        # Step 4: Navigate to destination
        self.state = ServiceState.NAVIGATING_TO_DESTINATION
        dest_pos = self.config.known_locations.get(task.destination_location)
        if dest_pos:
            self.navigation.set_goal(*dest_pos)

        # Step 5: Place object
        self.state = ServiceState.PLACING_OBJECT
        if dest_pos:
            self.grasping.place_at(dest_pos)

        # Step 6: Return to charging station
        self.state = ServiceState.RETURNING
        charging_pos = self.config.known_locations.get("charging_station")
        if charging_pos:
            self.navigation.set_goal(*charging_pos)

        return {
            "task_id": task.task_id,
            "success": True,
            "duration": time.time() - start,
            "state": ServiceState.DONE.value,
            "grasp_result": grasp_result,
        }

    # ------------------------------------------------------------------
    # Voice Command Handlers
    # ------------------------------------------------------------------

    def _handle_move_command(self, intent) -> dict:
        """Handle a voice move command."""
        location = intent.parameters.get("location", "")
        pos = self.config.known_locations.get(location)
        if pos:
            self.navigation.set_goal(*pos)
            return {"action": "navigate", "location": location, "success": True}
        return {"action": "navigate", "location": location, "success": False, "error": "unknown location"}

    def _handle_grasp_command(self, intent) -> dict:
        """Handle a voice grasp command."""
        target = intent.parameters.get("target", "")
        result = self.grasping.grasp(target)
        return {"action": "grasp", "target": target, "success": result.success}

    def _handle_stop_command(self, intent) -> dict:
        """Handle an emergency stop command."""
        self.navigation.cancel()
        self.grasping.release()
        self.state = ServiceState.IDLE
        return {"action": "stop", "success": True}
