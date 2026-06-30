/**
 * src/components/camera-view/CameraView.tsx — Camera feed viewer
 *
 * Stub component for displaying real-time camera feeds from
 * the robot in the dashboard. Full camera integration
 * deferred to Phase 2 with actual hardware.
 */
'use client';

import React, { useState } from 'react';

interface CameraViewProps {
  streamUrl?: string;
  width?: number;
  height?: number;
}

export function CameraView({
  streamUrl,
  width = 320,
  height = 240,
}: CameraViewProps) {
  const [hasStream, setHasStream] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="panel-card">
      <h3 className="text-sm font-semibold text-brain-text mb-2">相机画面</h3>
      <div
        className="relative bg-brain-bg rounded border border-brain-border overflow-hidden"
        style={{ width, height }}
      >
        {streamUrl && hasStream ? (
          <img
            src={streamUrl}
            alt="Camera feed"
            className="w-full h-full object-cover"
            onLoad={() => setHasStream(true)}
            onError={() => {
              setHasStream(false);
              setError('无法加载视频流');
            }}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-brain-muted">
            <svg className="w-8 h-8 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            {error ? (
              <span className="text-xs text-red-400">{error}</span>
            ) : (
              <span className="text-xs">相机未连接</span>
            )}
          </div>
        )}
      </div>
      <div className="flex gap-2 mt-2">
        <button
          className="text-[10px] text-brain-muted hover:text-brain-text px-2 py-0.5 rounded bg-brain-surface transition-colors"
          onClick={() => setError(null)}
        >
          重新连接
        </button>
        <span className="text-[10px] text-brain-muted self-center">
          支持 RTSP / MJPEG / WebRTC
        </span>
      </div>
    </div>
  );
}
