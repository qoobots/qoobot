/**
 * src/services/decisionClient.ts — Decision service client
 *
 * Typed wrapper around the gRPC decision service for trajectory
 * generation, selection, and plan execution.
 */
import { grpcClient } from './grpcClient';
import type { Trajectory } from '@/types/domain';

export interface PlanRequest {
  taskId: string;
  goal: { x: number; y: number; z: number };
}

export interface ExecutionPlan {
  planId: string;
  taskId: string;
  trajectories: Trajectory[];
  selectedTrajectoryId: string | null;
  status: 'GENERATED' | 'SELECTED' | 'EXECUTING' | 'COMPLETED' | 'CANCELLED';
}

export class DecisionClient {
  private planCounter = 0;

  /** Generate multiple trajectory options for a goal pose. */
  async generateTrajectories(request: PlanRequest): Promise<Trajectory[]> {
    const planId = `plan_${Date.now()}_${++this.planCounter}`;
    return grpcClient.generateTrajectories(planId, request.goal);
  }

  /** Select a trajectory for execution. */
  async selectTrajectory(
    planId: string,
    trajectoryId: string,
    userOverride = false
  ): Promise<{ selected_id: string; status: string }> {
    return grpcClient.selectTrajectory(planId, trajectoryId, userOverride);
  }

  /** Cancel an active plan. */
  async cancelPlan(planId: string): Promise<boolean> {
    const result = await grpcClient.cancelPlan(planId);
    return result.success;
  }

  /** Full planning pipeline: request → generate → auto-select best. */
  async planAutoSelect(request: PlanRequest): Promise<ExecutionPlan> {
    const planId = `plan_${Date.now()}_${++this.planCounter}`;
    const trajectories = await grpcClient.generateTrajectories(planId, request.goal);

    // Auto-select the highest-scored collision-free trajectory
    const best = trajectories
      .filter((t) => t.collision_free)
      .sort((a, b) => b.score - a.score)[0];

    let selectedId: string | null = null;
    if (best) {
      await grpcClient.selectTrajectory(planId, best.id, false);
      selectedId = best.id;
    }

    return {
      planId,
      taskId: request.taskId,
      trajectories,
      selectedTrajectoryId: selectedId,
      status: selectedId ? 'SELECTED' : 'GENERATED',
    };
  }
}

export const decisionClient = new DecisionClient();
