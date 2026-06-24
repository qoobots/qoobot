/**
 * src/components/hitl-panel/StrategyBadge.tsx — Enhanced strategy badge with tooltip
 *
 * Displays strategy name with icon, description, and
 * visual indicator of characteristics.
 */
'use client';

import React from 'react';
import type { TrajectoryStrategy } from '@/types/domain';
import { STRATEGY_COLORS, STRATEGY_LABELS } from '@/types/enums';

interface StrategyBadgeProps {
  strategy: TrajectoryStrategy;
  size?: 'sm' | 'md';
  showDescription?: boolean;
  className?: string;
}

const STRATEGY_DESCRIPTIONS: Record<TrajectoryStrategy, string> = {
  OPTIMAL: '综合评分最优，平衡路径长度、碰撞安全和执行效率',
  CONSERVATIVE: '优先安全，避开所有潜在碰撞区域，路径可能较长',
  AGGRESSIVE: '最短路径优先，容忍低概率碰撞风险，执行最快',
  EXPLORATORY: '尝试非直线路径探索，可能发现更优解',
  REVERSE: '从目标逆向规划，适用于复杂环境起点搜索',
};

const STRATEGY_ICONS: Record<TrajectoryStrategy, string> = {
  OPTIMAL: '★',
  CONSERVATIVE: '🛡',
  AGGRESSIVE: '⚡',
  EXPLORATORY: '🔍',
  REVERSE: '↩',
};

export function StrategyBadge({
  strategy,
  size = 'md',
  showDescription = false,
  className = '',
}: StrategyBadgeProps) {
  const color = STRATEGY_COLORS[strategy];
  const label = STRATEGY_LABELS[strategy];
  const icon = STRATEGY_ICONS[strategy];
  const description = STRATEGY_DESCRIPTIONS[strategy];

  const sizeClasses = {
    sm: 'px-1.5 py-0.5 text-[10px]',
    md: 'px-2 py-1 text-xs',
  };

  return (
    <div className={`inline-flex items-start gap-1.5 ${className}`}>
      <span
        className={`
          inline-flex items-center gap-1 rounded-full font-medium
          ${sizeClasses[size]}
        `.trim()}
        style={{
          backgroundColor: `${color}20`,
          color,
          borderColor: color,
          borderWidth: '1px',
          borderStyle: 'solid',
        }}
      >
        <span>{icon}</span>
        <span>{label}</span>
      </span>
      {showDescription && (
        <p className="text-[11px] text-brain-muted leading-relaxed max-w-xs">
          {description}
        </p>
      )}
    </div>
  );
}
