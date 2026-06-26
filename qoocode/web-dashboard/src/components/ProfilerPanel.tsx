import React from 'react';
import { useSimStore, LatencyStats } from '../store/simStore';
import { Zap, Clock, Cpu } from 'lucide-react';

const STAGE_COLORS: Record<string, string> = {
  perception: '#3b82f6',
  planning: '#8b5cf6',
  control: '#22c55e',
  communication: '#f59e0b',
};

export function ProfilerPanel() {
  const latencyStats = useSimStore((s) => s.latencyStats);

  return (
    <div style={styles.container}>
      {latencyStats.length === 0 && (
        <div style={styles.empty}>
          <Zap size={32} style={{ opacity: 0.3 }} />
          <span>暂无性能数据</span>
        </div>
      )}

      <div style={styles.grid}>
        {latencyStats.map((stage) => (
          <LatencyCard key={stage.stage} stage={stage} />
        ))}
      </div>

      {/* 总览 */}
      {latencyStats.length > 0 && (
        <div style={styles.overview}>
          <div style={styles.overviewTitle}>链路总览</div>
          <div style={styles.chain}>
            {latencyStats.map((stage, i) => (
              <React.Fragment key={stage.stage}>
                {i > 0 && <span style={styles.chainArrow}>→</span>}
                <div style={styles.chainNode}>
                  <div style={{
                    ...styles.chainDot,
                    background: STAGE_COLORS[stage.stage] || '#64748b',
                  }} />
                  <span style={styles.chainLabel}>{stage.stage}</span>
                  <span style={styles.chainValue}>{stage.meanMs.toFixed(1)}ms</span>
                </div>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LatencyCard({ stage }: { stage: LatencyStats }) {
  const color = STAGE_COLORS[stage.stage] || '#64748b';
  const maxMs = Math.max(stage.p99Ms, stage.meanMs * 1.5);

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <div style={{ ...styles.stageDot, background: color }} />
        <div>
          <div style={styles.stageName}>{stage.stage}</div>
          <div style={styles.stageCount}>{stage.count} 次采样</div>
        </div>
      </div>

      {/* 延迟柱状图 */}
      <div style={styles.bars}>
        <div style={styles.barGroup}>
          <div style={styles.barLabel}>均值</div>
          <div style={styles.barTrack}>
            <div style={{
              ...styles.barFill,
              width: `${(stage.meanMs / maxMs) * 100}%`,
              background: color,
            }} />
          </div>
          <div style={styles.barValue}>{stage.meanMs.toFixed(2)}ms</div>
        </div>
        <div style={styles.barGroup}>
          <div style={styles.barLabel}>P95</div>
          <div style={styles.barTrack}>
            <div style={{
              ...styles.barFill,
              width: `${(stage.p95Ms / maxMs) * 100}%`,
              background: color,
              opacity: 0.7,
            }} />
          </div>
          <div style={styles.barValue}>{stage.p95Ms.toFixed(2)}ms</div>
        </div>
        <div style={styles.barGroup}>
          <div style={styles.barLabel}>P99</div>
          <div style={styles.barTrack}>
            <div style={{
              ...styles.barFill,
              width: `${(stage.p99Ms / maxMs) * 100}%`,
              background: '#ef4444',
              opacity: 0.7,
            }} />
          </div>
          <div style={styles.barValue}>{stage.p99Ms.toFixed(2)}ms</div>
        </div>
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
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: 12,
    color: 'var(--text-secondary)',
    fontSize: 14,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: 12,
    marginBottom: 16,
  },
  card: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: 14,
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 14,
  },
  stageDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    flexShrink: 0,
  },
  stageName: {
    fontSize: 14,
    fontWeight: 600,
    textTransform: 'capitalize' as const,
  },
  stageCount: {
    fontSize: 11,
    color: 'var(--text-secondary)',
  },
  bars: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  barGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  barLabel: {
    width: 32,
    fontSize: 11,
    color: 'var(--text-secondary)',
    textAlign: 'right' as const,
  },
  barTrack: {
    flex: 1,
    height: 8,
    background: 'var(--bg-tertiary)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 4,
    transition: 'width 0.3s',
  },
  barValue: {
    width: 60,
    fontSize: 11,
    fontFamily: 'monospace',
    fontVariantNumeric: 'tabular-nums' as const,
    textAlign: 'right' as const,
  },
  overview: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: 16,
  },
  overviewTitle: {
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 12,
  },
  chain: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap' as const,
  },
  chainArrow: {
    color: 'var(--text-secondary)',
    fontSize: 14,
  },
  chainNode: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    background: 'var(--bg-tertiary)',
    borderRadius: 6,
  },
  chainDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
  },
  chainLabel: {
    fontSize: 12,
    fontWeight: 500,
  },
  chainValue: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: 'var(--text-secondary)',
  },
};
