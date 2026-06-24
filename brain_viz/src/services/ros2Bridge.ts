/**
 * src/services/ros2Bridge.ts — ROS 2 bridge client for brain_viz
 *
 * Connects to brain_core via rosbridge WebSocket for real-time
 * robot state and sensor data streaming.
 */

interface ROS2BridgeConfig {
  url: string;
  reconnectDelay?: number;
  maxReconnectAttempts?: number;
}

interface TopicSubscription {
  topic: string;
  messageType: string;
  callback: (message: unknown) => void;
}

class ROS2Bridge {
  private ws: WebSocket | null = null;
  private config: ROS2BridgeConfig;
  private subscriptions: TopicSubscription[] = [];
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private connected = false;

  constructor(config: ROS2BridgeConfig) {
    this.config = {
      reconnectDelay: 2000,
      maxReconnectAttempts: 5,
      ...config,
    };
  }

  get isConnected(): boolean { return this.connected; }

  async connect(): Promise<boolean> {
    if (this.ws?.readyState === WebSocket.OPEN) return true;

    return new Promise((resolve) => {
      try {
        this.ws = new WebSocket(this.config.url);

        this.ws.onopen = () => {
          console.log('[ROS2Bridge] Connected');
          this.connected = true;
          this.reconnectAttempts = 0;
          // Advertise as rosbridge client
          this.send({
            op: 'advertise',
            topic: '/brain_viz/status',
            type: 'std_msgs/String',
          });
          // Re-subscribe to previous topics
          for (const sub of this.subscriptions) {
            this.send({
              op: 'subscribe',
              topic: sub.topic,
              type: sub.messageType,
            });
          }
          resolve(true);
        };

        this.ws.onmessage = (event: MessageEvent) => {
          try {
            const msg = JSON.parse(event.data as string);
            this.handleMessage(msg);
          } catch (err) {
            console.error('[ROS2Bridge] Parse error:', err);
          }
        };

        this.ws.onclose = () => {
          this.connected = false;
          console.log('[ROS2Bridge] Disconnected');
          this.scheduleReconnect();
          resolve(false);
        };

        this.ws.onerror = () => {
          resolve(false);
        };
      } catch {
        resolve(false);
      }
    });
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
    this.connected = false;
  }

  subscribe<T = unknown>(
    topic: string,
    messageType: string,
    callback: (message: T) => void
  ): () => void {
    const sub: TopicSubscription = { topic, messageType, callback: callback as (msg: unknown) => void };
    this.subscriptions.push(sub);

    if (this.connected) {
      this.send({ op: 'subscribe', topic, type: messageType });
    }

    return () => {
      this.subscriptions = this.subscriptions.filter((s) => s !== sub);
      if (this.connected) {
        this.send({ op: 'unsubscribe', topic });
      }
    };
  }

  publish(topic: string, messageType: string, message: unknown): void {
    this.send({ op: 'publish', topic, msg: message });
  }

  callService<T = unknown>(
    service: string, request: unknown
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const id = `srv_${Date.now()}`;
      const timeout = setTimeout(() => {
        reject(new Error(`Service call ${service} timed out`));
      }, 5000);

      const handler = (event: MessageEvent) => {
        try {
          const msg = JSON.parse(event.data as string);
          if (msg.op === 'service_response' && msg.id === id) {
            this.ws?.removeEventListener('message', handler);
            clearTimeout(timeout);
            if (msg.result) {
              resolve(msg.values as T);
            } else {
              reject(new Error(`Service ${service} returned false`));
            }
          }
        } catch { /* ignore */ }
      };

      this.ws?.addEventListener('message', handler);
      this.send({ op: 'call_service', id, service, args: request });
    });
  }

  /** Get current joint states. */
  async getJointStates(): Promise<{
    names: string[]; positions: number[];
    velocities: number[]; efforts: number[];
  }> {
    return this.callService('/get_joint_states', {});
  }

  /** Execute a trajectory via FollowJointTrajectory action. */
  async executeTrajectory(waypoints: { positions: number[]; time_from_start: number }[]): Promise<{ success: boolean }> {
    return this.callService('/execute_trajectory', { waypoints });
  }

  private send(message: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  private handleMessage(msg: Record<string, unknown>): void {
    if (msg.op === 'publish') {
      const topic = msg.topic as string;
      const payload = msg.msg;
      for (const sub of this.subscriptions) {
        if (sub.topic === topic) {
          sub.callback(payload);
        }
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= (this.config.maxReconnectAttempts ?? 5)) {
      console.warn('[ROS2Bridge] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = (this.config.reconnectDelay ?? 2000) * Math.pow(1.5, this.reconnectAttempts - 1);

    this.reconnectTimer = setTimeout(() => {
      console.log(`[ROS2Bridge] Reconnecting (attempt ${this.reconnectAttempts})...`);
      this.connect();
    }, delay);
  }
}

export const ros2Bridge = new ROS2Bridge({
  url: typeof window !== 'undefined'
    ? `ws://${window.location.hostname}:9090`
    : 'ws://localhost:9090',
});
