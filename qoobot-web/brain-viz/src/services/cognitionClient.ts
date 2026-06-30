/**
 * src/services/cognitionClient.ts — Cognition service client
 *
 * Typed wrapper around the gRPC cognition service for intent parsing,
 * task decomposition, and behavior tree generation.
 */
import { grpcClient } from './grpcClient';
import type { Intent, Task, SceneGraph } from '@/types/domain';

export class CognitionClient {
  /** Parse a natural language instruction into structured intent. */
  async parseIntent(
    instruction: string,
    context?: string
  ): Promise<{ intent: Intent; alternatives: Intent[] }> {
    const intent = await grpcClient.parseIntent(instruction, context);
    // In production, the server returns a list of alternatives
    return { intent, alternatives: [] };
  }

  /** Decompose a parsed intent into subtasks. */
  async decomposeTask(
    intent: Intent,
    scene?: SceneGraph
  ): Promise<Task> {
    return grpcClient.decomposeTask(intent, scene);
  }

  /** Generate a behavior tree XML from intent. */
  async generateBT(intent: Intent): Promise<string> {
    return grpcClient.generateBT(intent);
  }

  /** Request clarification when intent is ambiguous. */
  async clarify(
    instruction: string,
    ambiguity: string
  ): Promise<Intent> {
    return grpcClient.clarify(instruction, ambiguity);
  }

  /** Full parsing pipeline: instruction → intent → task → BT. */
  async processInstruction(
    instruction: string,
    scene?: SceneGraph
  ): Promise<{ intent: Intent; task: Task; btXml: string }> {
    const intent = await this.parseIntent(instruction);
    const task = await this.decomposeTask(intent.intent, scene);
    const btXml = await this.generateBT(intent.intent);
    return { intent: intent.intent, task, btXml };
  }
}

export const cognitionClient = new CognitionClient();
