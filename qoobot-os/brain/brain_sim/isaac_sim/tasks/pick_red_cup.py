"""
Isaac Sim Task: Pick Red Cup
=============================
Task-specific configuration for the "Pick Red Cup" manipulation skill.

This file defines:
  - Task parameters (object type, target location, tolerance)
  - Skill decomposition (sub-tasks)
  - Success criteria
  - Integration with Brain OS skill registry

Used by:
  - RL training (Isaac Lab)
  - Behaviour tree skill nodes
  - Brain OS SkillManager
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Skill Definition
# ============================================================================

class SkillPhase(Enum):
    """Skill execution phases."""
    APPROACH = "approach"       # Move EE close to object
    PRE_GRASP = "pre_grasp"     # Align gripper with object
    GRASP = "grasp"             # Close gripper
    LIFT = "lift"               # Lift object from surface
    MOVE = "move"               # Move object to target
    PLACE = "place"             # Lower and release
    RETRACT = "retract"         # Move EE away


@dataclass
class PickRedCupConfig:
    """
    Task configuration for "pick red cup" skill.
    
    This maps to the Brain OS skill registry:
      skill_name: "pick_red_cup"
      skill_type: "manipulation"
      category: "pick_and_place"
    """
    
    # Task identity
    skill_name: str = "pick_red_cup"
    description: str = "Grasp the red cup from the coffee table"
    category: str = "pick_and_place"
    
    # Object to pick
    target_object: str = "red_cup"
    object_color: str = "red"       # Visual feature for detection
    object_type: str = "cup"        # Grasp strategy selector
    
    # Target location (where to place, relative to world)
    target_position: List[float] = field(default_factory=lambda: [0.40, 0.10, 0.15])
    target_orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    
    # Grasp parameters
    grasp_force: float = 50.0       # N
    grasp_width: float = 0.06       # m (cup diameter ≈ 70mm, gripper close to 60mm)
    grasp_approach_offset: float = 0.05  # Offset above object before grasp
    
    # Tolerance
    position_tolerance: float = 0.02   # m
    orientation_tolerance: float = 0.1  # rad
    
    # Execution
    max_velocity: float = 1.0       # m/s end effector
    timeout_seconds: float = 30.0   # Max execution time
    
    # RL training (Isaac Lab)
    rl_enabled: bool = True
    observation_type: str = "full"             # full, visual, tactile
    curriculum_enabled: bool = True            # Progressive task difficulty
    domain_randomization: bool = True           # Randomize object pose/color/lighting
    
    # Domain randomization ranges (for RL)
    dr_object_position_noise: float = 0.02     # m
    dr_object_rotation_noise: float = 0.1      # rad
    dr_lighting_intensity_range: Tuple[float, float] = (0.8, 1.2)
    dr_friction_range: Tuple[float, float] = (0.5, 1.5)


# ============================================================================
# Sub-Task Decomposition
# ============================================================================

@dataclass
class SubTask:
    """A sub-task in the pick-red-cup skill."""
    name: str
    phase: SkillPhase
    description: str
    prerequisite: Optional[str] = None  # Must complete before this
    
    # Motion parameters
    target_joint_positions: Optional[List[float]] = None
    target_ee_pose: Optional[Dict[str, Any]] = None
    gripper_action: Optional[str] = None  # "open", "close", "hold"
    
    # Success conditions
    success_condition: str = ""  # Descriptive condition
    timeout: float = 5.0  # seconds


def get_subtasks(config: PickRedCupConfig) -> List[SubTask]:
    """
    Generate the sub-task sequence for pick-red-cup.
    
    Returns ordered list of SubTasks forming the execution plan.
    This is what the Brain OS TaskDecomposer outputs.
    """
    return [
        SubTask(
            name="approach_cup",
            phase=SkillPhase.APPROACH,
            description="Move end effector 5cm above the red cup",
            target_ee_pose={
                "position": [0.40, 0.10, 0.20],  # 5cm above cup
                "quaternion": [0.0, 0.707, 0.0, 0.707]  # Gripper pointing down
            },
            gripper_action="open",
            success_condition="EE within 2cm of approach pose",
            timeout=5.0
        ),
        SubTask(
            name="pre_grasp_align",
            phase=SkillPhase.PRE_GRASP,
            description="Align gripper fingers around the cup",
            prerequisite="approach_cup",
            target_ee_pose={
                "position": [0.40, 0.10, 0.12],  # At cup grasp height
                "quaternion": [0.0, 0.707, 0.0, 0.707]
            },
            gripper_action="open",
            success_condition="EE within 1cm of grasp pose",
            timeout=3.0
        ),
        SubTask(
            name="grasp_cup",
            phase=SkillPhase.GRASP,
            description="Close gripper to grasp the cup",
            prerequisite="pre_grasp_align",
            gripper_action="close",
            success_condition="Gripper force > threshold AND cup moves with EE",
            timeout=2.0
        ),
        SubTask(
            name="lift_cup",
            phase=SkillPhase.LIFT,
            description="Lift cup 15cm above table",
            prerequisite="grasp_cup",
            target_ee_pose={
                "position": [0.40, 0.10, 0.30],
                "quaternion": [0.0, 0.707, 0.0, 0.707]
            },
            gripper_action="hold",
            success_condition="Cup height > 0.25m AND still grasped",
            timeout=5.0
        ),
        SubTask(
            name="move_to_target",
            phase=SkillPhase.MOVE,
            description="Move cup to target position",
            prerequisite="lift_cup",
            target_ee_pose={
                "position": config.target_position,
                "quaternion": config.target_orientation
            },
            gripper_action="hold",
            success_condition="EE within 2cm of target pose",
            timeout=10.0
        ),
        SubTask(
            name="place_cup",
            phase=SkillPhase.PLACE,
            description="Lower cup to surface and release",
            prerequisite="move_to_target",
            target_ee_pose={
                "position": [
                    config.target_position[0],
                    config.target_position[1],
                    config.target_position[2] + 0.05  # 5cm above placement
                ],
                "quaternion": config.target_orientation
            },
            gripper_action="open",
            success_condition="Gripper open AND cup resting on surface",
            timeout=3.0
        ),
        SubTask(
            name="retract",
            phase=SkillPhase.RETRACT,
            description="Move arm clear of the workspace",
            prerequisite="place_cup",
            target_ee_pose={
                "position": [0.50, 0.10, 0.40],
                "quaternion": [0.0, 0.0, 0.0, 1.0]
            },
            gripper_action="open",
            success_condition="EE > 30cm above table",
            timeout=3.0
        ),
    ]


# ============================================================================
# Integration Layer
# ============================================================================

def register_with_brain_os() -> Dict[str, Any]:
    """
    Register this skill with the Brain OS skill registry.
    
    Returns the skill manifest that Brain OS SkillManager understands.
    """
    config = PickRedCupConfig()
    
    return {
        "skill_name": config.skill_name,
        "version": "1.0.0",
        "description": config.description,
        "category": config.category,
        "parameters": {
            "target_object": config.target_object,
            "target_position": config.target_position,
        },
        "subtasks": [
            {
                "name": st.name,
                "phase": st.phase.value,
                "description": st.description,
                "timeout": st.timeout
            }
            for st in get_subtasks(config)
        ],
        "capabilities": [
            "visual_detection",     # Need to detect red cup
            "inverse_kinematics",   # Need IK solver
            "force_control",        # Need FT sensor feedback
            "collision_avoidance",  # Safety monitoring
        ],
        "preconditions": [
            "robot.arm.is_calibrated",
            "camera.rgb.streaming",
            "safety.collision_check.active",
        ],
        "postconditions": [
            "cup.is_at_target",
            "gripper.is_open",
            "arm.is_at_safe_pose",
        ],
    }


# ============================================================================
# RL Training Configuration
# ============================================================================

def get_training_config() -> Dict[str, Any]:
    """
    Get Isaac Lab training configuration for pick_red_cup.
    
    Compatible with omni.isaac.lab Runner.
    """
    config = PickRedCupConfig()
    
    return {
        "task_name": "BrainOS-PickAndPlace-v0",
        "task_entry": "brain_sim.isaac_sim.environments.pick_and_place:PickAndPlaceEnv",
        "task_config": {
            "task": config.skill_name,
            "headless": True,
            "max_episode_steps": 200,
            "reward_type": "dense",
        },
        
        # Training hyperparameters
        "algorithm": "PPO",
        "num_envs": 4096,          # Parallel environments
        "total_timesteps": 100_000_000,  # 100M steps
        "learning_rate": 3e-4,
        "batch_size": 1024,
        "n_steps": 64,
        "gamma": 0.99,
        "gae_lambda": 0.95,
        "ent_coef": 0.01,
        "vf_coef": 0.5,
        
        # Network architecture
        "policy": "MultiInputPolicy",
        "net_arch": [512, 256, 128],
        "activation_fn": "ReLU",
        
        # Domain randomization
        "domain_randomization": config.domain_randomization,
        "dr_params": {
            "object_position_noise": config.dr_object_position_noise,
            "object_rotation_noise": config.dr_object_rotation_noise,
            "lighting_range": config.dr_lighting_intensity_range,
            "friction_range": config.dr_friction_range,
        },
        
        # Logging & checkpointing
        "log_interval": 10_000,
        "save_interval": 100_000,
        "checkpoint_path": "models/pick_red_cup/checkpoints/",
        "tensorboard_dir": "logs/pick_red_cup/",
    }


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    # Print skill manifest
    import json
    skill_manifest = register_with_brain_os()
    print(json.dumps(skill_manifest, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("Sub-task Sequence:")
    print("=" * 60)
    for i, st in enumerate(get_subtasks(PickRedCupConfig())):
        print(f"  {i+1}. [{st.phase.value}] {st.name}: {st.description}")
        if st.prerequisite:
            print(f"     requires: {st.prerequisite}")
    
    print("\n" + "=" * 60)
    print("Training Config Summary:")
    print("=" * 60)
    tc = get_training_config()
    print(f"  Algorithm: {tc['algorithm']}")
    print(f"  Parallel envs: {tc['num_envs']}")
    print(f"  Total steps: {tc['total_timesteps']:,}")
    print(f"  DR enabled: {tc['domain_randomization']}")
