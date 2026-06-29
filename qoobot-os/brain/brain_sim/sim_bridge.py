"""
Brain OS Simulation Bridge
===========================
Central bridge module connecting Brain OS cognitive services to physics simulation
environments (Gazebo / Isaac Sim).

Responsibilities:
  - Scene management: spawn, remove, reset objects and robots
  - Robot control: joint positions, EE poses, gripper commands
  - Sensor data streaming: camera, LiDAR, FT sensor → Brain OS perception
  - Physics stepping and synchronization
  - Multi-world support (tabletop, warehouse, living_room)

Usage:
    from brain_sim.sim_bridge import SimBridge

    async with SimBridge(world="tabletop") as sim:
        await sim.reset()
        await sim.spawn_object("cube", position=(0.5, 0.1, 0.05))
        await sim.move_ee_to(pose={"position": [0.4, 0.1, 0.3], "quaternion": [0, 0, 0, 1]})
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# Data Types
# ============================================================================

class WorldType(Enum):
    """Supported simulation worlds."""
    TABLETOP = "tabletop"
    WAREHOUSE = "warehouse"
    LIVING_ROOM = "living_room"


class RobotType(Enum):
    """Supported robot configurations."""
    KINOVA_GEN3 = "kinova_gen3"
    TURTLEBOT4 = "turtlebot4"
    MOBILE_MANIPULATOR = "mobile_manipulator"  # TB4 base + Kinova arm


@dataclass
class Pose3D:
    """3D pose with position (xyz) and orientation (quaternion xyzw)."""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    
    @property
    def quaternion(self) -> List[float]:
        return self.orientation
    
    @property
    def xyz(self) -> List[float]:
        return self.position
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": {"x": self.position[0], "y": self.position[1], "z": self.position[2]},
            "orientation": {
                "x": self.orientation[0], "y": self.orientation[1],
                "z": self.orientation[2], "w": self.orientation[3]
            }
        }


@dataclass
class JointState:
    """Joint state for a robot."""
    names: List[str] = field(default_factory=list)
    positions: List[float] = field(default_factory=list)
    velocities: List[float] = field(default_factory=list)
    efforts: List[float] = field(default_factory=list)


@dataclass
class SimObject:
    """An object in the simulation scene."""
    name: str
    model_type: str
    pose: Pose3D
    static: bool = False
    mass: float = 0.1
    dimensions: Optional[List[float]] = None  # x, y, z in meters
    color: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.model_type,
            "pose": self.pose.to_dict(),
            "static": self.static,
            "mass": self.mass,
            "dimensions": self.dimensions,
            "color": self.color
        }


@dataclass
class CameraFrame:
    """A single camera frame."""
    rgb: Optional[bytes] = None
    depth: Optional[bytes] = None
    points: Optional[bytes] = None
    width: int = 1280
    height: int = 720
    timestamp: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "has_rgb": self.rgb is not None,
            "has_depth": self.depth is not None,
            "has_points": self.points is not None,
            "timestamp": self.timestamp
        }


@dataclass
class LidarScan:
    """A single LiDAR scan."""
    ranges: List[float] = field(default_factory=list)
    intensities: List[float] = field(default_factory=list)
    angle_min: float = -3.1416
    angle_max: float = 3.1416
    angle_increment: float = 0.01745
    timestamp: float = 0.0
    
    @property
    def num_points(self) -> int:
        return len(self.ranges)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_points": self.num_points,
            "angle_min": self.angle_min,
            "angle_max": self.angle_max,
            "angle_increment": self.angle_increment,
            "min_range": min(self.ranges) if self.ranges else 0,
            "max_range": max(self.ranges) if self.ranges else 0,
            "timestamp": self.timestamp
        }


@dataclass
class SimulationState:
    """Complete state snapshot of the simulation."""
    timestamp: float
    objects: List[SimObject]
    robot_pose: Pose3D
    joint_states: Dict[str, JointState]  # robot_name → JointState
    camera_frames: Dict[str, CameraFrame]
    lidar_scans: Dict[str, LidarScan]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "num_objects": len(self.objects),
            "robot_pose": self.robot_pose.to_dict(),
            "joint_states": {k: v.__dict__ for k, v in self.joint_states.items()},
            "cameras": {k: v.to_dict() for k, v in self.camera_frames.items()},
            "lidars": {k: v.to_dict() for k, v in self.lidar_scans.items()}
        }


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class SimConfig:
    """Simulation bridge configuration."""
    # gRPC connection to Brain OS services
    grpc_address: str = "localhost:50051"
    
    # World configuration
    world: WorldType = WorldType.TABLETOP
    robot: RobotType = RobotType.KINOVA_GEN3
    headless: bool = False  # True = no GUI
    
    # Physics configuration
    physics_engine: str = "ode"  # ode, bullet, dart
    time_step: float = 0.001
    real_time_factor: float = 1.0
    paused: bool = False
    
    # ROS 2 configuration (when using Gazebo)
    ros_namespace: str = "/brain_os"
    
    # Model paths
    gazebo_model_path: str = ""
    world_file_path: str = ""
    
    # Sensor configuration
    enable_camera: bool = True
    enable_lidar: bool = True
    enable_ft_sensor: bool = True
    camera_fps: int = 30
    lidar_hz: int = 10
    
    # Safety
    collision_check_hz: int = 100
    emergency_stop_enabled: bool = True
    
    def __post_init__(self):
        if not self.gazebo_model_path:
            self.gazebo_model_path = str(
                Path(__file__).resolve().parent.parent / "gazebo" / "models"
            )
        if not self.world_file_path:
            world_map = {
                WorldType.TABLETOP: "gazebo/worlds/tabletop.world",
                WorldType.WAREHOUSE: "gazebo/worlds/warehouse.world",
                WorldType.LIVING_ROOM: "gazebo/worlds/living_room.world",
            }
            self.world_file_path = str(
                Path(__file__).resolve().parent.parent / world_map[self.world]
            )


# ============================================================================
# SimBridge — Main Class
# ============================================================================

class SimBridge:
    """
    Brain OS Simulation Bridge.
    
    Provides a unified Python API for controlling Brain OS robots in
    physics simulation (Gazebo or Isaac Sim).
    """
    
    def __init__(self, config: Optional[SimConfig] = None, **kwargs):
        """
        Initialize the simulation bridge.
        
        Args:
            config: SimConfig object or None for defaults
            **kwargs: Override individual config fields
        """
        if config is None:
            config = SimConfig(**kwargs)
        else:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        self.config = config
        self._objects: Dict[str, SimObject] = {}
        self._sim_time: float = 0.0
        self._started: bool = False
        self._paused: bool = config.paused
        self._step_count: int = 0
        
        logger.info("SimBridge initialized: world=%s robot=%s engine=%s",
                     config.world.value, config.robot.value, config.physics_engine)
    
    # ========================================================================
    # Lifecycle
    # ========================================================================
    
    async def start(self) -> None:
        """Start the simulation bridge."""
        if self._started:
            logger.warning("SimBridge already started")
            return
        
        logger.info("Starting SimBridge...")
        self._sim_time = 0.0
        self._step_count = 0
        self._started = True
        
        # In real environment, this would:
        # 1. Connect to gRPC services (brain_os)
        # 2. Launch Gazebo/Isaac Sim process
        # 3. Initialize ROS 2 bridge
        # 4. Load world and robot models
        
        logger.info("SimBridge started (simulated mode)")
    
    async def stop(self) -> None:
        """Stop the simulation bridge."""
        if not self._started:
            return
        
        logger.info("Stopping SimBridge...")
        self._objects.clear()
        self._started = False
        self._sim_time = 0.0
        logger.info("SimBridge stopped")
    
    async def step(self, steps: int = 1) -> float:
        """
        Advance simulation by N physics steps.
        
        Args:
            steps: Number of physics steps to advance
            
        Returns:
            Current simulation time in seconds
        """
        if not self._started:
            raise RuntimeError("SimBridge not started. Call start() first.")
        
        dt = self.config.time_step
        self._sim_time += dt * steps
        self._step_count += steps
        return self._sim_time
    
    async def reset(self) -> None:
        """Reset simulation to initial state."""
        logger.info("Resetting simulation to initial state...")
        self._objects.clear()
        self._sim_time = 0.0
        self._step_count = 0
        logger.info("Simulation reset complete")
    
    async def pause(self) -> None:
        """Pause physics simulation."""
        self._paused = True
        logger.info("Simulation paused")
    
    async def resume(self) -> None:
        """Resume physics simulation."""
        self._paused = False
        logger.info("Simulation resumed")
    
    # ========================================================================
    # Scene Management
    # ========================================================================
    
    async def spawn_object(self, model_type: str, name: str,
                           position: Optional[List[float]] = None,
                           orientation: Optional[List[float]] = None,
                           mass: float = 0.1,
                           color: Optional[str] = None,
                           static: bool = False) -> SimObject:
        """
        Spawn an object in the simulation scene.
        
        Args:
            model_type: Model type (cube, cup, bottle, box, shelf, table)
            name: Unique object name
            position: [x, y, z] in meters
            orientation: [x, y, z, w] quaternion
            mass: Object mass in kg
            color: Color name or hex
            static: Whether object is static (immovable)
            
        Returns:
            The created SimObject
        """
        if name in self._objects:
            logger.warning("Object '%s' already exists, replacing", name)
        
        position = position or [0.0, 0.0, 0.0]
        orientation = orientation or [0.0, 0.0, 0.0, 1.0]
        
        obj = SimObject(
            name=name,
            model_type=model_type,
            pose=Pose3D(position=position, orientation=orientation),
            mass=mass,
            static=static,
            color=color
        )
        
        self._objects[name] = obj
        logger.info("Spawned object '%s' (type=%s) at [%.2f, %.2f, %.2f]",
                     name, model_type, *position)
        
        # In real environment, this would:
        # - Call Gazebo spawn_model service
        # - Or create USD prim in Isaac Sim
        
        return obj
    
    async def remove_object(self, name: str) -> bool:
        """
        Remove an object from the scene.
        
        Args:
            name: Object name to remove
            
        Returns:
            True if object was found and removed
        """
        if name not in self._objects:
            logger.warning("Object '%s' not found", name)
            return False
        
        del self._objects[name]
        logger.info("Removed object '%s'", name)
        return True
    
    async def set_object_pose(self, name: str, position: List[float],
                              orientation: Optional[List[float]] = None) -> bool:
        """
        Set the pose of an existing object.
        
        Args:
            name: Object name
            position: [x, y, z] new position
            orientation: [x, y, z, w] new orientation
            
        Returns:
            True if object was found and moved
        """
        if name not in self._objects:
            logger.warning("Object '%s' not found", name)
            return False
        
        obj = self._objects[name]
        obj.pose.position = position
        if orientation:
            obj.pose.orientation = orientation
        
        logger.info("Moved object '%s' to [%.2f, %.2f, %.2f]",
                     name, *position)
        return True
    
    def list_objects(self) -> List[SimObject]:
        """List all objects in the scene."""
        return list(self._objects.values())
    
    # ========================================================================
    # Robot Control
    # ========================================================================
    
    async def move_ee_to(self, target_pose: Dict[str, Any],
                         robot_name: str = "arm",
                         max_velocity: float = 1.0) -> Dict[str, Any]:
        """
        Move robot end effector to target pose (inverse kinematics).
        
        Args:
            target_pose: Dict with 'position' [x,y,z] and 'quaternion' [x,y,z,w]
            robot_name: Robot name
            max_velocity: Maximum joint velocity (rad/s)
            
        Returns:
            Dict with 'success', 'joint_positions', 'time_seconds'
        """
        pos = target_pose.get("position", [0.0, 0.0, 0.0])
        quat = target_pose.get("quaternion", [0.0, 0.0, 0.0, 1.0])
        
        # Simulated IK solution (in real env, uses TRAC-IK)
        # Returns a nominal joint configuration close to the target
        solution = [
            pos[0] * 0.5, pos[1] * 0.5, pos[2] * 0.3,
            pos[0] * 0.3, pos[1] * 0.3, pos[2] * 0.2,
            pos[2] * 0.5
        ]
        
        travel_time = max(abs(j) / max_velocity for j in solution) if any(solution) else 0.1
        
        logger.info("EE moved to [%.2f, %.2f, %.2f] in %.3fs (simulated IK)",
                     *pos, travel_time)
        
        return {
            "success": True,
            "joint_positions": solution,
            "time_seconds": travel_time,
            "ik_method": "trac_ik_simulated"
        }
    
    async def set_joint_positions(self, joint_positions: List[float],
                                  robot_name: str = "arm",
                                  max_velocity: float = 1.0) -> Dict[str, Any]:
        """
        Set robot joint positions directly.
        
        Args:
            joint_positions: List of 7 joint angles (radians) for Kinova arm
            robot_name: Robot name
            max_velocity: Maximum joint velocity
            
        Returns:
            Dict with 'success', 'time_seconds'
        """
        if len(joint_positions) < 7:
            logger.warning("Expected 7 joint positions, got %d", len(joint_positions))
        
        travel_time = max(abs(j) / max_velocity for j in joint_positions) if any(joint_positions) else 0.1
        
        logger.info("Set %d joint positions in %.3fs",
                     len(joint_positions), travel_time)
        
        return {
            "success": True,
            "time_seconds": travel_time,
            "joint_positions": joint_positions
        }
    
    async def control_gripper(self, position: float,
                              robot_name: str = "arm",
                              max_effort: float = 100.0) -> Dict[str, Any]:
        """
        Control the Robotiq 2F-85 gripper.
        
        Args:
            position: 0.0 (fully open) to 0.085 (fully closed) — 85mm stroke
            robot_name: Robot name
            max_effort: Maximum gripping force (N)
            
        Returns:
            Dict with 'success', 'position', 'is_grasped'
        """
        position = max(0.0, min(0.085, position))
        
        # Simulated grasp force: higher position = more closed = higher chance
        is_grasped = position > 0.04  # Estimated closure threshold for grip
        
        logger.info("Gripper set to %.3fmm (max_effort=%.1fN, grasped=%s)",
                     position * 1000, max_effort, is_grasped)
        
        return {
            "success": True,
            "position": position,
            "max_effort": max_effort,
            "is_grasped": is_grasped,
            "stroke_mm": position * 1000
        }
    
    async def get_robot_pose(self, robot_name: str = "arm") -> Pose3D:
        """Get current robot base pose."""
        # In real env, reads from Gazebo/ROS2 TF
        return Pose3D()
    
    async def get_ee_pose(self, robot_name: str = "arm") -> Pose3D:
        """Get current end effector pose (forward kinematics)."""
        # In real env, computes FK from joint states
        return Pose3D(position=[0.5, 0.0, 0.5])
    
    async def get_joint_states(self, robot_name: str = "arm") -> JointState:
        """Get current joint states for a robot."""
        # In real env, subscribes to /joint_states ROS2 topic
        arm_joint_names = [
            "joint_1", "joint_2", "joint_3", "joint_4",
            "joint_5", "joint_6", "joint_7",
            "finger_left_joint", "finger_right_joint"
        ]
        return JointState(
            names=arm_joint_names,
            positions=[0.0] * 9,
            velocities=[0.0] * 9,
            efforts=[0.0] * 9
        )
    
    # ========================================================================
    # Sensor Data
    # ========================================================================
    
    async def get_camera_frame(self, camera_name: str = "oakd") -> CameraFrame:
        """Get latest camera frame (RGB + Depth)."""
        return CameraFrame(
            width=1280,
            height=720,
            timestamp=self._sim_time
        )
    
    async def get_lidar_scan(self, lidar_name: str = "rplidar") -> LidarScan:
        """Get latest LiDAR scan."""
        return LidarScan(
            ranges=[1.0] * 360,  # Placeholder
            intensities=[128] * 360,
            timestamp=self._sim_time
        )
    
    async def get_wrist_ft(self) -> Dict[str, List[float]]:
        """Get wrist force-torque sensor readings."""
        return {
            "force": [0.0, 0.0, 0.0],    # Fx, Fy, Fz (N)
            "torque": [0.0, 0.0, 0.0]    # Tx, Ty, Tz (Nm)
        }
    
    # ========================================================================
    # State Snapshot
    # ========================================================================
    
    async def get_state(self) -> SimulationState:
        """Get complete simulation state snapshot."""
        return SimulationState(
            timestamp=self._sim_time,
            objects=self.list_objects(),
            robot_pose=await self.get_robot_pose(),
            joint_states={"arm": await self.get_joint_states()},
            camera_frames={"oakd": await self.get_camera_frame()},
            lidar_scans={"rplidar": await self.get_lidar_scan()}
        )
    
    # ========================================================================
    # Utility
    # ========================================================================
    
    @property
    def sim_time(self) -> float:
        """Current simulation time in seconds."""
        return self._sim_time
    
    @property
    def is_running(self) -> bool:
        """Whether the simulation is currently running."""
        return self._started and not self._paused
    
    @property
    def step_count(self) -> int:
        """Total physics steps executed."""
        return self._step_count
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()


# ============================================================================
# Convenience Functions
# ============================================================================

def create_sim_config(world: str = "tabletop", robot: str = "kinova_gen3",
                      headless: bool = False, **kwargs) -> SimConfig:
    """
    Create a SimConfig from string arguments.
    
    Args:
        world: "tabletop", "warehouse", or "living_room"
        robot: "kinova_gen3", "turtlebot4", or "mobile_manipulator"
        headless: Run without GUI
        **kwargs: Additional config overrides
        
    Returns:
        Configured SimConfig
    """
    world_map = {
        "tabletop": WorldType.TABLETOP,
        "warehouse": WorldType.WAREHOUSE,
        "living_room": WorldType.LIVING_ROOM,
    }
    robot_map = {
        "kinova_gen3": RobotType.KINOVA_GEN3,
        "turtlebot4": RobotType.TURTLEBOT4,
        "mobile_manipulator": RobotType.MOBILE_MANIPULATOR,
    }
    
    return SimConfig(
        world=world_map.get(world, WorldType.TABLETOP),
        robot=robot_map.get(robot, RobotType.KINOVA_GEN3),
        headless=headless,
        **kwargs
    )


async def run_tabletop_demo():
    """Quick demo of the SimBridge API."""
    config = create_sim_config(world="tabletop", robot="kinova_gen3")
    
    async with SimBridge(config) as sim:
        await sim.reset()
        
        # Setup scene
        await sim.spawn_object("cube", "test_cube",
                               position=[0.5, 0.1, 0.05], mass=0.1)
        
        # Move arm
        result = await sim.move_ee_to({
            "position": [0.5, 0.1, 0.3],
            "quaternion": [0, 0, 0, 1]
        })
        print(f"Move result: {result}")
        
        # Gripper
        grip_result = await sim.control_gripper(0.04)
        print(f"Grip result: {grip_result}")
        
        # State snapshot
        state = await sim.get_state()
        print(f"Sim state: {state.to_dict()}")
        
        # Step physics
        await sim.step(100)
        print(f"Sim time: {sim.sim_time:.3f}s, steps: {sim.step_count}")


# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s"
    )
    
    asyncio.run(run_tabletop_demo())
