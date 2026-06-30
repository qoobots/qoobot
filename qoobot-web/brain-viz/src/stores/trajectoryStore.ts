/**
 * src/stores/trajectoryStore.ts — Trajectory store (Zustand)
 */
import { create } from 'zustand';
import type { Trajectory } from '@/types/domain';

interface TrajectoryStore {
  trajectories: Trajectory[];
  selectedId: string | null;
  showGhostTrails: boolean;
  setTrajectories: (trajs: Trajectory[]) => void;
  selectTrajectory: (id: string | null) => void;
  toggleGhostTrails: () => void;
}

export const useTrajectoryStore = create<TrajectoryStore>((set) => ({
  trajectories: [],
  selectedId: null,
  showGhostTrails: true,

  setTrajectories: (trajs) => set({ trajectories: trajs }),
  selectTrajectory: (id) => set({ selectedId: id }),
  toggleGhostTrails: () => set((s) => ({ showGhostTrails: !s.showGhostTrails })),
}));
