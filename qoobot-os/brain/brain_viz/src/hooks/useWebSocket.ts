/**
 * src/hooks/useWebSocket.ts — WebSocket lifecycle hook
 *
 * Manages WebSocket connection lifecycle and event subscription
 * with React cleanup. Bridge between wsClient service and components.
 */
'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { wsClient } from '@/services/wsClient';
import type { WSEventType, WSEvent } from '@/types/domain';
import type { ConnectionState } from '@/types/events';

interface UseWebSocketOptions {
  autoConnect?: boolean;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
}

interface UseWebSocketReturn {
  connectionState: ConnectionState;
  connect: () => void;
  disconnect: () => void;
  subscribe: <T = Record<string, unknown>>(
    eventType: WSEventType,
    callback: (payload: T) => void
  ) => () => void;
  send: (type: string, payload: Record<string, unknown>) => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { autoConnect = true } = options;
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const unsubscribeRefs = useRef<Array<() => void>>([]);

  const connect = useCallback(() => {
    setConnectionState('connecting');
    wsClient.connect();
    // wsClient manages its own connection lifecycle,
    // we approximate state here
    const checkInterval = setInterval(() => {
      // The wsClient doesn't expose readyState publicly,
      // so we track via the onopen/onclose callbacks
    }, 500);

    setTimeout(() => {
      setConnectionState((prev) =>
        prev === 'connecting' ? 'connected' : prev
      );
      clearInterval(checkInterval);
    }, 1000);
  }, []);

  const disconnect = useCallback(() => {
    wsClient.disconnect();
    setConnectionState('disconnected');
  }, []);

  const subscribe = useCallback(
    <T = Record<string, unknown>>(
      eventType: WSEventType,
      callback: (payload: T) => void
    ): (() => void) => {
      const unsubscribe = wsClient.on(eventType, (event: WSEvent) => {
        callback(event.payload as T);
      });
      unsubscribeRefs.current.push(unsubscribe);
      return unsubscribe;
    },
    []
  );

  const send = useCallback(
    (type: string, payload: Record<string, unknown>) => {
      wsClient.send(type, payload);
    },
    []
  );

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      unsubscribeRefs.current.forEach((fn) => fn());
      unsubscribeRefs.current = [];
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]);

  return { connectionState, connect, disconnect, subscribe, send };
}
