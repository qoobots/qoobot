/**
 * src/services/perceptionClient.ts — Perception service client
 *
 * Typed wrapper around the gRPC perception service for
 * scene graph, object detection, and localization.
 */
import { grpcClient, type GRPCStreamCallbacks } from './grpcClient';
import type { SceneGraph, Object3D } from '@/types/domain';

export interface LocalizationData {
  pose: {
    position: { x: number; y: number; z: number };
    orientation: { x: number; y: number; z: number; w: number };
  };
  covariance: number[];
  mapId: string;
  timestamp: string;
}

export interface ObjectQuery {
  label?: string;
  minConfidence?: number;
  maxResults?: number;
}

export class PerceptionClient {
  /** Get the full scene graph from perception. */
  async getSceneGraph(): Promise<SceneGraph> {
    // The actual RPC would be on the perception service;
    // for now, the gRPC client stub maps to decision service
    return {
      timestamp: new Date().toISOString(),
      objects: [
        {
          id: 'obj_001', label: 'red_cup',
          centroid: [0.3, 0.05, 0.2], confidence: 0.92,
        },
        {
          id: 'obj_002', label: 'blue_bottle',
          centroid: [-0.2, 0.1, 0.15], confidence: 0.88,
        },
        {
          id: 'obj_003', label: 'yellow_box',
          centroid: [0.1, 0.02, -0.15], confidence: 0.95,
        },
        {
          id: 'obj_004', label: 'table',
          centroid: [0, -0.4, 0.3], confidence: 0.99,
        },
      ],
      robot_pose: [0, 0.3, 0, 0, 0, 0, 1],
    };
  }

  /** Get current robot localization. */
  async getLocalization(): Promise<LocalizationData> {
    return {
      pose: {
        position: { x: 0, y: 0.3, z: 0 },
        orientation: { x: 0, y: 0, z: 0, w: 1 },
      },
      covariance: Array(36).fill(0),
      mapId: 'tabletop_map',
      timestamp: new Date().toISOString(),
    };
  }

  /** Query detected objects by criteria. */
  async queryObjects(query: ObjectQuery): Promise<Object3D[]> {
    const scene = await this.getSceneGraph();
    let results = scene.objects;

    if (query.label) {
      const lower = query.label.toLowerCase();
      results = results.filter((o) => o.label.toLowerCase().includes(lower));
    }

    if (query.minConfidence !== undefined) {
      results = results.filter((o) => o.confidence >= query.minConfidence);
    }

    if (query.maxResults !== undefined) {
      results = results.slice(0, query.maxResults);
    }

    return results;
  }

  /** Get the object closest to the gripper (mock: first object). */
  async getNearestObject(): Promise<Object3D | null> {
    const scene = await this.getSceneGraph();
    return scene.objects[0] ?? null;
  }

  /** Check if a specific object is detected in the scene. */
  async isObjectVisible(label: string): Promise<boolean> {
    const objects = await this.queryObjects({ label, minConfidence: 0.5 });
    return objects.length > 0;
  }

  /** Subscribe to real-time scene graph updates (streaming). */
  subscribeSceneGraph(
    callbacks: GRPCStreamCallbacks<SceneGraph>
  ): () => void {
    return grpcClient.streamSceneGraph(callbacks);
  }
}

export const perceptionClient = new PerceptionClient();
