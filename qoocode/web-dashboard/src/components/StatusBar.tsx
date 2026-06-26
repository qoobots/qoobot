import React from 'react';
import { useSimStore } from '../store/simStore';
import { Wifi, WifiOff, Play, Pause, Square, Clock } from 'lucide-react';

interface Props {
  connected: boolean;
}

export function StatusBar({ connected }: Props) {
  const simState = useSimStore((s) => s.simState);
  const stats = useSimStore((s) => s.stats);

  const stateIcon = () => {
    switch (simState) {
      case 'RUNNING': return <Play size={14} color="#22c55e" />;
      case 'PAUSED': return <Pause size={14} color="#eab308" />;
      case 'STOPPED': return <Square size={14} color="#94a3b8" />;
      default: return <Clock size={14} color="#94a3b8" />;
    }
  };

  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <div style={styles.logo}>QooCode Dashboard</div>
        <div style={styles.separator} />
        <div style={styles.status}>
          {connected ? (
            <Wifi size={14} color="#22c55e" />
          ) : (
            <WifiOff size={14} color="#ef4444" />
          )}
          <span style={{ color: connected ? '#22c55e' : '#ef4444' }}>
            {connected ? '已连接' : '未连接'}
          </span>
        </div>
        <div style={styles.separator} />
        <div style={styles.status}>
          {stateIcon()}
          <span>{simState}</span>
        </div>
      </div>

      <div style={styles.right}>
        <span style={styles.metric}>
          仿真时间: {stats.simTime.toFixed(2)}s
        </span>
        <span style={styles.metric}>
          步数: {stats.totalSteps.toLocaleString()}
        </span>
        <span style={styles.metric}>
          RTF: {stats.realTimeFactor.toFixed(2)}x
        </span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    height: 32,
    padding: '0 12px',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border)',
    fontSize: 12,
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  logo: {
    fontWeight: 700,
    color: 'var(--accent)',
    letterSpacing: '-0.02em',
  },
  separator: {
    width: 1,
    height: 16,
    background: 'var(--border)',
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
  },
  metric: {
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
    fontVariantNumeric: 'tabular-nums',
  },
};
