"""
brain_sim — Brain OS Simulation Module

Phase 2 M6: 真实物理仿真验证层。
通过 SimBridge 连接 MuJoCo/Gazebo/Isaac Sim 后端，
提供 Brain OS 认知服务的仿真测试环境。
"""

from brain_sim.sim_bridge import (
    SimBridge,
    SimConfig,
    SimObject,
    JointState,
    Pose3D,
    CameraFrame,
    LidarScan,
    SimulationState,
    WorldType,
    RobotType,
    create_sim_config,
)

__all__ = [
    "SimBridge",
    "SimConfig",
    "SimObject",
    "JointState",
    "Pose3D",
    "CameraFrame",
    "LidarScan",
    "SimulationState",
    "WorldType",
    "RobotType",
    "create_sim_config",
]
