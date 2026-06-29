import React, { useMemo, useState } from 'react';
import { useSimStore, LatencyStats } from '../store/simStore';
import { Zap, Clock, Cpu, AlertTriangle, HardDrive, Wifi, BarChart3, Flame, Gauge } from 'lucide-react';

const STAGE_COLORS: Record<string, string> = {
  perception: '#3b82f6',
  planning: '#8b5cf6',
  control: '#22c55e',
  communication: '#f59e0b',
  inference: '#ef4444',
};

interface Bottleneck {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  stage: string;
  description: string;
  suggestion: string;
  value: number;
}

interface ResourceSample {
  timestamp: number;
  cpu: number;
  gpu: number;
  npu: number;
  memory: number;
  memoryUsedMB: number;
  memoryTotalMB: number;
}

// Mock data generators for demonstration
function generateMockBottlenecks(latencyStats: LatencyStats[]): Bottleneck[] {
  const bottlenecks: Bottleneck[] = [];
  for (const stage of latencyStats) {
    if (stage.p99Ms > 100) {
      bottlenecks.push({
        id: `${stage.stage}-latency`,
        severity: 'critical',
        stage: stage.stage,
        description: `${stage.stage} P99 延迟过高 (${stage.p99Ms.toFixed(1)}ms)`,
        suggestion: `建议优化 ${stage.stage} 阶段算法或启用并行处理`,
        value: stage.p99Ms,
      });
    } else if (stage.p99Ms > 50) {
      bottlenecks.push({
        id: `${stage.stage}-latency`,
        severity: 'high',
        stage: stage.stage,
        description: `${stage.stage} P99 延迟偏高 (${stage.p99Ms.toFixed(1)}ms)`,
        suggestion: `考虑为 ${stage.stage} 增加缓存或减少计算复杂度`,
        value: stage.p99Ms,
      });
    }
  }
  return bottlenecks;
}

function generateMockResourceHistory(count: number): ResourceSample[] {
  const samples: ResourceSample[] = [];
  for (let i = 0; i < count; i++) {
    samples.push({
      timestamp: Date.now() - (count - i) * 1000,
      cpu: 30 + Math.random() * 50,
      gpu: 20 + Math.random() * 60,
      npu: 10 + Math.random() * 40,
      memory: 40 + Math.random() * 30,
      memoryUsedMB: 2048 + Math.random() * 2048,
      memoryTotalMB: 8192,
    });
  }
  return samples;
}

function generateMockFlameData() {
  return {
    name: 'Skill::run()',
    value: 100,
    children: [
      {
        name: 'Perception::process()',
        value: 35,
        children: [
          { name: 'Camera::capture()', value: 8 },
          { name: 'Detector::infer()', value: 18, children: [
            { name: 'NPU::forward()', value: 14 },
            { name: 'PostProcess::nms()', value: 4 },
          ]},
          { name: 'SensorFusion::merge()', value: 9 },
        ],
      },
      {
        name: 'Planning::plan()',
        value: 28,
        children: [
          { name: 'AStar::search()', value: 15 },
          { name: 'TrajectoryOpt::smooth()', value: 8 },
          { name: 'CollisionCheck::verify()', value: 5 },
        ],
      },
      {
        name: 'Control::execute()',
        value: 22,
        children: [
          { name: 'IK::solve()', value: 10 },
          { name: 'ImpedanceCtrl::compute()', value: 7 },
          { name: 'JointCmd::send()', value: 5 },
        ],
      },
      {
        name: 'Communication::publish()',
        value: 10,
        children: [
          { name: 'DDS::write()', value: 6 },
          { name: 'Serialization::pack()', value: 4 },
        ],
      },
      { name: 'Other', value: 5 },
    ],
  };
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#ef4444',
  high: '#f59e0b',
  medium: '#3b82f6',
  low: '#8b949e',
};

const SEVERITY_ICONS: Record<string, React.ReactNode> = {
  critical: <AlertTriangle size={14} color="#ef4444" />,
  high: <AlertTriangle size={14} color="#f59e0b" />,
  medium: <AlertTriangle size={14} color="#3b82f6" />,
  low: <AlertTriangle size={14} color="#8b949e" />,
};

type ProfilerView = 'latency' | 'resources' | 'flame' | 'bottlenecks';

