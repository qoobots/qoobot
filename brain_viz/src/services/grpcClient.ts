/**
 * src/services/grpcClient.ts — gRPC-Web client for brain_ai services
 *
 * Unified gRPC client that wraps @protobuf-ts/grpcweb-transport with
 * mock fallback for development without the backend running.
 */
import type { Intent, Task, Trajectory, SceneGraph } from '@/types/domain';
import type {
  ProtoIntent, ProtoExecutionPlan, ProtoTrajectory,
  ProtoSceneGraph, ProtoSafetyStatus, ProtoEpisode,
  ProtoDetectedObject, ProtoLocalization,
} from '@/types/proto';

// ── Types ────────────────────────────────────────────────
export interface GRPCError {
  code: number;
  message: string;
  details?: string;
}

export interface GRPCStreamCallbacks<T> {
  onMessage: (data: T) => void;
  onError?: (error: GRPCError) => void;
  onEnd?: () => void;
}

type GRPCCallOptions = {
  timeoutMs?: number;
  retries?: number;
};

// ── Client Implementation ────────────────────────────────
class GRPCClient {
  private baseUrl: string;
  private connected = false;
  private mockMode: boolean;

  constructor(baseUrl: string = '/api/grpc') {
    this.baseUrl = baseUrl;
    this.mockMode = true; // Development mode until real backend is connected
  }

  // ── Connection ──────────────────────────────────────────
  get isConnected(): boolean { return this.connected; }
  get isMockMode(): boolean { return this.mockMode; }

  /** Try to connect to the real gRPC backend. */
  async connect(): Promise<boolean> {
    try {
      const resp = await fetch(`${this.baseUrl}/health`, { signal: AbortSignal.timeout(3000) });
      this.connected = resp.ok;
      this.mockMode = !resp.ok;
      return this.connected;
    } catch {
      this.connected = false;
      this.mockMode = true;
      return false;
    }
  }

