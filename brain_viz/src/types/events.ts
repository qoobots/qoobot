/**
 * src/types/events.ts — Custom application event types
 * Extends the WSEvent domain types with UI-side events.
 */

import type { Trajectory, SceneGraph, HITLPrompt, RobotState, Task, SafetyStatus } from './domain';

// ── UI Action Events ──────────────────────────────────────
export type UIActionType =
  | 'user_confirm_trajectory'
  | 'user_cancel'
  | 'user_emergency_stop'
  | 'user_override_mode'
  | 'user_send_instruction'
  | 'user_toggle_ghost_trails';

export interface UserAction {
  type: UIActionType;
  timestamp: string;
  payload?: Record<string, unknown>;
}

// ── Notification Events ──────────────────────────────────
export type NotificationLevel = 'info' | 'success' | 'warning' | 'error';

export interface AppNotification {
  id: string;
  level: NotificationLevel;
  message: string;
  detail?: string;
  timestamp: string;
  dismissed: boolean;
}

// ── Selection Events ─────────────────────────────────────
export interface SelectionEvent {
  objectId: string | null;
  trajectoryId: string | null;
  source: 'click' | 'hover' | 'keyboard';
}

// ── Keyboard Shortcuts ───────────────────────────────────
export interface KeyboardShortcut {
  key: string;
  ctrlKey: boolean;
  shiftKey: boolean;
  description: string;
  action: string;
}

export const DEFAULT_SHORTCUTS: KeyboardShortcut[] = [
  { key: 'c', ctrlKey: false, shiftKey: false, description: '聊天面板', action: 'panel:chat' },
  { key: 'h', ctrlKey: false, shiftKey: false, description: 'HITL面板', action: 'panel:hitl' },
  { key: 's', ctrlKey: false, shiftKey: false, description: '状态监控', action: 'panel:status' },
  { key: 'd', ctrlKey: false, shiftKey: false, description: '开发面板', action: 'panel:dev' },
  { key: 'g', ctrlKey: false, shiftKey: false, description: '切换GhostTrail', action: 'toggle:ghost' },
  { key: 'Escape', ctrlKey: false, shiftKey: false, description: '取消/返回', action: 'cancel' },
  { key: ' ', ctrlKey: false, shiftKey: false, description: '紧急制动', action: 'emergency_stop' },
];

// ── Panel Event Types ────────────────────────────────────
export interface PanelSwitchEvent {
  from: string;
  to: string;
  timestamp: string;
}

// ── WebSocket Connection State ───────────────────────────
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface ConnectionEvent {
  state: ConnectionState;
  timestamp: string;
  error?: string;
}

// ── Ghost Trail Animation State ──────────────────────────
export interface GhostTrailConfig {
  enabled: boolean;
  opacity: number;         // 0..1
  lineWidth: number;       // 1..5
  animationSpeed: number;  // 0..5
  selectedStrategy: string | null;
  maxTrails: number;       // 1..10
}

// ── Camera Presets ───────────────────────────────────────
export type CameraPreset = 'top-down' | 'side' | 'front' | 'perspective' | 'free';

export interface CameraConfig {
  preset: CameraPreset;
  target: [number, number, number];
  distance: number;
  azimuth: number;    // horizontal angle in radians
  polar: number;      // vertical angle in radians
}
