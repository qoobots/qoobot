/**
 * src/components/status-monitor/HealthCard.tsx — System health status card
 */
'use client';

import React from 'react';
import type { SystemHealth } from '@/stores/monitorStore';
import { useMonitorStore } from '@/stores/monitorStore';
import { formatElapsed } from '@/utils/formatTime';

export function HealthCard() {
  const health = useMonitorStore((s) => s.health);

  const statusColor = health.overall === 'healthy' ? '#22c55e'
    : health.overall === 'degraded' ? '#eab308' : '#ef4444';

  const statusLabel = health.overall === 'healthy' ? '健康'
    : health.overall === 'degraded' ? '降级' : '异常';

  return (
    <div className="panel-card">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-brain-text">系统健康</h3>
        <span
          className="px-2 py-0.5 rounded-full text-[10px] font-medium"
          style={{ backgroundColor: `${statusColor}20`, color: statusColor }}
        >
          {statusLabel}
        </span>
      </div>

      {/* Component status grid */}
      <div className="grid grid-cols-2 gap-1.5">
        {Object.entries(health.components).length === 0 ? (
          <div className="col-span-2 text-xs text-brain-muted text-center py-4">
            等待组件状态上报...
          </div>
        ) : (
          Object.entries(health.components).map(([name, status]) => {
            const color = status === 'ok' ? '#22c55e'
              : status === 'warning' ? '#eab308'
              : status === 'error' ? '#ef4444'
              : '#6b7280';

            const label = status === 'ok' ? '正常'
              : status === 'warning' ? '警告'
              : status === 'error' ? '异常' : '未知';

            return (
              <div key={name} className="flex items-center gap-2 px-2 py-1.5 bg-brain-surface rounded">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-xs text-brain-text flex-1">{name}</span>
                <span className="text-[10px]" style={{ color }}>{label}</span>
              </div>
            );
          })
        )}
      </div>

      <div className="mt-2 text-[10px] text-brain-muted text-right">
        上次检查：{health.lastCheck ? formatElapsed(health.lastCheck) : '--'}
      </div>
    </div>
  );
}