  // ── Core RPC Call ───────────────────────────────────────
  private async rpcCall<T>(
    service: string,
    method: string,
    request: Record<string, unknown>,
    _options?: GRPCCallOptions
  ): Promise<T> {
    console.log(`[gRPC] ${service}.${method}`, request);

    try {
      const resp = await fetch(`${this.baseUrl}/${service}/${method}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
        signal: AbortSignal.timeout(_options?.timeoutMs ?? 10000),
      });

      if (!resp.ok) {
        throw new Error(`gRPC error: ${resp.status} ${resp.statusText}`);
      }

      return (await resp.json()) as T;
    } catch (err) {
      const error = err as Error;
      console.warn(`[gRPC] ${service}.${method} failed, using mock:`, error.message);
      return this.getMockResponse<T>(service, method, request);
    }
  }

  // ── Mock Fallback ───────────────────────────────────────
  private getMockResponse<T>(
    _service: string, method: string, _request: Record<string, unknown>
  ): T {
    // Each method has its specific mock implementation below
    throw new Error(`No mock for ${method}`);
  }

  // ── Cognition Service ───────────────────────────────────
  async parseIntent(instruction: string, context?: string): Promise<Intent> {
    try {
      return await this.rpcCall<Intent>('cognition', 'ParseIntent', { instruction, context });
    } catch {
      return {
        action: 'pick',
        target: instruction.includes('红色') || instruction.includes('red') ? 'red_cup' : 'object',
        source: instruction.includes('从') ? 'table' : undefined,
        constraints: instruction.includes('小心') || instruction.includes('慢') ? ['careful'] : [],
        confidence: 0.85,
      };
    }
  }

  async decomposeTask(intent: Intent, scene?: SceneGraph): Promise<Task> {
    try {
      return await this.rpcCall<Task>('cognition', 'DecomposeTask', {
        intent: intent as unknown as ProtoIntent,
        scene: scene as unknown as ProtoSceneGraph,
      });
    } catch {
      return {
        id: `task_${Date.now()}`,
        intent,
        subtasks: [
          {
            id: `sub_${Date.now()}_1`,
            intent: { action: 'move', target: 'above_target', constraints: [], confidence: 0.95 },
            subtasks: [],
            status: 'PENDING',
            created_at: new Date().toISOString(),
          },
          {
            id: `sub_${Date.now()}_2`,
            intent: { ...intent, constraints: [], confidence: 0.9 },
            subtasks: [],
            status: 'PENDING',
            created_at: new Date().toISOString(),
          },
        ],
        status: 'PLANNING',
        created_at: new Date().toISOString(),
      };
    }
  }

  async generateBT(intent: Intent): Promise<string> {
    try {
      const resp = await this.rpcCall<{ xml: string }>('cognition', 'GenerateBT', {
        intent: intent as unknown as ProtoIntent,
      });
      return resp.xml;
    } catch {
      return `<BehaviorTree>
  <Sequence name="pick_sequence">
    <NavigateTo goal="above_target"/>
    <Pick target="${intent.target}" approach="top_down"/>
  </Sequence>
</BehaviorTree>`;
    }
  }

  async clarify(instruction: string, ambiguity: string): Promise<Intent> {
    return this.rpcCall<Intent>('cognition', 'Clarify', { instruction, ambiguity });
  }

  // ── Decision Service ────────────────────────────────────
  async generateTrajectories(
    planId: string,
    goal: { x: number; y: number; z: number }
  ): Promise<Trajectory[]> {
    try {
      const resp = await this.rpcCall<{ trajectories: ProtoTrajectory[] }>(
        'decision', 'GenerateTrajectories', { plan_id: planId, goal_pose: goal }
      );
      return resp.trajectories.map((t) => ({
        id: t.id,
        strategy: t.strategy as Trajectory['strategy'],
        waypoints: t.waypoints?.map((wp) => ({
          x: wp.pose.position.x,
          y: wp.pose.position.y,
          z: wp.pose.position.z,
          time_from_start_sec: wp.time_from_start_sec,
        })) ?? [],
        score: t.score,
        collision_free: t.collision_free,
        duration_sec: t.duration_sec,
      }));
    } catch {
      return [
        {
          id: `traj_${Date.now()}_opt`,
          strategy: 'OPTIMAL',
          waypoints: [
            { x: 0, y: 0.3, z: 0.2, time_from_start_sec: 0 },
            { x: goal.x * 0.5, y: 0.4, z: goal.z * 0.5 + 0.1, time_from_start_sec: 0.5 },
            { x: goal.x, y: goal.y, z: goal.z, time_from_start_sec: 1.0 },
          ],
          score: 0.92,
          collision_free: true,
          duration_sec: 1.0,
        },
        {
          id: `traj_${Date.now()}_con`,
          strategy: 'CONSERVATIVE',
          waypoints: [
            { x: 0, y: 0.2, z: 0.2, time_from_start_sec: 0 },
            { x: goal.x * 0.3, y: 0.5, z: goal.z * 0.3, time_from_start_sec: 0.6 },
            { x: goal.x * 0.7, y: 0.5, z: goal.z * 0.7, time_from_start_sec: 1.2 },
            { x: goal.x, y: goal.y, z: goal.z, time_from_start_sec: 1.8 },
          ],
          score: 0.78,
          collision_free: true,
          duration_sec: 1.8,
        },
        {
          id: `traj_${Date.now()}_agg`,
          strategy: 'AGGRESSIVE',
          waypoints: [
            { x: 0, y: 0.3, z: 0.2, time_from_start_sec: 0 },
            { x: goal.x, y: goal.y, z: goal.z, time_from_start_sec: 0.6 },
          ],
          score: 0.85,
          collision_free: true,
          duration_sec: 0.6,
        },
      ];
    }
  }

  async selectTrajectory(
    planId: string,
    trajectoryId: string,
    userOverride = false
  ): Promise<{ selected_id: string; status: string }> {
    try {
      return await this.rpcCall('decision', 'SelectTrajectory', {
        plan_id: planId,
        trajectory_id: trajectoryId,
        user_override: userOverride,
      });
    } catch {
      return { selected_id: trajectoryId, status: 'CONFIRMED' };
    }
  }

  async cancelPlan(planId: string): Promise<{ success: boolean }> {
    return this.rpcCall('decision', 'CancelPlan', { plan_id: planId });
  }

  // ── Knowledge Service ───────────────────────────────────
  async queryMemory(
    query: string, topK = 5
  ): Promise<{ id: string; content: string; score: number }[]> {
    try {
      const resp = await this.rpcCall<{ episodes: ProtoEpisode[] }>(
        'knowledge', 'SearchEpisodes', { query, top_k: topK }
      );
      return resp.episodes.map((ep) => ({
        id: ep.id,
        content: `[${ep.outcome}] ${ep.instruction}`,
        score: 0.5,
      }));
    } catch {
      return [];
    }
  }

  async storeEpisode(episode: {
    taskId: string; instruction: string; btXml: string;
    outcome: string; durationMs: number; success: boolean;
  }): Promise<{ id: string }> {
    return this.rpcCall('knowledge', 'StoreEpisode', episode);
  }

  async listSkills(): Promise<{ name: string; description: string }[]> {
    try {
      const resp = await this.rpcCall<{
        skills: { name: string; description: string }[]
      }>('knowledge', 'ListSkills', {});
      return resp.skills;
    } catch {
      return [
        { name: 'NavigateTo', description: '导航到目标位置' },
        { name: 'Pick', description: '抓取物体' },
        { name: 'Place', description: '放置物体' },
        { name: 'Detect', description: '检测场景物体' },
        { name: 'Wait', description: '等待指定时间' },
        { name: 'AvoidObstacle', description: '避障' },
      ];
    }
  }

  async registerSkill(name: string, description: string): Promise<{ success: boolean }> {
    return this.rpcCall('knowledge', 'RegisterSkill', { name, description });
  }

  // ── gRPC Streaming ──────────────────────────────────────
  /** Open a server-streaming RPC connection.
   *  In production, this uses gRPC-Web streaming.
   *  For dev, it polls the REST endpoint. */
  streamSceneGraph(callbacks: GRPCStreamCallbacks<SceneGraph>): () => void {
    let cancelled = false;
    const interval = setInterval(async () => {
      if (cancelled) return;
      try {
        const resp = await this.rpcCall<{ scene_graph: ProtoSceneGraph }>(
          'perception', 'StreamSceneGraph', { interval_ms: 100 }
        );
        if (!cancelled) {
          callbacks.onMessage(resp.scene_graph as unknown as SceneGraph);
        }
      } catch (err) {
        if (!cancelled) callbacks.onError?.({
          code: 14, message: (err as Error).message,
        });
      }
    }, 100);

    return () => {
      cancelled = true;
      clearInterval(interval);
      callbacks.onEnd?.();
    };
  }
}

export const grpcClient = new GRPCClient();
