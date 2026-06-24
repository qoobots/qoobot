/**
 * src/types/enums.ts — Display helpers and enum mappings
 */
import type { SafetyLevel, TrajectoryStrategy } from './domain';

export const SAFETY_COLORS: Record<SafetyLevel, string> = {
  NORMAL:    '#22c55e',
  WARNING:   '#eab308',
  CRITICAL:  '#ef4444',
  EMERGENCY: '#dc2626',
};

export const SAFETY_LABELS: Record<SafetyLevel, string> = {
  NORMAL:    '正常',
  WARNING:   '警告',
  CRITICAL:  '严重',
  EMERGENCY: '紧急制动',
};

export const STRATEGY_COLORS: Record<TrajectoryStrategy, string> = {
  OPTIMAL:      '#f59e0b',
  CONSERVATIVE: '#22c55e',
  AGGRESSIVE:   '#ef4444',
  EXPLORATORY:  '#3b82f6',
  REVERSE:      '#8b5cf6',
};

export const STRATEGY_LABELS: Record<TrajectoryStrategy, string> = {
  OPTIMAL:      '最优',
  CONSERVATIVE: '保守',
  AGGRESSIVE:   '激进',
  EXPLORATORY:  '探索',
  REVERSE:      '逆向',
};
