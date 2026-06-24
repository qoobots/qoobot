/**
 * src/types/domain.ts — Core domain types for Brain OS Visualization
 * Mirrors brain_ai/domain/entities.py
 */

// ── Enums ─────────────────────────────────────────────────
export type SafetyLevel = 'NORMAL' | 'WARNING' | 'CRITICAL' | 'EMERGENCY';
export type TaskStatus   = 'PENDING' | 'PLANNING' | 'AWAITING_HITL' | 'EXECUTING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type TrajectoryStrategy = 'OPTIMAL' | 'CONSERVATIVE' | 'AGGRESSIVE' | 'EXPLORATORY' | 'REVERSE';

// ── Waypoint & Trajectory ─────────────────────────────────
export interface Waypoint {
  x: number; y: number; z: number;
  qx?: number; qy?: number; qz?: number; qw?: number;
  time_from_start_sec: number;
}

export interface Trajectory {
  id: string;
  strategy: TrajectoryStrategy;
  waypoints: Waypoint[];
  score: number;           // 0..1
  collision_free: boolean;
  duration_sec: number;
}

// ── Scene ─────────────────────────────────────────────────
export interface Object3D {
  id: string;
  label: string;
  centroid: [number, number, number];
  bbox_3d?: [number, number, number][];
  confidence: number;
}

export interface SceneGraph {
  timestamp: string;
  objects: Object3D[];
  robot_pose: [number, number, number, number, number, number, number];
  occupancy_grid?: number[][][];
}

// ── Robot State ───────────────────────────────────────────
export interface JointState {
  names: string[];
  positions: number[];
  velocities: number[];
  efforts: number[];
}

export interface RobotState {
  joints: JointState;
  gripper_position: number;
  safety_level: SafetyLevel;
  emergency_stop: boolean;
  timestamp: string;
}

// ── Intent & Task ─────────────────────────────────────────
export interface Intent {
  action: string;
  target: string;
  source?: string;
  constraints: string[];
  confidence: number;
}

export interface Task {
  id: string;
  intent: Intent;
  subtasks: Task[];
  status: TaskStatus;
  created_at: string;
}

// ── Safety ────────────────────────────────────────────────
export interface SafetyStatus {
  level: SafetyLevel;
  active_warnings: string[];
  emergency_stop_active: boolean;
  collision_risk: number;
}

// ── HITL ──────────────────────────────────────────────────
export interface HITLPrompt {
  trajectories: Trajectory[];
  timeout_sec: number;
  auto_select_id?: string;
}

// ── WebSocket Events ──────────────────────────────────────
export type WSEventType =
  | 'scene_update'
  | 'ghost_trail'
  | 'safety_alert'
  | 'hitl_prompt'
  | 'robot_state'
  | 'task_status';

export interface WSEvent {
  type: WSEventType;
  payload: Record<string, unknown>;
}