export function ProfilerPanel() {
  const latencyStats = useSimStore((s) => s.latencyStats);
  const [view, setView] = useState<ProfilerView>('latency');

  const bottlenecks = useMemo(() => generateMockBottlenecks(latencyStats), [latencyStats]);
  const resourceHistory = useMemo(() => generateMockResourceHistory(60), []);
  const flameData = useMemo(() => generateMockFlameData(), []);

  return (
    <div style={styles.container}>
      {/* Sub-tabs */}
      <div style={styles.subTabs}>
        {([
          { id: 'latency' as const, label: '延迟', icon: <Clock size={14} /> },
          { id: 'resources' as const, label: '资源', icon: <Cpu size={14} /> },
          { id: 'flame' as const, label: '火焰图', icon: <Flame size={14} /> },
          { id: 'bottlenecks' as const, label: '瓶颈', icon: <Gauge size={14} /> },
        ]).map((tab) => (
          <button
            key={tab.id}
            style={{
              ...styles.subTab,
              ...(view === tab.id ? styles.subTabActive : {}),
            }}
            onClick={() => setView(tab.id)}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      <div style={styles.viewContent}>
        {latencyStats.length === 0 && view !== 'resources' && view !== 'flame' && (
          <div style={styles.empty}>
            <Zap size={32} style={{ opacity: 0.3 }} />
            <span>暂无性能数据 — 启动仿真后自动采集</span>
          </div>
        )}

        {view === 'latency' && <LatencyView latencyStats={latencyStats} />}
        {view === 'resources' && <ResourceView history={resourceHistory} />}
        {view === 'flame' && <FlameView data={flameData} />}
        {view === 'bottlenecks' && <BottleneckView bottlenecks={bottlenecks} />}
      </div>
    </div>
  );
}

// ─── Latency View ───────────────────────────────────────

function LatencyView({ latencyStats }: { latencyStats: LatencyStats[] }) {
  return (
    <>
      <div style={styles.grid}>
        {latencyStats.map((stage) => (
          <LatencyCard key={stage.stage} stage={stage} />
        ))}
      </div>

      {latencyStats.length > 0 && (
        <div style={styles.overview}>
          <div style={styles.overviewTitle}>端到端链路总览</div>
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
          {/* Total */}
          <div style={styles.totalRow}>
            <span style={styles.totalLabel}>总延迟</span>
            <span style={styles.totalValue}>
              {latencyStats.reduce((sum, s) => sum + s.meanMs, 0).toFixed(1)}ms
            </span>
          </div>
        </div>
      )}
    </>
  );
}

function LatencyCard({ stage }: { stage: LatencyStats }) {
  const color = STAGE_COLORS[stage.stage] || '#64748b';
  const maxMs = Math.max(stage.p99Ms, stage.meanMs * 1.5, 1);

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <div style={{ ...styles.stageDot, background: color }} />
        <div>
          <div style={styles.stageName}>{stage.stage}</div>
          <div style={styles.stageCount}>{stage.count} 次采样</div>
        </div>
      </div>

      <div style={styles.bars}>
        <BarRow label="均值" value={stage.meanMs} max={maxMs} color={color} />
        <BarRow label="P95" value={stage.p95Ms} max={maxMs} color={color} opacity={0.7} />
        <BarRow label="P99" value={stage.p99Ms} max={maxMs} color="#ef4444" opacity={0.7} />
      </div>
    </div>
  );
}

function BarRow({ label, value, max, color, opacity = 1 }: {
  label: string; value: number; max: number; color: string; opacity?: number;
}) {
  return (
    <div style={styles.barGroup}>
      <div style={styles.barLabel}>{label}</div>
      <div style={styles.barTrack}>
        <div style={{
          ...styles.barFill,
          width: `${Math.min((value / max) * 100, 100)}%`,
          background: color,
          opacity,
        }} />
      </div>
      <div style={styles.barValue}>{value.toFixed(2)}ms</div>
    </div>
  );
}

// ─── Resource View ──────────────────────────────────────

function ResourceView({ history }: { history: ResourceSample[] }) {
  const latest = history[history.length - 1];
  const maxCpu = Math.max(...history.map(h => h.cpu), 100);

  return (
    <div>
      {/* Current resource gauges */}
      {latest && (
        <div style={styles.resourceGrid}>
          <ResourceGauge label="CPU" value={latest.cpu} max={100} color="#3b82f6" icon={<Cpu size={18} />} />
          <ResourceGauge label="GPU" value={latest.gpu} max={100} color="#8b5cf6" icon={<Cpu size={18} />} />
          <ResourceGauge label="NPU" value={latest.npu} max={100} color="#22c55e" icon={<Cpu size={18} />} />
          <ResourceGauge label="Memory" value={latest.memory} max={100} color="#f59e0b" icon={<HardDrive size={18} />} />
        </div>
      )}

      {/* History sparkline */}
      <div style={styles.sparklineContainer}>
        <div style={styles.sparklineTitle}>CPU 利用率历史 (60s)</div>
        <div style={styles.sparkline}>
          {history.map((h, i) => (
            <div
              key={i}
              style={{
                ...styles.sparkBar,
                height: `${(h.cpu / maxCpu) * 100}%`,
                background: h.cpu > 80 ? '#ef4444' : h.cpu > 60 ? '#f59e0b' : '#3b82f6',
              }}
              title={`${h.cpu.toFixed(1)}%`}
            />
          ))}
        </div>
      </div>

      {/* Memory details */}
      {latest && (
        <div style={styles.memDetail}>
          <div style={styles.memRow}>
            <Wifi size={14} style={{ opacity: 0.5 }} />
            <span>已用: {(latest.memoryUsedMB / 1024).toFixed(1)} GB</span>
            <span>/ {(latest.memoryTotalMB / 1024).toFixed(1)} GB</span>
            <span style={{ color: 'var(--text-secondary)', marginLeft: 'auto' }}>
              {latest.memory.toFixed(1)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function ResourceGauge({ label, value, max, color, icon }: {
  label: string; value: number; max: number; color: string; icon: React.ReactNode;
}) {
  const pct = (value / max) * 100;
  const alertColor = value > 90 ? '#ef4444' : value > 70 ? '#f59e0b' : color;

  return (
    <div style={styles.gaugeCard}>
      <div style={styles.gaugeHeader}>
        {icon}
        <span style={styles.gaugeLabel}>{label}</span>
        <span style={{ ...styles.gaugeValue, color: alertColor }}>{value.toFixed(1)}%</span>
      </div>
      <div style={styles.gaugeTrack}>
        <div style={{
          ...styles.gaugeFill,
          width: `${pct}%`,
          background: alertColor,
          transition: 'width 0.5s',
        }} />
      </div>
    </div>
  );
}

// ─── Flame Graph View ───────────────────────────────────

interface FlameNode {
  name: string;
  value: number;
  children?: FlameNode[];
}

function FlameView({ data }: { data: FlameNode }) {
  const maxDepth = useMemo(() => getMaxDepth(data), [data]);

  function renderFlameNode(node: FlameNode, depth: number, parentWidth: number): React.ReactNode {
    const widthPct = (node.value / data.value) * 100;
    const hue = 200 + depth * 40;
    const lightness = 30 + depth * 8;

    return (
      <div key={`${node.name}-${depth}`} style={{ display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            ...styles.flameBlock,
            width: `${widthPct}%`,
            background: `hsl(${hue}, 60%, ${lightness}%)`,
            paddingLeft: depth > 0 ? 4 : 8,
            fontSize: depth === 0 ? 12 : 11,
            cursor: 'default',
          }}
          title={`${node.name}: ${node.value}ms`}
        >
          <span style={styles.flameLabel}>{node.name}</span>
          <span style={styles.flameValue}>{node.value}ms</span>
        </div>
        {node.children && node.children.length > 0 && (
          <div style={styles.flameChildren}>
            {node.children.map(child => renderFlameNode(child, depth + 1, node.value))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      <div style={styles.flameLegend}>
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          火焰图 — 宽度表示时间占比，纵向表示调用深度
        </span>
      </div>
      <div style={styles.flameContainer}>
        {renderFlameNode(data, 0, data.value)}
      </div>
    </div>
  );
}

function getMaxDepth(node: FlameNode): number {
  if (!node.children || node.children.length === 0) return 0;
  return 1 + Math.max(...node.children.map(getMaxDepth));
}

// ─── Bottleneck View ────────────────────────────────────

function BottleneckView({ bottlenecks }: { bottlenecks: Bottleneck[] }) {
  const criticalCount = bottlenecks.filter(b => b.severity === 'critical').length;
  const highCount = bottlenecks.filter(b => b.severity === 'high').length;

  return (
    <div>
      {/* Summary */}
      <div style={styles.bnSummary}>
        <div style={styles.bnSummaryItem}>
          <span style={{ color: '#ef4444', fontSize: 24, fontWeight: 700 }}>{criticalCount}</span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>严重</span>
        </div>
        <div style={styles.bnSummaryItem}>
          <span style={{ color: '#f59e0b', fontSize: 24, fontWeight: 700 }}>{highCount}</span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>高优先级</span>
        </div>
      </div>

      {bottlenecks.length === 0 ? (
        <div style={styles.bnEmpty}>
          <BarChart3 size={24} style={{ opacity: 0.3 }} />
          <span>未检测到性能瓶颈</span>
        </div>
      ) : (
        <div style={styles.bnList}>
          {bottlenecks.map((bn) => (
            <div key={bn.id} style={styles.bnItem}>
              <div style={styles.bnHeader}>
                {SEVERITY_ICONS[bn.severity]}
                <span style={{ ...styles.bnSeverity, color: SEVERITY_COLORS[bn.severity] }}>
                  {bn.severity.toUpperCase()}
                </span>
                <span style={styles.bnStage}>{bn.stage}</span>
                <span style={styles.bnValue}>{bn.value.toFixed(1)}ms</span>
              </div>
              <div style={styles.bnDesc}>{bn.description}</div>
              <div style={styles.bnSuggestion}>💡 {bn.suggestion}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Styles ─────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  container: {
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  subTabs: {
    display: 'flex',
    gap: 2,
    padding: '6px 12px',
    background: 'var(--bg-tertiary)',
    borderBottom: '1px solid var(--border)',
  },
  subTab: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '4px 12px',
    border: 'none',
    borderRadius: 4,
    background: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: 12,
    transition: 'all 0.15s',
  },
  subTabActive: {
    background: 'var(--accent)',
    color: '#fff',
  },
  viewContent: {
    flex: 1,
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
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
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
  totalRow: {
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 8,
    marginTop: 12,
    paddingTop: 12,
    borderTop: '1px solid var(--border)',
  },
  totalLabel: {
    fontSize: 12,
    color: 'var(--text-secondary)',
  },
  totalValue: {
    fontSize: 16,
    fontWeight: 700,
    fontFamily: 'monospace',
    color: 'var(--accent)',
  },

  // Resource view
  resourceGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: 12,
    marginBottom: 16,
  },
  gaugeCard: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: 14,
  },
  gaugeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  gaugeLabel: {
    fontSize: 13,
    fontWeight: 600,
  },
  gaugeValue: {
    fontSize: 18,
    fontWeight: 700,
    fontFamily: 'monospace',
    marginLeft: 'auto',
  },
  gaugeTrack: {
    height: 8,
    background: 'var(--bg-tertiary)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  gaugeFill: {
    height: '100%',
    borderRadius: 4,
  },
  sparklineContainer: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: 14,
    marginBottom: 16,
  },
  sparklineTitle: {
    fontSize: 12,
    color: 'var(--text-secondary)',
    marginBottom: 10,
  },
  sparkline: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 2,
    height: 80,
  },
  sparkBar: {
    flex: 1,
    borderRadius: '1px 1px 0 0',
    minWidth: 2,
    transition: 'height 0.3s',
  },
  memDetail: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: '10px 14px',
  },
  memRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 12,
    fontFamily: 'monospace',
  },

  // Flame view
  flameLegend: {
    marginBottom: 8,
  },
  flameContainer: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: 4,
    overflow: 'auto',
  },
  flameBlock: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    height: 28,
    borderRight: '1px solid rgba(0,0,0,0.2)',
    borderBottom: '1px solid rgba(0,0,0,0.1)',
    boxSizing: 'border-box' as const,
    overflow: 'hidden',
    whiteSpace: 'nowrap' as const,
    transition: 'filter 0.15s',
  },
  flameLabel: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    color: '#fff',
    textShadow: '0 1px 2px rgba(0,0,0,0.3)',
  },
  flameValue: {
    fontSize: 10,
    color: 'rgba(255,255,255,0.7)',
    fontFamily: 'monospace',
    marginLeft: 8,
    flexShrink: 0,
  },
  flameChildren: {
    display: 'flex',
  },

  // Bottleneck view
  bnSummary: {
    display: 'flex',
    gap: 24,
    marginBottom: 16,
  },
  bnSummaryItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '12px 24px',
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
  },
  bnEmpty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 40,
    color: 'var(--text-secondary)',
    fontSize: 14,
  },
  bnList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  bnItem: {
    background: 'var(--bg-secondary)',
    borderRadius: 8,
    border: '1px solid var(--border)',
    padding: 12,
  },
  bnHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  bnSeverity: {
    fontSize: 11,
    fontWeight: 700,
  },
  bnStage: {
    fontSize: 13,
    fontWeight: 600,
    textTransform: 'capitalize' as const,
  },
  bnValue: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: 'var(--text-secondary)',
    marginLeft: 'auto',
  },
  bnDesc: {
    fontSize: 12,
    color: 'var(--text-primary)',
    marginBottom: 4,
    marginLeft: 22,
  },
  bnSuggestion: {
    fontSize: 11,
    color: 'var(--text-secondary)',
    marginLeft: 22,
    fontStyle: 'italic',
  },
};
