// qooremote TypeScript 类型定义
// 对应 qooremote/proto/teleop_*.proto 协议定义

/** 机器人运行模式 */
export enum RobotMode {
  AUTO = 'AUTO',
  HYBRID = 'HYBRID',
  TELEOP = 'TELEOP'
}

/** 遥控会话状态 */
export enum SessionStatus {
  INITIATING = 'INITIATING',
  CONNECTING = 'CONNECTING',
  ACTIVE = 'ACTIVE',
  PAUSED = 'PAUSED',
  CLOSING = 'CLOSING',
  CLOSED = 'CLOSED',
  REJECTED = 'REJECTED',
  TIMEOUT = 'TIMEOUT'
}

/** 控制模式 */
export enum ControlMode {
  POSITION = 'POSITION',
  VELOCITY = 'VELOCITY',
  TORQUE = 'TORQUE',
  IMPEDANCE = 'IMPEDANCE',
  ADMITTANCE = 'ADMITTANCE'
}

/** 紧急停止类型 */
export enum StopType {
  PROTECTIVE = 'PROTECTIVE',
  EMERGENCY = 'EMERGENCY',
  STO = 'STO'
}

/** 安全模式 */
export enum SafetyMode {
  NORMAL = 'NORMAL',
  REDUCED_SPEED = 'REDUCED_SPEED',
  PROTECTIVE_STOP = 'PROTECTIVE_STOP',
  EMERGENCY_STOP = 'EMERGENCY_STOP',
  STO = 'STO',
  MAINTENANCE = 'MAINTENANCE'
}

/** 通信质量 */
export enum CommQuality {
  EXCELLENT = 'EXCELLENT',
  GOOD = 'GOOD',
  FAIR = 'FAIR',
  POOR = 'POOR',
  LOST = 'LOST'
}

/** 3D 向量 */
export interface Vec3 {
  x: number
  y: number
  z: number
}

/** 四元数 */
export interface Quaternion {
  w: number
  x: number
  y: number
  z: number
}

/** 位姿 */
export interface Pose {
  position: Vec3
  orientation: Quaternion
}

/** 基座运动指令 */
export interface BaseCommand {
  vx: number
  vy: number
  omega: number
}

/** 关节目标 */
export interface JointSetpoint {
  joint_name: string
  position: number
  velocity: number
  torque_ff: number
  control_mode: ControlMode
}

/** 末端执行器指令 */
export interface GripperCommand {
  type: 'PARALLEL' | 'THREE_FINGER' | 'SUCTION' | 'DEXTEROUS'
  position: number
  grasp_force: number
  suction_on: boolean
}

/** 头部指令 */
export interface HeadCommand {
  pitch: number
  yaw: number
  roll: number
}

/** 全身运动指令 */
export interface TeleopCommand {
  timestamp_ns: number
  sequence: number
  session_id: string
  base: BaseCommand
  joints: JointSetpoint[]
  left_gripper: GripperCommand
  right_gripper: GripperCommand
  head: HeadCommand
  control_mode: ControlMode
  speed_override: number
}

/** 关节状态 */
export interface JointState {
  joint_name: string
  position: number
  velocity: number
  torque: number
  current: number
  temperature: number
  status: 'OK' | 'WARNING' | 'ERROR' | 'DISABLED'
}

/** 安全状态 */
export interface SafetyStatus {
  current_mode: SafetyMode
  active_events: string[]
  emergency_stop_engaged: boolean
  protective_stop_engaged: boolean
}

/** 电池状态 */
export interface BatteryStatus {
  state_of_charge: number
  state_of_health: number
  voltage: number
  current: number
  temperature: number
  time_remaining_s: number
}

/** 系统状态 */
export interface SystemStatus {
  cpu_usage: number
  memory_usage: number
  gpu_usage: number
  cpu_temperature: number
  board_temperature: number
  comm_quality: CommQuality
  network_latency_ms: number
  uptime_s: number
}

/** 机器人状态快照 */
export interface TeleopState {
  timestamp_ns: number
  sequence: number
  session_id: string
  base_pose: Pose
  base_velocity: Vec3
  base_angular_velocity: Vec3
  joints: JointState[]
  safety: SafetyStatus
  battery: BatteryStatus
  system: SystemStatus
}

/** 遥控会话信息 */
export interface TeleopSession {
  session_id: string
  robot_id: string
  robot_name: string
  operator_id: string
  operator_name: string
  control_mode: RobotMode
  session_status: SessionStatus
  media_types: ('VIDEO' | 'AUDIO' | 'DATA')[]
  created_at: string
  connected_at: string | null
  command_count: number
  avg_latency_ms: number
  max_latency_ms: number
}

/** 示教记录 */
export interface TeachingRecord {
  record_id: string
  session_id: string
  operator_id: string
  operator_name: string
  robot_id: string
  name: string
  description: string
  tags: string[]
  duration_ms: number
  frame_count: number
  data_format: string
  quality_score: number
  is_verified: boolean
  created_at: string
}

/** 诊断事件 */
export interface DiagnosticEvent {
  timestamp_ns: number
  severity: 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL' | 'FATAL'
  component: string
  message: string
  detail: string
}

/** API 通用响应 */
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

/** 视频流配置 */
export interface VideoStreamConfig {
  track_id: string
  label: string
  codec: 'H264' | 'H265' | 'VP8' | 'VP9' | 'AV1'
  resolution: { width: number; height: number }
  max_fps: number
  max_bitrate_kbps: number
  enabled: boolean
}

/** 媒体流统计 */
export interface StreamStats {
  track_id: string
  bytes_sent: number
  packets_sent: number
  packets_lost: number
  packet_loss_rate: number
  current_bitrate_kbps: number
  current_fps: number
  rtt_ms: number
  jitter_ms: number
  codec: string
  resolution: { width: number; height: number }
}
