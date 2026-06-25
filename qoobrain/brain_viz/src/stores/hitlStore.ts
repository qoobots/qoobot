/**
 * src/stores/hitlStore.ts — HITL (Human-in-the-Loop) store (Zustand)
 */
import { create } from 'zustand';
import type { HITLPrompt, Trajectory } from '@/types/domain';

interface HITLStore {
  prompt: HITLPrompt | null;
  countdown: number;
  mode: 'autonomous' | 'suggested' | 'manual';
  awaitingSelection: boolean;
  setPrompt: (prompt: HITLPrompt) => void;
  setCountdown: (seconds: number) => void;
  setMode: (mode: 'autonomous' | 'suggested' | 'manual') => void;
  selectTrajectory: (traj: Trajectory) => void;
  clearPrompt: () => void;
}

export const useHITLStore = create<HITLStore>((set) => ({
  prompt: null,
  countdown: 0,
  mode: 'suggested',
  awaitingSelection: false,

  setPrompt: (prompt) => set({ prompt, awaitingSelection: true, countdown: prompt.timeout_sec }),
  setCountdown: (countdown) => set({ countdown }),
  setMode: (mode) => set({ mode }),
  selectTrajectory: (_traj) => set({ awaitingSelection: false, prompt: null }),
  clearPrompt: () => set({ prompt: null, awaitingSelection: false }),
}));
