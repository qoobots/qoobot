/**
 * src/components/common/ProgressBar.tsx — Animated progress bar component
 */
'use client';

import React from 'react';

interface ProgressBarProps {
  value: number;      // 0..100 or 0..1 if fractional
  max?: number;       // defaults to 100
  label?: string;
  showValue?: boolean;
  formatValue?: (value: number) => string;
  size?: 'sm' | 'md' | 'lg';
  color?: string;
  animated?: boolean;
  striped?: boolean;
  className?: string;
}

const sizeHeights = { sm: 'h-1', md: 'h-2', lg: 'h-4' };

export function ProgressBar({
  value,
  max = 100,
  label,
  showValue = false,
  formatValue,
  size = 'md',
  color = '#6366f1',
  animated = true,
  striped = false,
  className = '',
}: ProgressBarProps) {
  const percentage = Math.max(0, Math.min(100, (value / max) * 100));

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {(label || showValue) && (
        <div className="flex justify-between items-center">
          {label && <span className="text-xs text-brain-muted">{label}</span>}
          {showValue && (
            <span className="text-xs font-mono text-brain-text">
              {formatValue ? formatValue(value, max) : `${percentage.toFixed(0)}%`}
            </span>
          )}
        </div>
      )}
      <div className={`w-full ${sizeHeights[size]} bg-brain-border rounded-full overflow-hidden`}>
        <div
          className={`
            ${sizeHeights[size]} rounded-full
            ${animated ? 'transition-all duration-300 ease-out' : ''}
            ${striped ? 'bg-stripes' : ''}
          `.trim()}
          style={{
            width: `${percentage}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}
