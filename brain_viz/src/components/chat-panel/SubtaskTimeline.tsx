/**
 * src/components/chat-panel/SubtaskTimeline.tsx — Subtask timeline visualization
 *
 * Displays a vertical timeline of subtasks with status indicators.
 */
'use client';

import React from 'react';
import type { Task, TaskStatus } from '@/types/domain';
import { Badge } from '@/components/common/Badge';

interface SubtaskTimelineProps {
  task: Task | null;
}

const STATUS_ORDER: TaskStatus[] = [
  'PENDING', 'PLANNING', 'AWAITING_HITL', 'EXECUTING', 'COMPLETED',
];

function getStatusIndex(status: TaskStatus): number {
  return STATUS_ORDER.indexOf(status);
}

function getStatusIcon(status: TaskStatus): string {
  switch (status) {
    case 'COMPLETED': return '✓';
    case 'FAILED': return '✕';
    case 'EXECUTING': return '⟳';
    case 'AWAITING_HITL': return '⏳';
    case 'CANCELLED': return '⊘';
    default: return '○';
  }
}

function getStatusColor(status: TaskStatus): string {
  switch (status) {
    case 'COMPLETED': return '#22c55e';
    case 'FAILED': return '#ef4444';
    case 'EXECUTING': return '#6366f1';
    case 'AWAITING_HITL': return '#f59e0b';
    case 'CANCELLED': return '#6b7280';
    default: return '#3b82f6';
  }
}

function SubtaskNode({ subtask, depth = 0 }: { subtask: Task; depth?: number }) {
  const isExecuting = subtask.status === 'EXECUTING';
  const isCompleted = subtask.status === 'COMPLETED';
  const isFailed = subtask.status === 'FAILED';

  return (
    <div className="flex gap-3" style={{ marginLeft: depth * 16 }}>
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div
          className={`
            w-5 h-5 rounded-full flex items-center justify-center text-[10px]
            ${isExecuting ? 'animate-spin' : ''}
          `.trim()}
          style={{
            backgroundColor: getStatusColor(subtask.status),
            color: '#0a0a1a',
          }}
        >
          {getStatusIcon(subtask.status)}
        </div>
        <div className="w-px flex-1 bg-brain-border" />
      </div>
      {/* Content */}
      <div className="pb-3 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm text-brain-text font-medium">
            {subtask.intent.action}
          </span>
          <Badge size="sm" taskStatus={subtask.status} />
        </div>
        <p className="text-xs text-brain-muted mt-0.5">
          {subtask.intent.target}
          {subtask.intent.source ? ` ← ${subtask.intent.source}` : ''}
        </p>
        {subtask.intent.constraints.length > 0 && (
          <div className="flex gap-1 mt-1">
            {subtask.intent.constraints.map((c, i) => (
              <span key={i} className="text-[10px] text-brain-muted bg-brain-surface px-1 py-0.5 rounded">
                {c}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function SubtaskTimeline({ task }: SubtaskTimelineProps) {
  if (!task) {
    return (
      <div className="flex items-center justify-center h-32 text-brain-muted text-sm">
        暂无任务分解数据
      </div>
    );
  }

  const allSubtasks = task.subtasks && task.subtasks.length > 0
    ? task.subtasks
    : [task];

  // Sort by status progression
  const sorted = [...allSubtasks].sort(
    (a, b) => getStatusIndex(b.status) - getStatusIndex(a.status)
  );

  return (
    <div className="px-3 py-2">
      <div className="text-xs text-brain-muted font-medium uppercase tracking-wide mb-2">
        任务分解 ({allSubtasks.length} 个子任务)
      </div>
      <div className="flex flex-col">
        {sorted.map((sub) => (
          <SubtaskNode key={sub.id} subtask={sub} />
        ))}
      </div>
    </div>
  );
}
