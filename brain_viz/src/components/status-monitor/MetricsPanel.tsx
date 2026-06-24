/**
 * src/components/status-monitor/MetricsPanel.tsx — Performance metrics dashboard
 */
'use client';

import React, { useEffect, useRef } from 'react';
import { useMonitorStore } from '@/stores/monitorStore';
import { ProgressBar } from '@/components/common/ProgressBar';
import { formatBytes, formatFrequency } from '@/utils/formatTime';

function MiniSparkline({ data, color, height = 30 }: {
  data: { timestamp: string; value: number }[];
  color: string;
  height?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length < 2) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const h = canvas.height;

    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;

    ctx.clearRect(0, 0, width, h);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    data.forEach((d, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = h - ((d.value - min) / range) * (h - 4) - 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });

    ctx.stroke();
  }, [data, color]);

  return (
    <canvas
      ref={canvasRef}
      width={120}
      height={height}
      className="w-full h-full"
    />
  );
}

export function MetricsPanel() {
  const metrics = useMonitorStore((s) => s.metrics);

  return (
    <div className="panel-card space-y-3">
      <h3 className="text-sm font-semibold text-brain-text">性能指标</h3>

      {/* CPU */}
      <div>
        <div className="flex justify-between mb-1">
          <span className="text-xs text-brain-muted">CPU</span>
          <span className="text-xs font-mono text-brain-text">{metrics.cpuPercent.toFixed(1)}%</span>
        </div>
        <ProgressBar value={metrics.cpuPercent} max={100} size="sm" color="#6366f1" />
        <div className="h-6 mt-0.5">
          <MiniSparkline
            data={metrics.history.cpu}
            color="#6366f1"
            height={20}
          />
        </div>
      </div>

      {/* Memory */}
      <div>
        <div className="flex justify-between mb-1">
          <span className="text-xs text-brain-muted">内存</span>
          <span className="text-xs font-mono text-brain-text">
            {formatBytes(metrics.memoryMB * 1024 * 1024)}
          </span>
        </div>
        <ProgressBar value={metrics.memoryMB} max={4096} size="sm" color="#22c55e" />
        <div className="h-6 mt-0.5">
          <MiniSparkline
            data={metrics.history.memory}
            color="#22c55e"
            height={20}
          />
        </div>
      </div>

      {/* GPU */}
      {metrics.gpuPercent > 0 && (
        <div>
          <div className="flex justify-between mb-1">
            <span className="text-xs text-brain-muted">GPU</span>
            <span className="text-xs font-mono text-brain-text">{metrics.gpuPercent.toFixed(1)}%</span>
          </div>
          <ProgressBar value={metrics.gpuPercent} max={100} size="sm" color="#8b5cf6" />
        </div>
      )}

      {/* Frame Rate */}
      <div>
        <div className="flex justify-between mb-1">
          <span className="text-xs text-brain-muted">帧率</span>
          <span className="text-xs font-mono text-brain-text">
            {formatFrequency(metrics.frameRate)}
          </span>
        </div>
        <div className="h-6 mt-0.5">
          <MiniSparkline
            data={metrics.history.frameRate}
            color="#f59e0b"
            height={20}
          />
        </div>
      </div>

      {/* gRPC & WS Latency */}
      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-brain-border">
        <div>
          <span className="text-[10px] text-brain-muted">gRPC 延迟</span>
          <p className="text-sm font-mono text-brain-text">{metrics.gRPCLatencyMs.toFixed(1)}ms</p>
        </div>
        <div>
          <span className="text-[10px] text-brain-muted">WS 延迟</span>
          <p className="text-sm font-mono text-brain-text">{metrics.wsLatencyMs.toFixed(1)}ms</p>
        </div>
      </div>
    </div>
  );
}
