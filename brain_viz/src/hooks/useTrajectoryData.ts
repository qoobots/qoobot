/**
 * src/hooks/useTrajectoryData.ts — Trajectory data subscription hook
 *
 * Provides reactive access to trajectory data with
 * sorting, filtering, and selection utilities.
 */
'use client';

import { useMemo, useCallback } from 'react';
import { useTrajectoryStore } from '@/stores/trajectoryStore';
import type { Trajectory, TrajectoryStrategy } from '@/types/domain';

interface UseTrajectoryDataReturn {
  trajectories: Trajectory[];
  selectedTrajectory: Trajectory | null;
  selectedId: string | null;
  showGhostTrails: boolean;
  trajectoryCount: number;
  hasTrajectories: boolean;
  sortedByScore: Trajectory[];
  collisionFreeTrajectories: Trajectory[];
  collisionTrajectories: Trajectory[];
  strategiesAvailable: TrajectoryStrategy[];
  bestTrajectory: Trajectory | null;
  selectTrajectory: (id: string | null) => void;
  toggleGhostTrails: () => void;
  getTrajectoryById: (id: string) => Trajectory | undefined;
  getTrajectoriesByStrategy: (strategy: TrajectoryStrategy) => Trajectory[];
  getWaypointCount: (trajectoryId: string) => number;
}

export function useTrajectoryData(): UseTrajectoryDataReturn {
  const trajectories = useTrajectoryStore((s) => s.trajectories);
  const selectedId = useTrajectoryStore((s) => s.selectedId);
  const showGhostTrails = useTrajectoryStore((s) => s.showGhostTrails);
  const selectTrajectory = useTrajectoryStore((s) => s.selectTrajectory);
  const toggleGhostTrails = useTrajectoryStore((s) => s.toggleGhostTrails);

  const selectedTrajectory = useMemo(
    () => trajectories.find((t) => t.id === selectedId) ?? null,
    [trajectories, selectedId]
  );

  const trajectoryCount = trajectories.length;
  const hasTrajectories = trajectoryCount > 0;

  const sortedByScore = useMemo(
    () => [...trajectories].sort((a, b) => b.score - a.score),
    [trajectories]
  );

  const collisionFreeTrajectories = useMemo(
    () => trajectories.filter((t) => t.collision_free),
    [trajectories]
  );

  const collisionTrajectories = useMemo(
    () => trajectories.filter((t) => !t.collision_free),
    [trajectories]
  );

  const strategiesAvailable = useMemo(
    () => [...new Set(trajectories.map((t) => t.strategy))],
    [trajectories]
  );

  const bestTrajectory = useMemo(
    () => (sortedByScore.length > 0 ? sortedByScore[0] : null),
    [sortedByScore]
  );

  const getTrajectoryById = useCallback(
    (id: string): Trajectory | undefined => trajectories.find((t) => t.id === id),
    [trajectories]
  );

  const getTrajectoriesByStrategy = useCallback(
    (strategy: TrajectoryStrategy): Trajectory[] =>
      trajectories.filter((t) => t.strategy === strategy),
    [trajectories]
  );

  const getWaypointCount = useCallback(
    (trajectoryId: string): number => {
      const t = trajectories.find((t2) => t2.id === trajectoryId);
      return t?.waypoints.length ?? 0;
    },
    [trajectories]
  );

  return {
    trajectories,
    selectedTrajectory,
    selectedId,
    showGhostTrails,
    trajectoryCount,
    hasTrajectories,
    sortedByScore,
    collisionFreeTrajectories,
    collisionTrajectories,
    strategiesAvailable,
    bestTrajectory,
    selectTrajectory,
    toggleGhostTrails,
    getTrajectoryById,
    getTrajectoriesByStrategy,
    getWaypointCount,
  };
}
