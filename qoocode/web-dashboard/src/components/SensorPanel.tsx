import React, { useMemo } from 'react';
import { useSimStore, SensorStats } from '../store/simStore';
import { Camera, Radio, Gauge, Waves } from 'lucide-react';

const SENSOR_ICONS: Record<string, React.ReactNode> = {
  rgb_camera: <Camera size={16} />,
  depth_camera: <Camera size={16} />,
  rgbd_camera: <Camera size={16} />,
  imu: <Gauge size={16} />,
  lidar: <Radio size={16} />,
  joint_states: <Waves size={16} />,
};

export function SensorPanel() {
  const sensorStats = useSimStore((s) => s.sensorStats);

  return (
    <div style={styles.container}>
      {sensorStats.length === 0 && (
        <div style={styles.empty}>暂无传感器数据</div>
      )}

      <div style={styles.grid}>
        {sensorStats.map((sensor) => (
          <SensorCard key={sensor.name} sensor={sensor} />
        ))}
      </div>
    </div>
  );
}

function SensorCard({ sensor }: { sensor: SensorStats }) {
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <span style={styles.cardIcon}>
          {SENSOR_ICONS[sensor.type] || <Radio size={16} />}
        </span>
        <div>
          <div style={styles.cardTitle}>{sensor.name}</div>
          <div style={styles.cardType}>{sensor.type}</div>
        </div>
      </div>

      <div style={styles.metrics}>
        <div style={styles.metric}>
          <span style={styles.metricLabel}>频率</span>
          <span style={styles.metricValue}>{sensor.rateHz.toFixed(1)} Hz</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.metricLabel}>帧数</span>
          <span style={styles.metricValue}>{sensor.count}</span>
        </div>
        <div style={styles.metric}>
          <span style={styles.metricLabel}>形状</span>
          <span style={styles.metricValue}>
            [{sensor.shape?.join(', ') || 'N/A'}]
          </span>
        </div>
      </div>

      {/* 数值范围条 */}
      <div style={styles.rangeBar}>
        <div style={styles.rangeLabel}>范围</div>
        <div style={styles.rangeTrack}>
          <div style={{
            ...styles.rangeFill,
            width: `${Math.min(100, ((sensor.max - sensor.min) / (sensor.max || 1)) * 100)}%`,
          }} />
        </div>
        <div style={styles.rangeValues}>
          <span>{sensor.min?.toFixed(2)}</span>
          <span>{sensor.max?.toFixed(2)}</span>
        </div>
      </div>

      <div style={styles.stats}>
        <span>均值: {sensor.mean?.toFixed(3)}</span>
        <span>标准差: {sensor.mean?.toFixed(3)}</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    height: '100%',
    overflow: 'auto',
    padding: 12,
  },
  empty: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: 'var(--text-secondary)',
    fontSize: 14,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 12,
  },
  card: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: 14,
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    marginBottom: 12,
  },
  cardIcon: {
    color: 'var(--accent)',
    marginTop: 2,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: 600,
  },
  cardType: {
    fontSize: 11,
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
  },
  metrics: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: 8,
    marginBottom: 12,
  },
  metric: {
    textAlign: 'center' as const,
  },
  metricLabel: {
    fontSize: 10,
    color: 'var(--text-secondary)',
    display: 'block',
  },
  metricValue: {
    fontSize: 14,
    fontWeight: 600,
    fontFamily: 'monospace',
    fontVariantNumeric: 'tabular-nums' as const,
  },
  rangeBar: {
    marginBottom: 8,
  },
  rangeLabel: {
    fontSize: 10,
    color: 'var(--text-secondary)',
    marginBottom: 4,
  },
  rangeTrack: {
    height: 4,
    background: 'var(--bg-tertiary)',
    borderRadius: 2,
    marginBottom: 2,
  },
  rangeFill: {
    height: '100%',
    background: 'var(--accent)',
    borderRadius: 2,
    transition: 'width 0.3s',
  },
  rangeValues: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 10,
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
  },
  stats: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: 11,
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
  },
};
