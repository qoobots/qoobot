import { useEffect, useRef } from 'react';
import { useSimStore } from '../store/simStore';

const WS_URL = 'ws://localhost:8090/ws';

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<number>();
  const store = useSimStore();

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  function connect() {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        store.setConnected(true);
        console.log('[WS] 已连接');
      };

      ws.onclose = () => {
        store.setConnected(false);
        store.setSimState('STOPPED');
        console.log('[WS] 已断开，3秒后重连...');
        reconnectTimer.current = window.setTimeout(connect, 3000);
      };

      ws.onerror = (err) => {
        console.error('[WS] 错误:', err);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleMessage(msg);
        } catch (e) {
          console.error('[WS] 消息解析失败:', e);
        }
      };
    } catch (err) {
      console.error('[WS] 连接失败:', err);
      reconnectTimer.current = window.setTimeout(connect, 3000);
    }
  }

  function handleMessage(msg: Record<string, unknown>) {
    switch (msg.type) {
      case 'sim_state':
        store.setSimState(msg.state as string);
        break;

      case 'sim_stats':
        store.updateStats({
          simTime: msg.sim_time as number,
          totalSteps: msg.total_steps as number,
          realTimeFactor: msg.real_time_factor as number,
          stepTimeMs: msg.step_time_ms as number,
          physicsTimeMs: msg.physics_time_ms as number,
          renderTimeMs: msg.render_time_ms as number,
        });
        break;

      case 'scene_update':
        store.updateScene(msg.snapshot as any);
        break;

      case 'log':
        store.addLog({
          timestamp: msg.timestamp as number,
          level: (msg.level as string)?.toUpperCase() as any || 'INFO',
          message: msg.message as string,
          source: (msg.source as string) || '',
        });
        break;

      case 'sensor_stats':
        store.updateSensorStats(msg.stats as any);
        break;

      case 'latency_stats':
        store.updateLatencyStats(msg.stats as any);
        break;
    }
  }

  return { send: (msg: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }};
}
