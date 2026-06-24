/**
 * src/components/hitl-panel/ScoreChart.tsx — Trajectory score comparison chart
 *
 * Bar chart showing multi-dimensional scores for each trajectory strategy,
 * allowing users to compare paths at a glance.
 */
'use client';

import React, { useMemo } from 'react';
import type { Trajectory } from '@/types/domain';
import { STRATEGY_COLORS, STRATEGY_LABELS } from '@/types/enums';

interface ScoreChartProps {
  trajectories: Trajectory[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  maxDisplay?: number;
}

interface ScoreDimension {
  key: string;
  label: string;
  value: number; // 0..1
}

// Simulated score breakdown (in production, this comes from the scorer service)
function getScoreBreakdown(trajectory: Trajectory): ScoreDimension[] {
  const { score, collision_free, duration_sec, waypoints } = trajectory;
  const durationScore = Math.max(0, 1 - duration_sec / 30); // normalize 0-30s
  const smoothness = Math.min(1, 1.0 - (waypoints.length > 2 ? 0.1 : 0));
  const manipulability = score * 0.9 + 0.1; // approximate

  return [
    { key: 'path', label: '路径', value: score },
    { key: 'collision', label: '碰撞安全', value: collision_free ? 1.0 : 0.3 },
    { key: 'duration', label: '耗时', value: durationScore },
    { key: 'smoothness', label: '平滑度', value: smoothness },
    { key: 'manip', label: '可操作度', value: manipulability },
    { key: 'overall', label: '综合', value: score },
  ];
}

export function ScoreChart({
  trajectories,
  selectedId,
  onSelect,
  maxDisplay = 5,
}: ScoreChartProps) {
  const displayTrajectories = useMemo(
    () => [...trajectories].sort((a, b) => b.score - a.score).slice(0, maxDisplay),
    [trajectories, maxDisplay]
  );

  if (trajectories.length === 0) {
    return (
      <div className="text-sm text-brain-muted text-center py-4">
        暂无轨迹数据
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {displayTrajectories.map((traj) => {
        const dimensions = getScoreBreakdown(trajectory);
        const color = STRATEGY_COLORS[traj.strategy] || '#6366f1';
        const isSelected = traj.id === selectedId;

        return (
          <button
            key={traj.id}
            onClick={() => onSelect?.(traj.id)}
            className={`
              w-full text-left rounded-lg p-2 transition-colors
              ${isSelected
                ? 'bg-indigo-500/10 border border-indigo-500/30'
                : 'bg-brain-surface hover:bg-brain-border/30 border border-transparent'
              }
            `.trim()}
          >
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-2">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs font-medium text-brain-text">
                  {STRATEGY_LABELS[traj.strategy]}
                </span>
              </div>
              <span className="text-xs font-mono" style={{ color }}>
                {(traj.score * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex gap-1">
              {dimensions.map((dim) => (
                <div key={dim.key} className="flex-1" title={`${dim.label}: ${(dim.value * 100).toFixed(0)}%`}>
                  <div className="h-1 rounded-full bg-brain-border">
                    <div
                      className="h-1 rounded-full transition-all duration-300"
                      style={{
                        width: `${dim.value * 100}%`,
                        backgroundColor: color,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
            <div className="flex justify-between mt-1">
              {dimensions.map((dim) => (
                <span key={dim.key} className="text-[9px] text-brain-muted">
                  {dim.label}
                </span>
              ))}
            </div>
          </button>
        );
      })}
      {trajectories.length > maxDisplay && (
        <p className="text-[10px] text-brain-muted text-center">
          显示前 {maxDisplay} 条，共 {trajectories.length} 条
        </p>
      )}
    </div>
  );
}
