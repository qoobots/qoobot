/**
 * src/components/common/Badge.tsx — Status badge component
 */
'use client';

import React from 'react';
import type { SafetyLevel, TrajectoryStrategy, TaskStatus } from '@/types/domain';
import { SAFETY_COLORS, SAFETY_LABELS, STRATEGY_COLORS, STRATEGY_LABELS } from '@/types/enums';

type BadgeVariant = 'default' | 'outline' | 'dot';
type BadgeSize = 'sm' | 'md';

interface BadgeProps {
  children?: React.ReactNode;
  variant?: BadgeVariant;
  size?: BadgeSize;
  color?: string;
  className?: string;
  // Convenience props for common domain types
  safetyLevel?: SafetyLevel;
  strategy?: TrajectoryStrategy;
  taskStatus?: TaskStatus;
}

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  PENDING: '待处理',
  PLANNING: '规划中',
  AWAITING_HITL: '等待确认',
  EXECUTING: '执行中',
  COMPLETED: '已完成',
  FAILED: '失败',
  CANCELLED: '已取消',
};

const TASK_STATUS_COLORS: Record<TaskStatus, string> = {
  PENDING: '#6b7280',
  PLANNING: '#3b82f6',
  AWAITING_HITL: '#f59e0b',
  EXECUTING: '#6366f1',
  COMPLETED: '#22c55e',
  FAILED: '#ef4444',
  CANCELLED: '#6b7280',
};

const variantClasses: Record<BadgeVariant, string> = {
  default: '',
  outline: 'bg-transparent border',
  dot: '',
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2 py-0.5 text-xs',
};

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  color,
  className = '',
  safetyLevel,
  strategy,
  taskStatus,
}: BadgeProps) {
  // Determine display content and color from convenience props
  let displayText = children;
  let badgeColor = color;

  if (safetyLevel) {
    displayText = SAFETY_LABELS[safetyLevel];
    badgeColor = SAFETY_COLORS[safetyLevel];
  } else if (strategy) {
    displayText = STRATEGY_LABELS[strategy];
    badgeColor = STRATEGY_COLORS[strategy];
  } else if (taskStatus) {
    displayText = TASK_STATUS_LABELS[taskStatus];
    badgeColor = TASK_STATUS_COLORS[taskStatus];
  }

  const borderColor = variant === 'outline' ? badgeColor : 'transparent';
  const bgColor = variant === 'default' ? badgeColor : 'transparent';

  return (
    <span
      className={`
        inline-flex items-center gap-1 rounded-full font-medium
        ${sizeClasses[size]}
        ${variantClasses[variant]}
        ${className}
      `.trim()}
      style={{
        backgroundColor: bgColor ? `${bgColor}20` : undefined,
        borderColor: borderColor || undefined,
        color: badgeColor || undefined,
      }}
    >
      {variant === 'dot' && (
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: badgeColor }}
        />
      )}
      {displayText}
    </span>
  );
}
