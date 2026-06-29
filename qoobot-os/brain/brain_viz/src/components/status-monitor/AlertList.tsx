/**
 * src/components/status-monitor/AlertList.tsx — Safety alert list component
 */
'use client';

import React from 'react';
import { useMonitorStore } from '@/stores/monitorStore';
import { useSafetyAlerts } from '@/hooks/useSafetyAlerts';
import { formatTimestamp } from '@/utils/formatTime';
import { Button } from '@/components/common/Button';

export function AlertList() {
  const { activeAlerts, criticalAlerts, acknowledgeAlert, dismissAll } = useSafetyAlerts();

  if (activeAlerts.length === 0) {
    return (
      <div className="panel-card">
        <h3 className="text-sm font-semibold text-brain-text mb-2">安全告警</h3>
        <div className="flex flex-col items-center justify-center py-4 text-brain-muted text-xs gap-1">
          <svg className="w-5 h-5 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>无活跃告警</span>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-brain-text">
          安全告警 ({activeAlerts.length})
          {criticalAlerts.length > 0 && (
            <span className="ml-1 text-red-400">({criticalAlerts.length} 严重)</span>
          )}
        </h3>
        <Button size="sm" variant="ghost" onClick={dismissAll}>
          全部清除
        </Button>
      </div>

      <div className="flex flex-col gap-1.5 max-h-64 overflow-y-auto">
        {activeAlerts.map((alert) => (
          <div
            key={alert.id}
            className={`
              flex items-start gap-2 p-2 rounded text-xs
              ${alert.level === 'error'
                ? 'bg-red-500/10 border border-red-500/20'
                : alert.level === 'warning'
                  ? 'bg-yellow-500/10 border border-yellow-500/20'
                  : 'bg-blue-500/10 border border-blue-500/20'
              }
            `.trim()}
          >
            <span
              className={`
                mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-[10px]
                ${alert.level === 'error' ? 'bg-red-500 text-white'
                  : alert.level === 'warning' ? 'bg-yellow-500 text-black'
                  : 'bg-blue-500 text-white'
                }
              `.trim()}
            >
              {alert.level === 'error' ? '!' : alert.level === 'warning' ? '⚠' : 'i'}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-brain-text">{alert.message}</p>
              {alert.detail && <p className="text-brain-muted mt-0.5">{alert.detail}</p>}
              <span className="text-[10px] text-brain-muted">
                {formatTimestamp(alert.timestamp)}
              </span>
            </div>
            <button
              onClick={() => acknowledgeAlert(alert.id)}
              className="text-brain-muted hover:text-brain-text flex-shrink-0 p-0.5"
              title="确认"
            >
              ✓
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
