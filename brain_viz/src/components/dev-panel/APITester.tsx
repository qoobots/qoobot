/**
 * src/components/dev-panel/APITester.tsx — gRPC/Ws API testing tool
 */
'use client';

import React, { useState, useCallback } from 'react';
import { grpcClient } from '@/services/grpcClient';
import { Button } from '@/components/common/Button';

interface APIResult {
  endpoint: string;
  status: 'success' | 'error' | 'pending';
  data?: unknown;
  error?: string;
  durationMs?: number;
}

export function APITester() {
  const [instruction, setInstruction] = useState('拿起红色杯子');
  const [results, setResults] = useState<APIResult[]>([]);

  const runTest = useCallback(async (endpoint: string, fn: () => Promise<unknown>) => {
    const start = performance.now();
    setResults((prev) => [...prev, { endpoint, status: 'pending' }]);

    try {
      const data = await fn();
      const durationMs = performance.now() - start;
      setResults((prev) =>
        prev.map((r) => (r.endpoint === endpoint && r.status === 'pending'
          ? { endpoint, status: 'success', data, durationMs } : r))
      );
    } catch (err) {
      const durationMs = performance.now() - start;
      setResults((prev) =>
        prev.map((r) => (r.endpoint === endpoint && r.status === 'pending'
          ? { endpoint, status: 'error', error: (err as Error).message, durationMs } : r))
      );
    }
  }, []);

  const runAll = useCallback(async () => {
    setResults([]);
    await runTest('ParseIntent', () => grpcClient.parseIntent(instruction));
    await runTest('DecomposeTask', () =>
      grpcClient.decomposeTask({ action: 'pick', target: 'red_cup', constraints: [], confidence: 0.9 })
    );
    await runTest('GenerateTrajectories', () =>
      grpcClient.generateTrajectories('test_plan', { x: 0.3, y: 0.1, z: 0.2 })
    );
    await runTest('ListSkills', () => grpcClient.listSkills());
  }, [instruction, runTest]);

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          className="flex-1 bg-brain-surface border border-brain-border rounded px-2 py-1 text-xs text-brain-text"
          placeholder="输入测试指令..."
        />
        <Button size="sm" onClick={runAll}>测试全部</Button>
      </div>

      <div className="space-y-1.5">
        {results.map((r, i) => (
          <div
            key={`${r.endpoint}_${i}`}
            className={`
              rounded p-2 text-xs border
              ${r.status === 'success' ? 'border-green-500/20 bg-green-500/5'
              : r.status === 'error' ? 'border-red-500/20 bg-red-500/5'
              : 'border-brain-border bg-brain-surface'}
            `.trim()}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-brain-text">{r.endpoint}</span>
              <div className="flex items-center gap-2">
                {r.durationMs !== undefined && (
                  <span className="text-[10px] text-brain-muted">{r.durationMs.toFixed(0)}ms</span>
                )}
                <span className={`text-[10px] ${
                  r.status === 'success' ? 'text-green-400'
                  : r.status === 'error' ? 'text-red-400' : 'text-brain-muted'
                }`}>
                  {r.status === 'success' ? '✓' : r.status === 'error' ? '✕' : '...'}
                </span>
              </div>
            </div>
            {r.error && (
              <p className="text-red-400 mt-1">{r.error}</p>
            )}
            {r.status === 'success' && r.data && (
              <pre className="mt-1 text-[10px] text-brain-muted overflow-x-auto">
                {JSON.stringify(r.data, null, 2).slice(0, 200)}
              </pre>
            )}
          </div>
        ))}
      </div>

      {results.length > 0 && (
        <Button size="sm" variant="ghost" onClick={() => setResults([])}>
          清除结果
        </Button>
      )}
    </div>
  );
}
