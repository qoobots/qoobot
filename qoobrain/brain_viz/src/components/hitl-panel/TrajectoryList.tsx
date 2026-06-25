/**
 * src/components/hitl-panel/TrajectoryList.tsx — Trajectory list container
 *
 * Scrollable list of trajectory cards with filtering and sorting,
 * providing an overview of all generated paths.
 */
'use client';

import React, { useMemo, useCallback } from 'react';
import type { Trajectory, TrajectoryStrategy } from '@/types/domain';
import { TrajectoryCard } from './TrajectoryCard';

interface TrajectoryListProps {
  trajectories: Trajectory[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  maxItems?: number;
  showStrategyFilter?: boolean;
  showCollisionFilter?: boolean;
}

const STRATEGIES: TrajectoryStrategy[] = [
  'OPTIMAL', 'CONSERVATIVE', 'AGGRESSIVE', 'EXPLORATORY', 'REVERSE',
];

export function TrajectoryList({
  trajectories,
  selectedId,
  onSelect,
  maxItems = 10,
  showStrategyFilter = true,
  showCollisionFilter = false,
}: TrajectoryListProps) {
  const [strategyFilter, setStrategyFilter] = React.useState<TrajectoryStrategy | 'all'>('all');
  const [collisionOnly, setCollisionOnly] = React.useState(false);

  const filtered = useMemo(() => {
    let result = trajectories;

    if (strategyFilter !== 'all') {
      result = result.filter((t) => t.strategy === strategyFilter);
    }

    if (collisionOnly) {
      result = result.filter((t) => t.collision_free);
    }

    return [...result].sort((a, b) => b.score - a.score);
  }, [trajectories, strategyFilter, collisionOnly]);

  const handleClearFilters = useCallback(() => {
    setStrategyFilter('all');
    setCollisionOnly(false);
  }, []);

  if (trajectories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-brain-muted text-sm gap-2">
        <svg className="w-8 h-8 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l5.447 2.724A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        <span>暂无轨迹数据</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {/* Filters */}
      {(showStrategyFilter || showCollisionFilter) && (
        <div className="flex items-center gap-1.5 px-1">
          {showStrategyFilter && (
            <div className="flex gap-0.5 flex-1 overflow-x-auto pb-1">
              <button
                onClick={() => setStrategyFilter('all')}
                className={`
                  px-1.5 py-0.5 rounded text-[10px] transition-colors whitespace-nowrap
                  ${strategyFilter === 'all'
                    ? 'bg-indigo-500/20 text-indigo-400'
                    : 'text-brain-muted hover:text-brain-text'
                  }
                `.trim()}
              >
                全部
              </button>
              {STRATEGIES.map((s) => (
                <button
                  key={s}
                  onClick={() => setStrategyFilter(s)}
                  className={`
                    px-1.5 py-0.5 rounded text-[10px] transition-colors whitespace-nowrap
                    ${strategyFilter === s
                      ? 'bg-indigo-500/20 text-indigo-400'
                      : 'text-brain-muted hover:text-brain-text'
                    }
                  `.trim()}
                >
                  {s === 'OPTIMAL' ? '最优' : s === 'CONSERVATIVE' ? '保守' : s === 'AGGRESSIVE' ? '激进' : s === 'EXPLORATORY' ? '探索' : '逆向'}
                </button>
              ))}
            </div>
          )}
          <span className="text-[10px] text-brain-muted">
            {filtered.length}/{trajectories.length}
          </span>
        </div>
      )}

      {/* List */}
      <div className="flex flex-col gap-1.5 max-h-[500px] overflow-y-auto">
        {filtered.slice(0, maxItems).map((traj) => (
          <TrajectoryCard
            key={traj.id}
            trajectory={traj}
            selected={traj.id === selectedId}
            onClick={() => onSelect(traj.id)}
          />
        ))}
      </div>

      {filtered.length > maxItems && (
        <p className="text-[10px] text-brain-muted text-center">
          显示 {maxItems}/{filtered.length} 条，请使用筛选器缩小范围
        </p>
      )}
    </div>
  );
}
