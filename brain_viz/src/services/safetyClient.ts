/**
 * src/services/safetyClient.ts — Safety service client
 *
 * Typed wrapper around the gRPC safety service for
 * safety status, emergency stop, and alerts.
 */
import type { SafetyStatus, SafetyLevel } from '@/types/domain';

export interface SafetyServiceState {
  level: SafetyLevel;
  emergencyStop: boolean;
  collisionRisk: number;
  forceExceeded: boolean;
  jointLimitsExceeded: boolean;
  activeAlerts: string[];
  timestamp: string;
}

export class SafetyClient {
  private listeners: Array<(state: SafetyServiceState) => void> = [];
  private currentState: SafetyServiceState = {
    level: 'NORMAL',
    emergencyStop: false,
    collisionRisk: 0,
    forceExceeded: false,
    jointLimitsExceeded: false,
    activeAlerts: [],
    timestamp: new Date().toISOString(),
  };

  /** Get current safety status. */
  getStatus(): SafetyServiceState {
    return { ...this.currentState };
  }

  /** Subscribe to safety status changes. */
  onChange(callback: (state: SafetyServiceState) => void): () => void {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== callback);
    };
  }

  /** Request emergency stop. */
  emergencyStop(): void {
    this.currentState = {
      ...this.currentState,
      level: 'EMERGENCY',
      emergencyStop: true,
      activeAlerts: ['用户触发紧急制动'],
      timestamp: new Date().toISOString(),
    };
    this.notify();
    console.log('[Safety] Emergency stop activated');
  }

  /** Release emergency stop. */
  releaseEmergencyStop(): void {
    this.currentState = {
      ...this.currentState,
      level: 'NORMAL',
      emergencyStop: false,
      activeAlerts: [],
      timestamp: new Date().toISOString(),
    };
    this.notify();
    console.log('[Safety] Emergency stop released');
  }

  /** Acknowledge a safety alert. */
  acknowledgeAlert(alertMessage: string): void {
    this.currentState = {
      ...this.currentState,
      activeAlerts: this.currentState.activeAlerts.filter((a) => a !== alertMessage),
      timestamp: new Date().toISOString(),
    };
    this.notify();
  }

  /** Update from WebSocket event. */
  updateFromEvent(data: Partial<SafetyServiceState>): void {
    this.currentState = {
      ...this.currentState,
      ...data,
      timestamp: new Date().toISOString(),
    };
    this.notify();
  }

  private notify(): void {
    for (const listener of this.listeners) {
      listener({ ...this.currentState });
    }
  }
}

export const safetyClient = new SafetyClient();
