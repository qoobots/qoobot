/**
 * src/stores/robotStore.ts — Robot state store (Zustand)
 */
import { create } from 'zustand';
import type { RobotState, SafetyLevel } from '@/types/domain';

interface RobotStore {
  state: RobotState | null;
  connected: boolean;
  updateState: (state: RobotState) => void;
  setSafetyLevel: (level: SafetyLevel) => void;
  setEmergencyStop: (active: boolean) => void;
  setConnected: (connected: boolean) => void;
}

export const useRobotStore = create<RobotStore>((set) => ({
  state: null,
  connected: false,

  updateState: (state) => set({ state }),
  setSafetyLevel: (level) =>
    set((s) => ({
      state: s.state ? { ...s.state, safety_level: level } : null,
    })),
  setEmergencyStop: (active) =>
    set((s) => ({
      state: s.state ? { ...s.state, emergency_stop: active } : null,
    })),
  setConnected: (connected) => set({ connected }),
}));
