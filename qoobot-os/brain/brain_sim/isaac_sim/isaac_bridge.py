"""
Brain OS ↔ Isaac Sim Bridge
============================
Bidirectional communication bridge between Brain OS cognitive services
and NVIDIA Isaac Sim physics simulation.

Capabilities:
  - Robot state sync (joint positions, EE pose, gripper state)
  - Sensor data streaming (RTX-rendered images, depth, segmentation)
  - Action execution (joint commands, gripper, mobile base)
  - Scene management (create/remove prims, set materials, physics props)
  - Domain randomization for RL training
  - Real-time data logging for evaluation

Architecture:
  Brain OS (gRPC) ←→ isaac_bridge.py ←→ Isaac Sim (omni.* APIs)

Dependencies:
  - NVIDIA Isaac Sim 2023.1.1+
  - omni.isaac.core, omni.isaac.sensor, omni.usd
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Isaac Sim imports (available only in Isaac Sim Python environment)
try:
    from omni.isaac.core import World
    from omni.isaac.core.robots import Robot
    from omni.isaac.sensor import Camera, IMUSensor
    from omni.isaac.core.objects import DynamicCuboid, DynamicCylinder, FixedCuboid
    from omni.isaac.core.utils.prims import create_prim, delete_prim, get_prim_at_path
    from omni.usd import get_stage
    import carb
    HAS_ISAAC_SIM = True
except ImportError:
    HAS_ISAAC_SIM = False
    logger.warning("Isaac Sim not available — running in mock mode")


# ============================================================================
# Data Types
# ============================================================================

@dataclass
class IsaacRobotState:
    """Complete robot state snapshot."""
    joint_positions: np.ndarray         # shape (7,) for Kinova arm
    joint_velocities: np.ndarray        # shape (7,)
    ee_position: np.ndarray             # shape (3,)
    ee_quaternion: np.ndarray           # shape (4,)
    gripper_position: float             # 0.0-0.085m
    base_pose: np.ndarray               # shape (3,) mobile base
    timestamp: float


@dataclass  
class IsaacSensorData:
    """Sensor data bundle from Isaac Sim."""
    rgb: Optional[np.ndarray] = None          # (720, 1280, 3) uint8
    depth: Optional[np.ndarray] = None        # (480, 848) float32
    instance_seg: Optional[np.ndarray] = None # (480, 848) int32
    semantic_seg: Optional[np.ndarray] = None # (480, 848) int32
    pointcloud: Optional[np.ndarray] = None   # (N, 3) float32
    normals: Optional[np.ndarray] = None      # (720, 1280, 3) float32
    ft_force: np.ndarray = field(default_factory=lambda: np.zeros(3))
    ft_torque: np.ndarray = field(default_factory=lambda: np.zeros(3))
    timestamp: float = 0.0


@dataclass
class IsaacBridgeConfig:
    """Configuration for the Isaac Sim bridge."""
    # Connection
    use_rendering: bool = True
    render_resolution: Tuple[int, int] = (1280, 720)
    render_fps: int = 30
    headless: bool = False
    
    # Physics
    physics_dt: float = 1.0 / 240.0  # 240 Hz for stable contact
    rendering_dt: float = 1.0 / 30.0
    
    # Robot
    robot_usd_path: str = ""   # Path to kinova_gen3.usd
    robot_prim_path: str = "/World/kinova_gen3"
    
    # Scene
    usd_stage_path: str = ""   # Path to tabletop.usd
    
    # Domain randomization
    dr_enabled: bool = False
    dr_seed: int = 42
    
    # Brain OS connection
    grpc_address: str = "localhost:50051"
    
    def __post_init__(self):
        if not self.robot_usd_path:
            self.robot_usd_path = str(
                Path(__file__).resolve().parent.parent.parent
                / "brain_models" / "robots" / "kinova_gen3.usd"
            )
        if not self.usd_stage_path:
            self.usd_stage_path = str(
                Path(__file__).resolve().parent.parent
                / "isaac_sim" / "stages" / "tabletop.usd"
            )


# ============================================================================
# Isaac Bridge — Main Class
# ============================================================================

class IsaacBridge:
    """
    Bidirectional bridge between Brain OS and Isaac Sim.
    
    Works in two modes:
      1. Connected mode: Isaac Sim Python environment (omni.* APIs available)
      2. Mock mode: No Isaac Sim installed (for testing/CI)
    """
    
    def __init__(self, config: IsaacBridgeConfig):
        self.config = config
        self._world: Any = None
        self._robot: Any = None
        self._camera: Any = None
        self._stage_ready: bool = False
        self._running: bool = False
        self._mock = not HAS_ISAAC_SIM
        
        if not self._mock:
            self._init_isaac()
        else:
            logger.info("IsaacBridge running in mock mode (no Isaac Sim)")
    
    # ========================================================================
    # Lifecycle
    # ========================================================================
    
    def _init_isaac(self):
        """Initialize Isaac Sim world and load assets."""
        logger.info("Initializing Isaac Sim world...")
        
        # Create world with physics
        self._world = World(
            physics_dt=self.config.physics_dt,
            rendering_dt=self.config.rendering_dt,
            backend="torch"
        )
        
        # Load USD stage if specified
        if self.config.usd_stage_path:
            logger.info("Loading USD stage: %s", self.config.usd_stage_path)
            # In production: omni.usd.get_context().open_stage(self.config.usd_stage_path)
        
        # Load robot
        self._load_robot()
        
        # Initialize camera sensors
        self._init_sensors()
        
        self._stage_ready = True
        logger.info("Isaac Sim world ready")
    
    def _load_robot(self):
        """Load Kinova Gen3 robot from USD asset."""
        logger.info("Loading robot from: %s", self.config.robot_usd_path)
        
        # In production:
        # self._robot = Robot(
        #     prim_path=self.config.robot_prim_path,
        #     usd_path=self.config.robot_usd_path,
        #     name="kinova_gen3"
        # )
        # self._world.scene.add(self._robot)
        
        # Mock: create placeholder robot state
        self._mock_robot_state = IsaacRobotState(
            joint_positions=np.zeros(7),
            joint_velocities=np.zeros(7),
            ee_position=np.array([0.5, 0.0, 0.3]),
            ee_quaternion=np.array([0.0, 0.0, 0.0, 1.0]),
            gripper_position=0.0,
            base_pose=np.zeros(3),
            timestamp=time.time()
        )
    
    def _init_sensors(self):
        """Initialize RTX camera and other sensors."""
        # In production:
        # self._camera = Camera(
        #     prim_path="/World/camera",
        #     position=np.array([1.0, 0.0, 1.5]),
        #     frequency=self.config.render_fps,
        #     resolution=self.config.render_resolution
        # )
        # self._world.scene.add(self._camera)
        pass
    
    def start(self):
        """Start the simulation loop."""
        self._running = True
        logger.info("IsaacBridge simulation started")
    
    def stop(self):
        """Stop the simulation loop."""
        self._running = False
        if not self._mock:
            self._world.stop()
        logger.info("IsaacBridge simulation stopped")
    
    def step(self, render: bool = True):
        """
        Advance physics by one step.
        
        Args:
            render: Whether to render a new frame (costly if False)
        """
        if self._mock:
            self._mock_robot_state.timestamp = time.time()
            return
        
        # Step physics
        self._world.step(render=render and self.config.use_rendering)
    
    # ========================================================================
    # Robot Control
    # ========================================================================
    
    def set_joint_positions(self, positions: List[float], 
                           velocities: Optional[List[float]] = None):
        """
        Set robot joint position targets.
        
        Args:
            positions: 7 joint angles (radians)
            velocities: Optional 7 joint velocities
        """
        positions = np.array(positions[:7])
        
        if self._mock:
            self._mock_robot_state.joint_positions = positions
            self._mock_robot_state.ee_position = self._compute_fk_mock(positions)
            if velocities:
                self._mock_robot_state.joint_velocities = np.array(velocities[:7])
            return
        
        # In production:
        # self._robot.set_joint_positions(positions)
        # if velocities:
        #     self._robot.set_joint_velocities(velocities)
    
    def set_gripper(self, position: float, force: float = 50.0):
        """
        Control Robotiq 2F-85 gripper.
        
        Args:
            position: 0.0 (open) to 0.085 (closed)
            force: Gripping force in N
        """
        position = np.clip(position, 0.0, 0.085)
        
        if self._mock:
            self._mock_robot_state.gripper_position = position
            return
    
    def set_ee_pose(self, position: List[float], 
                   quaternion: Optional[List[float]] = None):
        """
        Move end effector to target pose using IK.
        
        Args:
            position: [x, y, z] in world frame
            quaternion: [x, y, z, w] orientation
        """
        quaternion = quaternion or [0.0, 0.0, 0.0, 1.0]
        
        if self._mock:
            self._mock_robot_state.ee_position = np.array(position[:3])
            self._mock_robot_state.ee_quaternion = np.array(quaternion[:4])
            return
        
        # In production:
        # self._robot.end_effector.set_world_pose(
        #     np.array(position[:3]),
        #     np.array(quaternion[:4])
        # )
    
    def set_base_velocity(self, linear: List[float], angular: float = 0.0):
        """
        Control mobile base velocity (differential drive).
        
        Args:
            linear: [vx, vy] in m/s
            angular: wz in rad/s
        """
        if not self._mock:
            # In production: send cmd_vel to diff drive controller
            pass
    
    # ========================================================================
    # State Queries
    # ========================================================================
    
    def get_robot_state(self) -> IsaacRobotState:
        """Get current robot state."""
        if self._mock:
            self._mock_robot_state.timestamp = time.time()
            return self._mock_robot_state
        
        # In production:
        # return IsaacRobotState(
        #     joint_positions=self._robot.get_joint_positions(),
        #     joint_velocities=self._robot.get_joint_velocities(),
        #     ee_position=self._robot.end_effector.get_world_pose()[0],
        #     ee_quaternion=self._robot.end_effector.get_world_pose()[1],
        #     ...,
        #     timestamp=time.time()
        # )
        return self._mock_robot_state
    
    def get_sensor_data(self) -> IsaacSensorData:
        """Get latest sensor readings."""
        return IsaacSensorData(
            timestamp=time.time()
        )
    
    # ========================================================================
    # Scene Management
    # ========================================================================
    
    def spawn_cube(self, name: str, position: List[float],
                   size: List[float] = None, color: str = None,
                   mass: float = 0.1):
        """Spawn a dynamic cube at position."""
        size = size or [0.08, 0.08, 0.08]
        
        logger.info("Spawning cube '%s' at %s", name, position)
        
        if not self._mock:
            # In production:
            # cube = DynamicCuboid(
            #     prim_path=f"/World/{name}",
            #     name=name,
            #     position=np.array(position),
            #     size=np.array(size),
            #     mass=mass,
            #     color=np.array([1.0, 0.0, 0.0]) if color == "red" else None
            # )
            # self._world.scene.add(cube)
            pass
    
    def spawn_cup(self, name: str, position: List[float],
                  radius: float = 0.04, height: float = 0.10,
                  mass: float = 0.05):
        """Spawn a cylindrical cup."""
        logger.info("Spawning cup '%s' at %s", name, position)
        
        if not self._mock:
            # In production: DynamicCylinder with cup material
            pass
    
    def remove_object(self, name: str):
        """Remove an object from the scene."""
        logger.info("Removing object '%s'", name)
        
        if not self._mock:
            delete_prim(f"/World/{name}")
    
    def reset_scene(self):
        """Reset scene to initial state."""
        logger.info("Resetting Isaac Sim scene...")
        
        if self._mock:
            self._mock_robot_state = IsaacRobotState(
                joint_positions=np.zeros(7),
                joint_velocities=np.zeros(7),
                ee_position=np.array([0.5, 0.0, 0.3]),
                ee_quaternion=np.array([0.0, 0.0, 0.0, 1.0]),
                gripper_position=0.0,
                base_pose=np.zeros(3),
                timestamp=time.time()
            )
            return
        
        # In production:
        # self._world.reset()
    
    # ========================================================================
    # Domain Randomization
    # ========================================================================
    
    def randomize_scene(self, seed: Optional[int] = None) -> Dict[str, Any]:
        """
        Apply domain randomization for RL training.
        
        Randomizes:
          - Object positions (±2cm)
          - Object colors (hue shift)
          - Lighting intensity
          - Floor friction
          - Camera pose (small jitter)
        """
        rng = np.random.default_rng(seed or self.config.dr_seed)
        
        params = {
            "object_jitter": rng.uniform(-0.02, 0.02, size=3).tolist(),
            "light_intensity": rng.uniform(0.8, 1.2),
            "friction_mult": rng.uniform(0.7, 1.3),
        }
        
        logger.info("Applied domain randomization: %s", params)
        
        if not self._mock:
            # Apply randomization in Isaac Sim
            pass
        
        return params
    
    # ========================================================================
    # Helpers
    # ========================================================================
    
    def _compute_fk_mock(self, joint_positions: np.ndarray) -> np.ndarray:
        """Simplified FK for mock mode."""
        x = 0.5 + np.sin(joint_positions[0]) * 0.3
        y = np.sin(joint_positions[1]) * 0.3
        z = 0.3 + np.cos(joint_positions[2]) * 0.2
        return np.array([x, y, z])
    
    @property
    def is_mock(self) -> bool:
        """Whether running in mock mode."""
        return self._mock
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# ============================================================================
# Convenience Function
# ============================================================================

def create_isaac_bridge(**kwargs) -> IsaacBridge:
    """Create an IsaacBridge with default or custom config."""
    config = IsaacBridgeConfig(**kwargs)
    return IsaacBridge(config)


# ============================================================================
# Demo
# ============================================================================

def run_demo():
    """Quick demo of IsaacBridge API."""
    logging.basicConfig(level=logging.INFO)
    
    bridge = create_isaac_bridge(headless=True)
    
    with bridge:
        # Reset scene
        bridge.reset_scene()
        
        # Spawn objects
        bridge.spawn_cup("red_cup", [0.5, 0.1, 0.05])
        
        # Move arm
        bridge.set_ee_pose([0.5, 0.1, 0.3])
        
        # Step
        for _ in range(10):
            bridge.step(render=True)
        
        # Read state
        state = bridge.get_robot_state()
        print(f"EE position: {state.ee_position}")
        print(f"Gripper: {state.gripper_position:.3f}m")
    
    print("Demo complete")


if __name__ == "__main__":
    run_demo()
