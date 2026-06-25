/**
 * src/components/dev-panel/DevPanel.tsx — Developer tools panel
 *
 * Provides debugging and testing interfaces for the Brain OS
 * during development.
 */
'use client';

import React, { useState } from 'react';
import { APITester } from './APITester';
import { SkillRegistry } from './SkillRegistry';
import { NodeInspector } from './NodeInspector';
import { useMonitorStore } from '@/stores/monitorStore';

type DevTab = 'api' | 'skills' | 'btree' | 'logs';

export function DevPanel() {
  const [tab, setTab] = useState<DevTab>('api');
  const isRecording = useMonitorStore((s) => s.isRecording);
  const setRecording = useMonitorStore((s) => s.setRecording);

  const tabs: { id: DevTab; label: string }[] = [
    { id: 'api', label: 'API测试' },
    { id: 'skills', label: '技能表' },
    { id: 'btree', label: '行为树' },
    { id: 'logs', label: '日志' },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-brain-border">
        <h2 className="text-sm font-semibold text-brain-text">开发面板</h2>
        <button
          onClick={() => setRecording(!isRecording)}
          className={`
            px-2 py-1 rounded text-[10px] font-medium transition-colors
            ${isRecording
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : 'bg-brain-surface text-brain-muted border border-brain-border'
            }
          `.trim()}
        >
          {isRecording ? '⏺ 记录中' : '⏹ 录制'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-brain-border">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`
              flex-1 px-3 py-2 text-xs font-medium transition-colors border-b-2
              ${tab === t.id
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-brain-muted hover:text-brain-text'
              }
            `.trim()}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {tab === 'api' && <APITester />}
        {tab === 'skills' && <SkillRegistry />}
        {tab === 'btree' && <NodeInspector />}
        {tab === 'logs' && <LogTab />}
      </div>
    </div>
  );
}

function LogTab() {
  const logs = useMonitorStore((s) => s.logs);
  const recentLogs = logs.slice(-20).reverse();

  return (
    <div className="space-y-1">
      <h3 className="text-xs text-brain-muted mb-2">最近 20 条日志</h3>
      {recentLogs.length === 0 ? (
        <p className="text-xs text-brain-muted">暂无日志</p>
      ) : (
        recentLogs.map((log) => (
          <div key={log.id} className="text-[10px] font-mono text-brain-text bg-brain-surface p-1.5 rounded">
            <span className="text-brain-muted">{log.timestamp.slice(11, 19)} </span>
            <span className={log.level === 'ERROR' ? 'text-red-400' : log.level === 'WARN' ? 'text-yellow-400' : ''}>
              [{log.level}]
            </span>{' '}
            {log.message}
          </div>
        ))
      )}
    </div>
  );
}
