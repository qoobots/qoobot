/**
 * src/components/common/Slider.tsx — Range slider component
 */
'use client';

import React, { useCallback, useRef } from 'react';

interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  label?: string;
  showValue?: boolean;
  formatValue?: (value: number) => string;
  disabled?: boolean;
  className?: string;
}

export function Slider({
  value,
  onChange,
  min = 0,
  max = 100,
  step = 1,
  label,
  showValue = true,
  formatValue,
  disabled = false,
  className = '',
}: SliderProps) {
  const trackRef = useRef<HTMLDivElement>(null);

  const percentage = ((value - min) / (max - min)) * 100;

  const handleTrackClick = useCallback(
    (e: React.MouseEvent) => {
      if (disabled || !trackRef.current) return;
      const rect = trackRef.current.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      const newValue = min + pct * (max - min);
      onChange(Math.round(newValue / step) * step);
    },
    [min, max, step, disabled, onChange]
  );

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      {(label || showValue) && (
        <div className="flex justify-between items-center">
          {label && <span className="text-xs text-brain-muted">{label}</span>}
          {showValue && (
            <span className="text-xs font-mono text-brain-text">
              {formatValue ? formatValue(value) : value}
            </span>
          )}
        </div>
      )}
      <div
        ref={trackRef}
        className={`
          relative h-2 rounded-full cursor-pointer
          ${disabled ? 'opacity-40 cursor-not-allowed' : ''}
          bg-brain-border
        `}
        onClick={handleTrackClick}
      >
        <div
          className="absolute h-full rounded-full bg-indigo-500 transition-all duration-100"
          style={{ width: `${percentage}%` }}
        />
        <div
          className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 w-4 h-4
            rounded-full bg-white border-2 border-indigo-500 shadow-md
            transition-all duration-100"
          style={{ left: `${percentage}%` }}
        />
      </div>
    </div>
  );
}
