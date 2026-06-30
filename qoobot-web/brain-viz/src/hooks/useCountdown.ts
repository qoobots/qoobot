/**
 * src/hooks/useCountdown.ts — Countdown timer hook
 *
 * Manages countdown state with callbacks for tick, timeout, and user confirmation.
 * Used by HITL panel and emergency response flows.
 */
'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

interface UseCountdownOptions {
  initialSeconds?: number;
  onTick?: (remaining: number) => void;
  onTimeout?: () => void;
  autoStart?: boolean;
  tickIntervalMs?: number;
}

interface UseCountdownReturn {
  remaining: number;
  isRunning: boolean;
  progress: number;         // 0..1
  isUrgent: boolean;        // < 3 seconds
  isCritical: boolean;      // < 1 second
  start: (seconds?: number) => void;
  stop: () => void;
  reset: (seconds?: number) => void;
  pause: () => void;
  resume: () => void;
}

const URGENT_THRESHOLD = 3;
const CRITICAL_THRESHOLD = 1;

export function useCountdown(options: UseCountdownOptions = {}): UseCountdownReturn {
  const {
    initialSeconds = 0,
    onTick,
    onTimeout,
    autoStart = false,
    tickIntervalMs = 100,
  } = options;

  const [remaining, setRemaining] = useState(initialSeconds);
  const [isRunning, setIsRunning] = useState(autoStart);
  const totalRef = useRef(initialSeconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onTimeoutRef = useRef(onTimeout);
  const onTickRef = useRef(onTick);

  // Keep callbacks fresh
  useEffect(() => {
    onTimeoutRef.current = onTimeout;
    onTickRef.current = onTick;
  });

  const clearTimer = useCallback(() => {
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const start = useCallback(
    (seconds?: number) => {
      clearTimer();
      const total = seconds ?? totalRef.current;
      totalRef.current = total;
      setRemaining(total);
      setIsRunning(true);
    },
    [clearTimer]
  );

  const stop = useCallback(() => {
    clearTimer();
    setIsRunning(false);
    setRemaining(0);
  }, [clearTimer]);

  const reset = useCallback(
    (seconds?: number) => {
      clearTimer();
      const total = seconds ?? totalRef.current;
      totalRef.current = total;
      setRemaining(total);
      setIsRunning(false);
    },
    [clearTimer]
  );

  const pause = useCallback(() => {
    clearTimer();
    setIsRunning(false);
  }, [clearTimer]);

  const resume = useCallback(() => {
    if (remaining > 0) {
      setIsRunning(true);
    }
  }, [remaining]);

  // Timer tick effect
  useEffect(() => {
    if (!isRunning || remaining <= 0) {
      clearTimer();
      return;
    }

    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        const next = Math.max(0, prev - tickIntervalMs / 1000);
        onTickRef.current?.(next);

        if (next <= 0) {
          clearTimer();
          setIsRunning(false);
          // Delay the timeout callback to avoid setState-during-render
          setTimeout(() => onTimeoutRef.current?.(), 0);
        }

        return next;
      });
    }, tickIntervalMs);

    return clearTimer;
  }, [isRunning, tickIntervalMs, clearTimer]);

  // Auto-start effect
  useEffect(() => {
    if (autoStart && initialSeconds > 0) {
      start(initialSeconds);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const progress = totalRef.current > 0 ? remaining / totalRef.current : 0;
  const isUrgent = remaining <= URGENT_THRESHOLD && remaining > CRITICAL_THRESHOLD;
  const isCritical = remaining <= CRITICAL_THRESHOLD && remaining > 0;

  return {
    remaining,
    isRunning,
    progress,
    isUrgent,
    isCritical,
    start,
    stop,
    reset,
    pause,
    resume,
  };
}
