/**
 * src/components/chat-panel/IntentView.tsx — Intent visualization component
 *
 * Displays parsed NLU intent as a structured card with action, target,
 * source, constraints, and confidence.
 */
'use client';

import React from 'react';
import type { Intent } from '@/types/domain';
import { Badge } from '@/components/common/Badge';
import { ProgressBar } from '@/components/common/ProgressBar';

interface IntentViewProps {
  intent: Intent | null;
}

export function IntentView({ intent }: IntentViewProps) {
  if (!intent) return null;

  return (
    <div className="panel-card mx-3 my-2 space-y-2 text-xs">
      <div className="flex items-center justify-between">
        <span className="text-brain-muted font-medium uppercase tracking-wide">
          意图解析
        </span>
        <span className="text-brain-text font-mono">
          {(intent.confidence * 100).toFixed(0)}% 置信度
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-brain-muted">动作</span>
          <p className="text-brain-text font-medium">{intent.action}</p>
        </div>
        <div>
          <span className="text-brain-muted">目标</span>
          <p className="text-brain-text font-medium">{intent.target}</p>
        </div>
        {intent.source && (
          <div>
            <span className="text-brain-muted">来源</span>
            <p className="text-brain-text">{intent.source}</p>
          </div>
        )}
      </div>

      {intent.constraints.length > 0 && (
        <div>
          <span className="text-brain-muted">约束条件</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {intent.constraints.map((c, i) => (
              <Badge key={i} size="sm" variant="dot">
                {c}
              </Badge>
            ))}
          </div>
        </div>
      )}

      <ProgressBar
        value={intent.confidence * 100}
        max={100}
        size="sm"
        color={intent.confidence > 0.8 ? '#22c55e' : intent.confidence > 0.5 ? '#eab308' : '#ef4444'}
      />
    </div>
  );
}
