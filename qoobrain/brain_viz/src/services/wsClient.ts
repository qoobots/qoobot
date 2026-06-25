/**
 * src/services/wsClient.ts — WebSocket client for brain_ai communication
 *
 * Connects to brain_ai WebSocket server (ws://localhost:8765)
 * Dispatches typed events to Zustand stores.
 */

import type { WSEvent, WSEventType } from '@/types/domain';

type EventCallback = (event: WSEvent) => void;

class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private listeners: Map<WSEventType, Set<EventCallback>> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 1000;

  constructor(url: string = 'ws://localhost:8765') {
    this.url = url;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    console.log('[WSClient] Connecting to', this.url);
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('[WSClient] Connected');
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (msg: MessageEvent) => {
      try {
        const event: WSEvent = JSON.parse(msg.data as string);
        this.dispatch(event);
      } catch (err) {
        console.error('[WSClient] Parse error:', err);
      }
    };

    this.ws.onclose = () => {
      console.log('[WSClient] Disconnected — reconnecting in', this.reconnectDelay, 'ms');
      this.scheduleReconnect();
    };

    this.ws.onerror = (err) => {
      console.error('[WSClient] Error:', err);
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  on(eventType: WSEventType, callback: EventCallback): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);

    return () => {
      this.listeners.get(eventType)?.delete(callback);
    };
  }

  send(type: string, payload: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
    }
  }

  private dispatch(event: WSEvent): void {
    const cbs = this.listeners.get(event.type);
    if (cbs) {
      cbs.forEach((cb) => cb(event));
    }
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => {
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
      this.connect();
    }, this.reconnectDelay);
  }
}

export const wsClient = new WSClient(
  typeof window !== 'undefined'
    ? `ws://${window.location.hostname}:8765`
    : 'ws://localhost:8765'
);
