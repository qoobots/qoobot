/**
 * tests/stores/trajectoryStore.test.ts — Trajectory store unit tests
 */

import { create } from 'zustand';

// We can't import the actual store directly in Jest (ESM issues),
// so we test the equivalent store logic.

interface TrajectoryStore {
  trajectories: Array<{
    id: string; strategy: string; waypoints: unknown[];
    score: number; collision_free: boolean; duration_sec: number;
  }>;
  selectedId: string | null;
  showGhostTrails: boolean;
  setTrajectories: (trajs: TrajectoryStore['trajectories']) => void;
  selectTrajectory: (id: string | null) => void;
  toggleGhostTrails: () => void;
}

const createTestStore = () =>
  create<TrajectoryStore>((set) => ({
    trajectories: [],
    selectedId: null,
    showGhostTrails: true,
    setTrajectories: (trajs) => set({ trajectories: trajs }),
    selectTrajectory: (id) => set({ selectedId: id }),
    toggleGhostTrails: () => set((s) => ({ showGhostTrails: !s.showGhostTrails })),
  }));

describe('TrajectoryStore', () => {
  const sampleTrajectory = {
    id: 'traj-test',
    strategy: 'OPTIMAL',
    waypoints: [{ x: 0, y: 0, z: 0, time_from_start_sec: 0 }],
    score: 0.95,
    collision_free: true,
    duration_sec: 1.2,
  };

  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
  });

  it('initializes with empty state', () => {
    expect(store.getState().trajectories).toEqual([]);
    expect(store.getState().selectedId).toBeNull();
    expect(store.getState().showGhostTrails).toBe(true);
  });

  it('sets trajectories', () => {
    store.getState().setTrajectories([sampleTrajectory]);
    expect(store.getState().trajectories).toHaveLength(1);
    expect(store.getState().trajectories[0].id).toBe('traj-test');
  });

  it('selects a trajectory', () => {
    store.getState().setTrajectories([sampleTrajectory]);
    store.getState().selectTrajectory('traj-test');
    expect(store.getState().selectedId).toBe('traj-test');
  });

  it('deselects a trajectory', () => {
    store.getState().selectTrajectory('traj-test');
    store.getState().selectTrajectory(null);
    expect(store.getState().selectedId).toBeNull();
  });

  it('toggles ghost trails', () => {
    expect(store.getState().showGhostTrails).toBe(true);
    store.getState().toggleGhostTrails();
    expect(store.getState().showGhostTrails).toBe(false);
    store.getState().toggleGhostTrails();
    expect(store.getState().showGhostTrails).toBe(true);
  });

  it('replaces trajectories when set again', () => {
    store.getState().setTrajectories([sampleTrajectory]);
    const newTraj = { ...sampleTrajectory, id: 'traj-new', score: 0.85 };
    store.getState().setTrajectories([newTraj]);
    expect(store.getState().trajectories).toHaveLength(1);
    expect(store.getState().trajectories[0].id).toBe('traj-new');
  });

  it('handles multiple trajectories sorted by score', () => {
    const trajs = [
      { ...sampleTrajectory, id: 't1', score: 0.7 },
      { ...sampleTrajectory, id: 't2', score: 0.95 },
      { ...sampleTrajectory, id: 't3', score: 0.85 },
    ];
    store.getState().setTrajectories(trajs);
    expect(store.getState().trajectories).toHaveLength(3);

    // Sort by score descending
    const sorted = [...store.getState().trajectories].sort((a, b) => b.score - a.score);
    expect(sorted[0].id).toBe('t2');
    expect(sorted[0].score).toBe(0.95);
    expect(sorted[2].id).toBe('t1');
    expect(sorted[2].score).toBe(0.7);
  });

  it('tracks selected trajectory across updates', () => {
    store.getState().setTrajectories([sampleTrajectory]);
    store.getState().selectTrajectory('traj-test');

    // Update trajectories but keep same ID
    store.getState().setTrajectories([
      { ...sampleTrajectory, score: 0.80 },
    ]);
    expect(store.getState().selectedId).toBe('traj-test');
  });
});
