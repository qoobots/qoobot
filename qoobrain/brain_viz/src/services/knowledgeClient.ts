/**
 * src/services/knowledgeClient.ts — Knowledge service client
 *
 * Typed wrapper around the gRPC knowledge service for
 * episodic memory and skill registry access.
 */
import { grpcClient } from './grpcClient';

export interface Skill {
  name: string;
  description: string;
  parameters?: string[];
}

export interface MemoryEntry {
  id: string;
  content: string;
  score: number;
  timestamp?: string;
}

export interface EpisodeRecord {
  taskId: string;
  instruction: string;
  btXml: string;
  outcome: string;
  durationMs: number;
  success: boolean;
}

export class KnowledgeClient {
  /** Semantic search in episodic memory. */
  async search(query: string, topK = 5): Promise<MemoryEntry[]> {
    return grpcClient.queryMemory(query, topK);
  }

  /** Store a completed task episode. */
  async storeEpisode(episode: EpisodeRecord): Promise<string> {
    const result = await grpcClient.storeEpisode(episode);
    return result.id;
  }

  /** List all registered skills. */
  async listSkills(): Promise<Skill[]> {
    const skills = await grpcClient.listSkills();
    return skills.map((s) => ({ ...s, parameters: [] }));
  }

  /** Register a new skill. */
  async registerSkill(
    name: string,
    description: string
  ): Promise<boolean> {
    const result = await grpcClient.registerSkill(name, description);
    return result.success;
  }

  /** Quick semantic search with a simplified interface. */
  async findSimilar(
    instruction: string,
    minScore = 0.5
  ): Promise<MemoryEntry[]> {
    const results = await this.search(instruction, 10);
    return results.filter((r) => r.score >= minScore);
  }
}

export const knowledgeClient = new KnowledgeClient();
