/**
 * src/components/hitl-panel/OverridePanel.tsx — Trajectory override/editing panel
 *
 * Allows users to manually adjust waypoints of a selected trajectory
 * before confirming execution.
 */
'use client';

import React, { useState, useCallback } from 'react';
import type { Waypoint, Trajectory } from '@/types/domain';
import { Button } from '@/components/common/Button';
import { Slider } from '@/components/common/Slider';

interface OverridePanelProps {
  trajectory: Trajectory | null;
  onApply: (modified: Trajectory) => void;
  onCancel: () => void;
}

export function OverridePanel({ trajectory, onApply, onCancel }: OverridePanelProps) {
  const [speedMultiplier, setSpeedMultiplier] = useState(1.0);
  const [heightOffset, setHeightOffset] = useState(0);

  const handleApply = useCallback(() => {
    if (!trajectory) return;

    const modifiedWaypoints: Waypoint[] = trajectory.waypoints.map((wp) => ({
      ...wp,
      y: wp.y + heightOffset,
      time_from_start_sec: wp.time_from_start_sec / speedMultiplier,
    }));

    onApply({
      ...trajectory,
      waypoints: modifiedWaypoints,
      duration_sec: trajectory.duration_sec / speedMultiplier,
    });
  }, [trajectory, speedMultiplier, heightOffset, onApply]);

  if (!trajectory) {
    return (
      <div className="panel-card text-sm text-brain-muted text-center">
        请先选择一条轨迹进行编辑
      </div>
    );
  }

  return (
    <div className="panel-card space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-brain-text">轨迹编辑</h3>
        <span className="text-xs text-brain-muted font-mono">{trajectory.id}</span>
      </div>

      <Slider
        label="速度倍率"
        value={speedMultiplier}
        onChange={setSpeedMultiplier}
        min={0.1}
        max={2.0}
        step={0.1}
        formatValue={(v) => `${v.toFixed(1)}x`}
      />

      <Slider
        label="高度偏移 (m)"
        value={heightOffset}
        onChange={setHeightOffset}
        min={-0.1}
        max={0.1}
        step={0.01}
        formatValue={(v) => `${(v * 100).toFixed(0)}cm`}
      />

      <div className="flex gap-2 pt-2">
        <Button size="sm" onClick={handleApply} fullWidth>
          应用修改
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          取消
        </Button>
      </div>
    </div>
  );
}
