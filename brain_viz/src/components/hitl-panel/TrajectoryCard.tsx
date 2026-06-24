/**
 * src/components/hitl-panel/TrajectoryCard.tsx — Single trajectory selection card
 */
'use client';

import { Clock, Shield, Zap } from 'lucide-react';
import type { Trajectory } from '@/types/domain';
import { STRATEGY_COLORS, STRATEGY_LABELS } from '@/types/enums';

interface TrajectoryCardProps {
  trajectory: Trajectory;
  selected: boolean;
  onSelect: () => void;
}

export function TrajectoryCard({ trajectory, selected, onSelect }: TrajectoryCardProps) {
  const color = STRATEGY_COLORS[trajectory.strategy];
  const label = STRATEGY_LABELS[trajectory.strategy];

  return (
    <button
      onClick={onSelect}
      className={`w-full text-left p-3 rounded-lg border transition-all duration-200
        ${selected
          ? 'border-brain-accent bg-brain-accent/10'
          : 'border-brain-border hover:border-brain-border/80 hover:bg-brain-panel/80'
        }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: color }}
          />
          <span className="text-xs font-mono font-bold text-brain-text">
            {label}
          </span>
        </div>
        <span className="text-xs text-brain-muted font-mono">
          {trajectory.id}
        </span>
      </div>

      <div className="flex items-center gap-3 text-xs text-brain-muted">
        {/* Score */}
        <span className="flex items-center gap-1">
          <Zap size={12} className="text-brain-gold" />
          {(trajectory.score * 100).toFixed(0)}%
        </span>

        {/* Duration */}
        <span className="flex items-center gap-1">
          <Clock size={12} />
          {trajectory.duration_sec.toFixed(1)}s
        </span>

        {/* Collision */}
        <span className="flex items-center gap-1">
          <Shield size={12} className={trajectory.collision_free ? 'text-brain-safe' : 'text-brain-danger'} />
          {trajectory.collision_free ? '安全' : '碰撞'}
        </span>
      </div>
    </button>
  );
}
