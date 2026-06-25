/**
 * src/components/status-monitor/ProcessMonitor.tsx — Process status monitor
 */
'use client';

import React from 'react';
import { useMonitorStore, type ProcessInfo } from '@/stores/monitorStore';
import { formatDuration, formatBytes } from '@/utils/formatTime';
import { Badge } from '@/components/common/Badge';

const PROCESS_STATUS_COLORS: Record<ProcessInfo['status'], string> = {
  running: '#22c55e',
  stopped: '#6b7280',
  error: '#ef4444',
};

const PROCESS_STATUS_LABELS: Record<ProcessInfo['status'], string> = {
  running: '运行中',
  stopped: '已停止',
  error: '异常',
};

function ProcessRow({ process }: { process: ProcessInfo }) {
  const color = PROCESS_STATUS_COLORS[process.status];

  return (
    <div className="flex items-center gap-2 px-2 py-1.5 bg-brain-surface rounded text-xs">
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <span className="text-brain-text font-medium truncate">{process.name}</span>
          <span className="text-[10px]" style={{ color }}>
            {PROCESS_STATUS_LABELS[process.status]}
          </span>
        </div>
        <div className="flex gap-3 mt-0.5 text-[10px] text-brain-muted">
          <span>PID {process.pid}</span>
          <span>↑ {formatDuration(process.uptimeSec)}</span>
          <span>CPU {process.cpuPercent.toFixed(1)}%</span>
          <span>{formatBytes(process.memoryMB * 1024 * 1024)}</span>
          {process.restartCount > 0 && (
            <span className="text-yellow-400">重启 {process.restartCount}</span>
          )}
        </div>
      </div>
    </div>
  );
}

export function ProcessMonitor() {
  const processes = useMonitorStore((s) => s.processes);

  if (processes.length === 0) {
    return (
      <div className="panel-card">
        <h3 className="text-sm font-semibold text-brain-text mb-2">进程监控</h3>
        <div className="text-xs text-brain-muted text-center py-4">
          等待进程信息...
        </div>
      </div>
    );
  }

  const running = processes.filter((p) => p.status === 'running').length;
  const errors = processes.filter((p) => p.status === 'error').length;

  return (
    <div className="panel-card">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-brain-text">进程监控</h3>
        <div className="flex gap-2 text-[10px]">
          <span className="text-green-400">{running} 运行</span>
          {errors > 0 && <span className="text-red-400">{errors} 异常</span>}
        </div>
      </div>
      <div className="flex flex-col gap-1">
        {processes.map((proc) => (
          <ProcessRow key={proc.name} process={proc} />
        ))}
      </div>
    </div>
  );
}
