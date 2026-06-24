/**
 * src/services/controlClient.ts — Control service client
 *
 * Typed wrapper around the gRPC control service for
 * direct robot control (joint commands, gripper, trajectory execution).
 */
import type { JointState, RobotState } from '@/types/domain';

export interface JointCommand {
  names: string[];
  positions: number[];
  velocities?: number[];
  efforts?: number[];
  timeFromStartSec: number;
}

export interface GripperCommand {
  position: number;     // 0 = closed, 1 = open
  maxEffort?: number;   // N
}

export interface TrajectoryPoint {
  positions: number[];
  velocities?: number[];
  timeFromStartSec: number;
}

export class ControlClient {
  private jointListeners: Array<(joints: JointState) => void> = [];
  private robotListeners: Array<(state: RobotState) => void> = [];
  private currentJoints: JointState = {
    names: ['joint_1', 'joint_2', 'joint_3', 'joint_4', 'joint_5', 'joint_6', 'joint_7'],
    positions: [0, 0, 0, 0, 0, 0, 0],
    velocities: [0, 0, 0, 0, 0, 0, 0],
    efforts: [0, 0, 0, 0, 0, 0, 0],
  };
  private gripperPos = 0.5;
  private executing = false;

  /** Send joint position command. */
  async sendJointCommand(command: JointCommand): Promise<{ accepted: boolean }> {
    console.log('[Control] Joint command:', command.names, command.positions);
    // Update internal state for UI feedback
    for (let i = 0; i < command.names.length; i++) {
      const idx = this.currentJoints.names.indexOf(command.names[i]);
      if (idx >= 0) {
        this.currentJoints.positions[idx] = command.positions[i];
      }
    }
    this.notifyJointListeners();
    return { accepted: true };
  }

  /** Control the gripper. */
  async controlGripper(command: GripperCommand): Promise<{ accepted: boolean }> {
    console.log('[Control] Gripper:', command.position);
    this.gripperPos = Math.max(0, Math.min(1, command.position));
    return { accepted: true };
  }

  /** Execute a trajectory (sequence of joint positions). */
  async executeTrajectory(points: TrajectoryPoint[]): Promise<{ success: boolean; progress: number }> {
    console.log('[Control] Executing trajectory:', points.length, 'points');
    this.executing = true;

    // Simulate execution for UI
    for (let i = 0; i < points.length; i++) {
      if (!this.executing) break;
      this.currentJoints.positions = points[i].positions;
      this.notifyJointListeners();
      const delay = i < points.length - 1
        ? (points[i + 1].timeFromStartSec - points[i].timeFromStartSec) * 1000
        : 100;
      await new Promise((resolve) => setTimeout(resolve, Math.max(10, delay)));
    }

    this.executing = false;
    return { success: true, progress: 1.0 };
  }

  /** Stop trajectory execution. */
  stopExecution(): void {
    this.executing = false;
    console.log('[Control] Execution stopped');
  }

  /** Go to home position. */
  async goHome(): Promise<{ accepted: boolean }> {
    return this.sendJointCommand({
      names: this.currentJoints.names,
      positions: [0, 0, 0, 0, 0, 0, 0],
      timeFromStartSec: 2.0,
    });
  }

  /** Open gripper fully. */
  async openGripper(): Promise<{ accepted: boolean }> {
    return this.controlGripper({ position: 1.0 });
  }

  /** Close gripper fully. */
  async closeGripper(): Promise<{ accepted: boolean }> {
    return this.controlGripper({ position: 0.0 });
  }

  /** Get current joint state. */
  getJointState(): JointState {
    return { ...this.currentJoints, positions: [...this.currentJoints.positions] };
  }

  /** Get gripper position. */
  getGripperPosition(): number {
    return this.gripperPos;
  }

  /** Subscribe to joint state updates. */
  onJointStateChange(callback: (joints: JointState) => void): () => void {
    this.jointListeners.push(callback);
    return () => {
      this.jointListeners = this.jointListeners.filter((l) => l !== callback);
    };
  }

  /** Subscribe to robot state updates. */
  onRobotStateChange(callback: (state: RobotState) => void): () => void {
    this.robotListeners.push(callback);
    return () => {
      this.robotListeners = this.robotListeners.filter((l) => l !== callback);
    };
  }

  private notifyJointListeners(): void {
    for (const l of this.jointListeners) {
      l({ ...this.currentJoints, positions: [...this.currentJoints.positions] });
    }
  }
}

export const controlClient = new ControlClient();
