/**
 * src/types/proto.ts — TypeScript types mirroring brain_proto definitions
 *
 * These types correspond to the protobuf message definitions in brain_proto/proto/.
 * They provide type-safe interfaces for gRPC service interactions on the frontend.
 */

// ── Common Types (mirrors common/types.proto) ────────────
export interface ProtoVector3 {
  x: number;
  y: number;
  z: number;
}

export interface ProtoQuaternion {
  x: number;
  y: number;
  z: number;
  w: number;
}

export interface ProtoPose {
  position: ProtoVector3;
  orientation: ProtoQuaternion;
}

export interface ProtoBoundingBox3D {
  center: ProtoPose;
  dimensions: ProtoVector3;
}

export interface ProtoHeader {
  timestamp: string;
  frame_id: string;
  seq: number;
}

// ── Perception Types (mirrors perception/types.proto) ───
export interface ProtoDetectedObject {
  id: string;
  label: string;
  confidence: number;
  bbox_3d: ProtoBoundingBox3D;
  pose: ProtoPose;
  mask_points?: ProtoVector3[];
}

export interface ProtoSceneGraph {
  header: ProtoHeader;
  objects: ProtoDetectedObject[];
  robot_pose: ProtoPose;
  occupancy_grid?: number[];
  grid_resolution?: number;
}

export interface ProtoLocalization {
  header: ProtoHeader;
  pose: ProtoPose;
  covariance: number[];  // 6x6 matrix flattened
  map_id: string;
}

// ── Cognition Types ──────────────────────────────────────
export interface ProtoIntent {
  action: string;
  target: string;
  source: string;
  constraints: string[];
  confidence: number;
  raw_text: string;
}

export interface ProtoSubTask {
  id: string;
  skill: string;
  parameters: Record<string, string>;
  preconditions: string[];
  expected_outcome: string;
  priority: number;
}

export interface ProtoBehaviorTree {
  xml: string;
  nodes: number;
  version: string;
}

// ── Decision Types ───────────────────────────────────────
export interface ProtoWaypoint {
  pose: ProtoPose;
  time_from_start_sec: number;
  velocity: ProtoVector3;
  acceleration: ProtoVector3;
}

export interface ProtoTrajectory {
  id: string;
  strategy: string;
  waypoints: ProtoWaypoint[];
  score: number;
  collision_free: boolean;
  duration_sec: number;
}

export interface ProtoExecutionPlan {
  id: string;
  task_id: string;
  bt_xml: string;
  trajectories: ProtoTrajectory[];
  selected_strategy: string;
  status: string;
}

// ── Control Types ────────────────────────────────────────
export interface ProtoJointCommand {
  names: string[];
  positions: number[];
  velocities: number[];
  efforts: number[];
  time_from_start_sec: number;
}

export interface ProtoGripperCommand {
  position: number;
  max_effort: number;
}

export interface ProtoRobotState {
  joints: ProtoJointCommand;
  gripper_position: number;
  safety_level: string;
  emergency_stop: boolean;
  timestamp: string;
}

// ── Safety Types ─────────────────────────────────────────
export interface ProtoSafetyAlert {
  id: string;
  level: string;
  message: string;
  source: string;
  timestamp: string;
  acknowledged: boolean;
}

export interface ProtoSafetyStatus {
  level: string;
  active_alerts: ProtoSafetyAlert[];
  emergency_stop_active: boolean;
  collision_risk: number;
  force_exceeded: boolean;
  joint_limits_exceeded: boolean;
}

// ── Knowledge Types ──────────────────────────────────────
export interface ProtoEpisode {
  id: string;
  task_id: string;
  instruction: string;
  outcome: string;
  bt_xml: string;
  duration_ms: number;
  success: boolean;
  metadata: Record<string, string>;
}

// ── gRPC Service Request/Response Types ──────────────────
export interface CognitionParseIntentRequest {
  instruction: string;
  context?: string;
}

export interface CognitionParseIntentResponse {
  intent: ProtoIntent;
  alternatives: ProtoIntent[];
}

export interface CognitionDecomposeTaskRequest {
  intent: ProtoIntent;
  scene?: ProtoSceneGraph;
}

export interface CognitionDecomposeTaskResponse {
  subtasks: ProtoSubTask[];
  bt_xml: string;
}

export interface DecisionGenerateTrajectoriesRequest {
  plan_id: string;
  start_pose: ProtoPose;
  goal_pose: ProtoPose;
  scene: ProtoSceneGraph;
}

export interface DecisionGenerateTrajectoriesResponse {
  trajectories: ProtoTrajectory[];
}

export interface DecisionSelectTrajectoryRequest {
  plan_id: string;
  trajectory_id: string;
  user_override: boolean;
}

export interface DecisionSelectTrajectoryResponse {
  accepted: boolean;
  selected_trajectory: ProtoTrajectory;
}

export interface SafetyQueryStatusResponse {
  status: ProtoSafetyStatus;
}
