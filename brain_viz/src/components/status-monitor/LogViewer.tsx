/**
 * src/components/status-monitor/LogViewer.tsx — Real-time log viewer component
 */
'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useMonitorStore, type LogEntry } from '@/stores/monitorStore';
import { formatTimestamp } from '@/utils/formatTime';

type LogLevelFilter = 'ALL' | LogEntry['level'];

const LEVEL_COLORS: Record<LogEntry['level'], string> = {
  DEBUG: '#6b7280',
  INFO: '#e8e8f0',
  WARN: '#eab308',
  ERROR: '#ef4444',
  FATAL: '#dc2626',
};

function LogRow({ entry }: { entry: LogEntry }) {
  const color = LEVEL_COLORS[entry.level] || '#6b7280';

  return (
    <div className="flex gap-2 py-0.5 px-2 hover:bg-brain-surface/50 rounded text-xs font-mono">
      <span className="text-brain-muted flex-shrink-0 w-16">
        {formatTimestamp(entry.timestamp)}
      </span>
      <span className="flex-shrink-0 w-12 text-right" style={{ color }}>
        {entry.level.padEnd(5)}
      </span>
      <span className="text-brain-muted flex-shrink-0 w-20 truncate">
        [{entry.source}]
      </span>
      <span className="text-brain-text flex-1 truncate">
        {entry.message}
      </span>
    </div>
  );
}

export function LogViewer() {
  const logs = useMonitorStore((s) => s.logs);
  const isRecording = useMonitorStore((s) => s.isRecording);
  const [filter, setFilter] = useState<LogLevelFilter>('ALL');
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  const filteredLogs = filter === 'ALL' ? logs : logs.filter((l) => l.level === filter);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [filteredLogs.length, autoScroll]);

  return (
    <div className="panel-card flex flex-col h-64">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-brain-text">日志</h3>
        <div className="flex items-center gap-1">
          {(['ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG'] as LogLevelFilter[]).map((level) => (
            <button
              key={level}
              onClick={() => setFilter(level)}
              className={`
                px-1.5 py-0.5 rounded text-[10px] transition-colors
                ${filter === level ? 'bg-indigo-500/20 text-indigo-400' : 'text-brain-muted hover:text-brain-text'}
              `.trim()}
            >
              {level}
            </button>
          ))}
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-1.5 py-0.5 rounded text-[10px] ${autoScroll ? 'text-green-400' : 'text-brain-muted'}`}
            title={autoScroll ? '自动滚动开启' : '自动滚动关闭'}
          >
            ↓
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto bg-brain-bg/50 rounded border border-brain-border">
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-brain-muted">
            {isRecording ? '等待日志...' : '暂无日志数据'}
          </div>
        ) : (
          filteredLogs.map((entry) => (
            <LogRow key={entry.id} entry={entry} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      <div className="flex justify-between items-center mt-1.5">
        <span className="text-[10px] text-brain-muted">
          {filteredLogs.length} 条记录
        </span>
      </div>
    </div>
  );
}
