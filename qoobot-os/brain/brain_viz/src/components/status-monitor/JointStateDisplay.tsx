/**
 * src/components/status-monitor/JointStateDisplay.tsx — Joint state visualization
 */
'use client';

import React, { useMemo } from 'react';
import { useRobotState } from '@/hooks/useRobotState';

export function JointStateDisplay() {
  const { joints, jointNames, jointPositionsDeg } = useRobotState();

  const jointData = useMemo(() => {
    if (!joints) return [];
    return joints.names.map((name, i) => ({
      name,
      position: joints.positions[i] ?? 0,
      positionDeg: (joints.positions[i] ?? 0) * 180 / Math.PI,
      velocity: joints.velocities[i] ?? 0,
      effort: joints.efforts[i] ?? 0,
    }));
  }, [joints]);

  if (!joints || jointData.length === 0) {
    return (
      <div className="panel-card">
        <h3 className="text-sm font-semibold text-brain-text mb-2">关节状态</h3>
        <div className="text-xs text-brain-muted text-center py-4">
          等待机器人连接...
        </div>
      </div>
    );
  }

  return (
    <div className="panel-card">
      <h3 className="text-sm font-semibold text-brain-text mb-2">关节状态</h3>
      <div className="flex flex-col gap-1.5">
        {jointData.map((joint) => {
          const absDeg = Math.abs(joint.positionDeg);
          const nearLimit = absDeg > 160; // approximate extreme
          const barColor = nearLimit ? '#ef4444' : '#6366f1';
          const normalized = (joint.positionDeg + 180) / 360; // map to 0..1

          return (
            <div key={joint.name} className="flex items-center gap-2 text-xs">
              <span className="w-16 text-brain-muted truncate" title={joint.name}>
                {joint.name}
              </span>
              <div className="flex-1 h-1.5 bg-brain-border rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-100"
                  style={{
                    width: `${normalized * 100}%`,
                    backgroundColor: barColor,
                  }}
                />
              </div>
              <span
                className="w-16 text-right font-mono"
                style={{ color: barColor }}
              >
                {joint.positionDeg.toFixed(1)}°
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
