/**
 * src/components/hitl-panel/Countdown.tsx — HITL countdown timer
 */
'use client';

import { useEffect, useRef, useState } from 'react';

interface CountdownProps {
  seconds: number;
  onTimeout: () => void;
}

export function Countdown({ seconds, onTimeout }: CountdownProps) {
  const [remaining, setRemaining] = useState(seconds);
  const onTimeoutRef = useRef(onTimeout);
  onTimeoutRef.current = onTimeout;

  useEffect(() => {
    setRemaining(seconds);
    const start = Date.now();

    const timer = setInterval(() => {
      const elapsed = (Date.now() - start) / 1000;
      const left = Math.max(0, seconds - elapsed);
      setRemaining(left);

      if (left <= 0) {
        clearInterval(timer);
        onTimeoutRef.current();
      }
    }, 50);

    return () => clearInterval(timer);
  }, [seconds]);

  const pct = (remaining / seconds) * 100;
  const isUrgent = remaining < 1.5;

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-2 bg-brain-border rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-100 ${
            isUrgent ? 'bg-brain-danger' : 'bg-brain-accent'
          }`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-sm font-mono font-bold ${
        isUrgent ? 'text-brain-danger' : 'text-brain-text'
      }`}>
        {remaining.toFixed(1)}s
      </span>
    </div>
  );
}
