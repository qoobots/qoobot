/**
 * src/hooks/useGrpcStream.ts — gRPC streaming hook
 *
 * Manages gRPC server-streaming RPC lifecycle with React state.
 * Handles stream open/close, message accumulation, and error recovery.
 */
'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { grpcClient } from '@/services/grpcClient';

interface UseGrpcStreamOptions {
  retryOnError?: boolean;
  maxRetries?: number;
  retryDelayMs?: number;
}

interface UseGrpcStreamReturn<T> {
  messages: T[];
  isStreaming: boolean;
  error: Error | null;
  startStream: (streamId: string) => void;
  stopStream: () => void;
  clearMessages: () => void;
}

export function useGrpcStream<T = Record<string, unknown>>(
  streamName: string,
  options: UseGrpcStreamOptions = {}
): UseGrpcStreamReturn<T> {
  const { retryOnError = true, maxRetries = 3, retryDelayMs = 2000 } = options;

  const [messages, setMessages] = useState<T[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const retryCount = useRef(0);
  const activeStreamId = useRef<string | null>(null);
  const cancelled = useRef(false);

  const clearMessages = useCallback(() => setMessages([]), []);

  const stopStream = useCallback(() => {
    cancelled.current = true;
    setIsStreaming(false);
    activeStreamId.current = null;
  }, []);

  const startStream = useCallback(
    (streamId: string) => {
      cancelled.current = false;
      activeStreamId.current = streamId;
      setIsStreaming(true);
      setError(null);
      retryCount.current = 0;

      const pollStream = async () => {
        // Note: Real gRPC-Web streaming would use the generated client.
        // This hook provides a simulated streaming pattern with the stub client,
        // polling at ~10Hz. Replace with real gRPC streaming when the service
        // is connected.
        let attempts = 0;

        while (!cancelled.current && attempts < (maxRetries + 1) * 10) {
          try {
            // Simulated stream message - replace with real gRPC stream call
            const response = await (grpcClient as any)[`stream_${streamName}`]?.();
            if (response && !cancelled.current) {
              setMessages((prev) => [...prev, response as T]);
            }
            await new Promise((resolve) => setTimeout(resolve, 100));
            attempts++;
          } catch (err) {
            if (cancelled.current) break;

            const e = err instanceof Error ? err : new Error(String(err));
            setError(e);
            retryCount.current++;

            if (retryOnError && retryCount.current < maxRetries) {
              await new Promise((resolve) => setTimeout(resolve, retryDelayMs));
            } else {
              setIsStreaming(false);
              break;
            }
          }
        }

        if (!cancelled.current) {
          setIsStreaming(false);
        }
      };

      pollStream();
    },
    [retryOnError, maxRetries, retryDelayMs]
  );

  useEffect(() => {
    return () => {
      cancelled.current = true;
    };
  }, []);

  return { messages, isStreaming, error, startStream, stopStream, clearMessages };
}
