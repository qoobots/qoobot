"""
Brain OS AI Engine — LLM/VLA/Perception/Planning Runtime

Package structure:
  brain_ai/
  ├── domain/         — Pydantic data models
  ├── perception/     — Object detection, SLAM, 3DGS
  ├── llm_agent/      — Intent parsing, task decomposition, BT generation
  ├── planner/        — Motion planning, multi-strategy trajectories, HITL
  ├── vla_agent/      — Vision-Language-Action inference
  ├── model_runtime/  — TRT-LLM, llama.cpp, ONNX, vLLM adapters
  ├── knowledge/      — Working memory, experience store, vector retrieval
  ├── ros2_bridge/    — ROS 2 topic publisher/subscriber
  ├── grpc_server/    — gRPC services (cognition, decision, knowledge)
  ├── ws_server/      — WebSocket event dispatcher (for brain_viz)
  ├── voice_io/       — ASR / TTS engines
  └── utils/          — Config, logging, transforms, timer
"""

__version__ = "0.1.0"
__author__  = "Brain OS Team"

# ── Core exports ──────────────────────────────────────────
from brain_ai.domain.entities import (
    Intent,
    Task,
    Plan,
    Trajectory,
    SceneGraph,
    RobotState,
    SafetyStatus,
)

__all__ = [
    "Intent",
    "Task",
    "Plan",
    "Trajectory",
    "SceneGraph",
    "RobotState",
    "SafetyStatus",
]
