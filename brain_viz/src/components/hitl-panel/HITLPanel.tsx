/**
 * src/components/hitl-panel/HITLPanel.tsx — Human-in-the-Loop trajectory selection panel
 */
'use client';

import { useHITLStore } from '@/stores/hitlStore';
import { useTrajectoryStore } from '@/stores/trajectoryStore';
import { Countdown } from './Countdown';
import { TrajectoryCard } from './TrajectoryCard';
import { ModeControl } from './ModeControl';
import type { Trajectory } from '@/types/domain';

export function HITLPanel() {
  const prompt = useHITLStore((s) => s.prompt);
  const awaitingSelection = useHITLStore((s) => s.awaitingSelection);
  const mode = useHITLStore((s) => s.mode);
  const setPrompt = useHITLStore((s) => s.setPrompt);
  const selectTrajectory = useHITLStore((s) => s.selectTrajectory);
  const trajectories = useTrajectoryStore((s) => s.trajectories);
  const setTrajectories = useTrajectoryStore((s) => s.setTrajectories);
  const selectedId = useTrajectoryStore((s) => s.selectedId);
  const setSelected = useTrajectoryStore((s) => s.selectTrajectory);

  const handleSelect = (traj: Trajectory) => {
    setSelected(traj.id);
    selectTrajectory(traj);
  };

  // Demo trajectories for Sprint 1
  const displayTrajectories = trajectories.length > 0 ? trajectories : [
    {
      id: 'demo-optimal', strategy: 'OPTIMAL' as const,
      waypoints: [], score: 0.95, collision_free: true, duration_sec: 2.0,
    },
    {
      id: 'demo-conservative', strategy: 'CONSERVATIVE' as const,
      waypoints: [], score: 0.72, collision_free: true, duration_sec: 2.5,
    },
  ];

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-mono font-bold text-brain-text">
          人机协同 · HITL
        </h2>
        <ModeControl />
      </div>

      {/* Countdown */}
      {awaitingSelection && prompt && (
        <Countdown
          seconds={prompt.timeout_sec}
          onTimeout={() => {
            // Auto-select optimal trajectory
            const best = displayTrajectories.sort((a, b) => b.score - a.score)[0];
            handleSelect(best);
          }}
        />
      )}

      {/* Trajectory list */}
      <div className="space-y-2">
        {displayTrajectories.map((traj) => (
          <TrajectoryCard
            key={traj.id}
            trajectory={traj}
            selected={selectedId === traj.id}
            onSelect={() => handleSelect(traj)}
          />
        ))}
      </div>

      {/* Demo trigger */}
      {!awaitingSelection && (
        <button
          className="btn-primary w-full text-sm"
          onClick={() => {
            setPrompt({
              trajectories: displayTrajectories,
              timeout_sec: 5.0,
            });
            setTrajectories(displayTrajectories);
          }}
        >
          模拟轨迹选择
        </button>
      )}
    </div>
  );
}
