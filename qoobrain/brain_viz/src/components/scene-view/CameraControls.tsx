/**
 * src/components/scene-view/CameraControls.tsx — Camera control UI overlay
 */
'use client';

import React, { useCallback } from 'react';
import type { CameraPreset } from '@/types/events';

interface CameraControlsProps {
  onPresetChange: (preset: CameraPreset) => void;
  currentPreset: CameraPreset;
}

const PRESETS: { id: CameraPreset; label: string; icon: string }[] = [
  { id: 'free', label: '自由', icon: '↕' },
  { id: 'perspective', label: '透视', icon: '◎' },
  { id: 'top-down', label: '俯视', icon: '⊙' },
  { id: 'front', label: '正视', icon: '□' },
  { id: 'side', label: '侧视', icon: '◫' },
];

export function CameraControls({ onPresetChange, currentPreset }: CameraControlsProps) {
  const handlePreset = useCallback(
    (preset: CameraPreset) => onPresetChange(preset),
    [onPresetChange]
  );

  return (
    <div className="absolute top-4 right-4 z-10 flex gap-1">
      <div className="flex rounded-lg bg-brain-bg/80 backdrop-blur-sm border border-brain-border overflow-hidden">
        {PRESETS.map((p) => (
          <button
            key={p.id}
            onClick={() => handlePreset(p.id)}
            className={`
              px-2 py-1.5 text-xs font-medium transition-colors
              ${currentPreset === p.id
                ? 'bg-indigo-600 text-white'
                : 'text-brain-muted hover:text-brain-text hover:bg-brain-surface'
              }
            `.trim()}
            title={p.label}
          >
            {p.icon}
          </button>
        ))}
      </div>
    </div>
  );
}
