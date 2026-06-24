"""
Isaac Sim Environment: Pick and Place
======================================
Defines the reinforcement learning environment for a Kinova Gen3 arm
performing pick-and-place tasks in NVIDIA Isaac Sim.

Supported tasks:
  - pick_cup: Grasp a red cup from the table
  - place_cup: Place cup at target position
  - stack_boxes: Stack two boxes
  - pick_any: Pick a specified object type

Uses Isaac Sim's RL environment framework (omni.isaac.lab compatible).
"""

import gymnasium as gym
import numpy as np
import torch
from typing import Any, Dict, Optional, Tuple


class PickAndPlaceEnv(gym.Env):
    """
    RL environment for tabletop pick-and-place with Kinova Gen3.
    
    Observation Space:
        - Joint positions (7) → rad
        - Joint velocities (7) → rad/s
        - EE position (3) → m
        - Object relative position (3) → m
        - Gripper state (2) → open/close
        - Camera embedding (64) → visual features
        Total: 86-dim
    
    Action Space:
        - Delta joint positions (7) → rad
        - Gripper command (1) → 0-1
        Total: 8-dim
    
    Reward:
        - Approach reward: -distance_to_target
        - Grasp reward: +1.0 for successful grasp
        - Lift reward: +2.0 for lifting object >10cm
        - Place reward: +5.0 for placing at target
        - Collision penalty: -10.0 per collision
    """
    
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 30}
    
    # Action/Observation dimensions
    ACTION_DIM = 8       # 7 joint deltas + 1 gripper
    OBS_DIM = 86         # Full observation
    
    def __init__(
        self,
        task: str = "pick_cup",
        headless: bool = True,
        max_episode_steps: int = 200,
        reward_type: str = "dense",
        seed: int = 42,
        **kwargs
    ):
        super().__init__()
        
        self.task = task
        self.headless = headless
        self.max_episode_steps = max_episode_steps
        self.reward_type = reward_type
        self.rng = np.random.default_rng(seed)
        
        # Episode state
        self._step_count = 0
        self._grasped = False
        self._collision_count = 0
        
        # Define spaces
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(self.OBS_DIM,), dtype=np.float32
        )
        
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0,
            shape=(self.ACTION_DIM,), dtype=np.float32
        )
        
        # Target positions per task
        self._target_positions = {
            "pick_cup": np.array([0.40, 0.10, 0.15]),
            "place_cup": np.array([0.60, -0.10, 0.12]),
            "stack_boxes": np.array([0.45, 0.00, 0.20]),
        }
        
        # Robot configuration
        self._home_joints = np.array([
            0.0, 0.26, 3.14, -2.27, 0.0, 0.96, 1.57
        ])
        
        # Current state (simulated)
        self._joint_positions = self._home_joints.copy()
        self._joint_velocities = np.zeros(7)
        self._ee_position = np.array([0.50, 0.0, 0.30])
        self._gripper_state = np.zeros(2)  # [left, right] finger positions
        self._object_position = np.zeros(3)
        
        self._init_isaac_sim()
    
    def _init_isaac_sim(self):
        """
        Initialize Isaac Sim stage, load robot + objects.
        
        In production, this:
        1. Creates Isaac Sim app instance
        2. Loads USD stage (tabletop.usd)
        3. Spawns Kinova Gen3 from USD asset
        4. Configures PhysX physics
        5. Sets up RTX rendering
        """
        # Placeholder — real implementation loads USD assets
        self._sim_initialized = True
        print(f"[Isaac Sim] Environment initialized: task={self.task}, "
              f"headless={self.headless}")
    
    # ========================================================================
    # Gym Interface
    # ========================================================================
    
    def reset(self, seed: Optional[int] = None, **kwargs) -> Tuple[np.ndarray, Dict]:
        """Reset environment to initial state."""
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        
        self._step_count = 0
        self._grasped = False
        self._collision_count = 0
        
        # Reset robot to home position
        self._joint_positions = self._home_joints.copy()
        self._joint_velocities = np.zeros(7)
        self._ee_position = self._compute_fk(self._home_joints)
        self._gripper_state = np.zeros(2)
        
        # Randomize object position slightly for robustness
        base_pos = self._target_positions.get(self.task, np.array([0.40, 0.10, 0.10]))
        noise = self.rng.uniform(-0.02, 0.02, size=2)
        self._object_position = np.array([
            base_pos[0] + noise[0],
            base_pos[1] + noise[1],
            base_pos[2]
        ])
        
        return self._get_obs(), self._get_info()
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one step in the environment.
        
        Args:
            action: [joint_delta_1..7, gripper_command]
            
        Returns:
            (observation, reward, terminated, truncated, info)
        """
        self._step_count += 1
        
        # Parse action
        joint_delta = action[:7] * 0.05  # Scale to max 0.05 rad/step
        gripper_cmd = float(action[7])
        
        # Apply joint limits
        self._joint_positions = np.clip(
            self._joint_positions + joint_delta,
            -3.14, 3.14
        )
        
        # Update ee position (simplified FK)
        self._ee_position = self._compute_fk(self._joint_positions)
        
        # Update gripper
        gripper_target = gripper_cmd * 0.085  # 0-85mm stroke
        self._gripper_state = np.clip(
            np.array([gripper_target, gripper_target]),
            0.0, 0.085
        )
        
        # Check grasp (simplified: close enough to object)
        dist_to_object = np.linalg.norm(self._ee_position - self._object_position)
        if dist_to_object < 0.05 and gripper_target > 0.04:
            self._grasped = True
        
        # Compute reward
        reward = self._compute_reward(action)
        
        # Termination
        terminated = self._check_termination(dist_to_object)
        truncated = self._step_count >= self.max_episode_steps
        
        return self._get_obs(), reward, terminated, truncated, self._get_info()
    
    def render(self):
        """Render current frame."""
        pass  # In production: returns rendered image from Isaac Sim RTX
    
    def close(self):
        """Clean up Isaac Sim resources."""
        self._sim_initialized = False
    
    # ========================================================================
    # Internal Methods
    # ========================================================================
    
    def _compute_fk(self, joint_positions: np.ndarray) -> np.ndarray:
        """
        Simplified forward kinematics for Kinova Gen3.
        
        In production, uses omni.isaac.core for accurate FK.
        """
        # Simplified: EE roughly moves with joint positions
        x = 0.5 + np.sin(joint_positions[0]) * 0.3
        y = np.sin(joint_positions[1]) * 0.3
        z = 0.3 + np.cos(joint_positions[2]) * 0.2
        
        # If grasped, object follows EE
        if self._grasped:
            self._object_position = np.array([x, y, z - 0.1])
        
        return np.array([x, y, z])
    
    def _compute_reward(self, action: np.ndarray) -> float:
        """
        Compute step reward.
        
        Dense: distance-based shaping
        Sparse: only terminal reward
        """
        dist_to_object = np.linalg.norm(self._ee_position - self._object_position)
        target_pos = self._target_positions.get(self.task, self._object_position)
        dist_to_target = np.linalg.norm(self._object_position - target_pos)
        
        if self.reward_type == "sparse":
            if self._grasped and dist_to_target < 0.05:
                return 5.0
            elif self._grasped:
                return 1.0
            else:
                return -0.01  # Small penalty per step
        
        # Dense reward
        reward = 0.0
        
        # Approach reward
        reward -= dist_to_object * 0.5
        
        # Grasp reward
        if dist_to_object < 0.05:
            reward += 0.2
        
        # Grasped reward
        if self._grasped:
            reward += 0.5
            reward -= dist_to_target * 0.5
        
        # Action smoothness penalty
        reward -= np.linalg.norm(action[:7]) * 0.01
        
        # Collision penalty
        reward -= self._collision_count * 10.0
        
        return float(reward)
    
    def _check_termination(self, dist_to_object: float) -> bool:
        """Check if episode should terminate."""
        # Success: grasped and at target
        if self._grasped and dist_to_object < 0.05:
            return True
        
        # Failure: too many collisions
        if self._collision_count > 5:
            return True
        
        # Failure: object dropped off table
        if self._object_position[2] < -0.1:
            return True
        
        return False
    
    def _get_obs(self) -> np.ndarray:
        """Construct observation vector."""
        obs = np.concatenate([
            self._joint_positions,           # 7
            self._joint_velocities,           # 7
            self._ee_position,                # 3
            self._object_position - self._ee_position,  # 3: relative
            self._gripper_state,              # 2
            np.zeros(64),                     # 64: camera embedding (placeholder)
        ])
        return obs.astype(np.float32)
    
    def _get_info(self) -> Dict[str, Any]:
        """Return environment info dict."""
        return {
            "step": self._step_count,
            "grasped": self._grasped,
            "collisions": self._collision_count,
            "ee_position": self._ee_position.tolist(),
            "object_position": self._object_position.tolist(),
            "gripper_state": self._gripper_state.tolist(),
        }
    
    # ========================================================================
    # Public API for Brain OS Integration
    # ========================================================================
    
    def get_ee_pose(self) -> Dict[str, Any]:
        """Get end effector pose (for Brain OS motion planner)."""
        return {
            "position": self._ee_position.tolist(),
            "quaternion": [0.0, 0.0, 0.0, 1.0],
            "grasped": self._grasped
        }
    
    def get_object_pose(self) -> Dict[str, Any]:
        """Get target object pose (for Brain OS perception)."""
        return {
            "position": self._object_position.tolist(),
            "quaternion": [0.0, 0.0, 0.0, 1.0]
        }
    
    def set_joint_positions(self, positions: np.ndarray) -> None:
        """Set robot joint positions directly (from Brain OS controller)."""
        self._joint_positions = np.array(positions[:7])
        self._ee_position = self._compute_fk(self._joint_positions)


# ============================================================================
# Registration (compatible with gymnasium / omni.isaac.lab)
# ============================================================================

gym.register(
    id="BrainOS-PickAndPlace-v0",
    entry_point="pick_and_place:PickAndPlaceEnv",
    max_episode_steps=200,
)
