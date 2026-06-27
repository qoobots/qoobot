import React, { useState } from 'react';
import { Scene3D } from './components/Scene3D';
import { Sidebar } from './components/Sidebar';
import { StatusBar } from './components/StatusBar';
import { LogPanel } from './components/LogPanel';
import { SensorPanel } from './components/SensorPanel';
import { ProfilerPanel } from './components/ProfilerPanel';
import { useSimStore } from './store/simStore';
import { Activity, Camera, BarChart3, Terminal } from 'lucide-react';

type TabId = 'scene' | 'logs' | 'sensors' | 'profiler';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const tabs: Tab[] = [
  { id: 'scene', label: '3D 场景', icon: <Camera size={16} /> },
  { id: 'logs', label: '日志', icon: <Terminal size={16} /> },
  { id: 'sensors', label: '传感器', icon: <Activity size={16} /> },
  { id: 'profiler', label: '性能', icon: <BarChart3 size={16} /> },
];

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('scene');
  const isConnected = useSimStore((s) => s.connected);

  return (
    <div style={styles.container}>
      {/* 顶部状态栏 */}
      <StatusBar connected={isConnected} />

      <div style={styles.main}>
        {/* 左侧边栏 */}
        <Sidebar />

        {/* 中央面板 */}
        <div style={styles.center}>
          {/* Tab 导航 */}
          <div style={styles.tabs}>
            {tabs.map((tab) => (
              <button
                key={tab.id}
                style={{
                  ...styles.tab,
                  ...(activeTab === tab.id ? styles.tabActive : {}),
                }}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>

          {/* Tab 内容 */}
          <div style={styles.tabContent}>
            {activeTab === 'scene' && <Scene3D />}
            {activeTab === 'logs' && <LogPanel />}
            {activeTab === 'sensors' && <SensorPanel />}
            {activeTab === 'profiler' && <ProfilerPanel />}
          </div>
        </div>

        {/* 右侧面板 */}
        <div style={styles.rightPanel}>
          <div style={styles.panelTitle}>实时数据</div>
          <LiveDataPanel />
        </div>
      </div>
    </div>
  );
}

function LiveDataPanel() {
  const stats = useSimStore((s) => s.stats);
  const robotStates = useSimStore((s) => s.robotStates);

  return (
    <div style={styles.liveData}>
      {/* 仿真统计 */}
      <div style={styles.dataSection}>
        <div style={styles.dataLabel}>仿真时间</div>
        <div style={styles.dataValue}>{stats.simTime.toFixed(2)}s</div>
      </div>
      <div style={styles.dataSection}>
        <div style={styles.dataLabel}>实时因子</div>
        <div style={{
          ...styles.dataValue,
          color: stats.realTimeFactor >= 0.9 ? 'var(--success)' : 'var(--warning)',
        }}>
          {stats.realTimeFactor.toFixed(2)}x
        </div>
      </div>
      <div style={styles.dataSection}>
        <div style={styles.dataLabel}>总步数</div>
        <div style={styles.dataValue}>{stats.totalSteps.toLocaleString()}</div>
      </div>
      <div style={styles.dataSection}>
        <div style={styles.dataLabel}>步进耗时</div>
        <div style={styles.dataValue}>{stats.stepTimeMs.toFixed(2)}ms</div>
      </div>

      {/* 机器人状态 */}
      {Object.entries(robotStates).map(([name, state]) => (
        <div key={name} style={styles.robotSection}>
          <div style={styles.robotName}>{name}</div>
          {Object.entries(state.joints).slice(0, 6).map(([jName, jState]) => (
            <div key={jName} style={styles.jointRow}>
              <span style={styles.jointName}>{jName}</span>
              <span style={styles.jointValue}>
                {jState.position.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    width: '100vw',
  },
  main: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },
  center: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  tabs: {
    display: 'flex',
    gap: 2,
    padding: '8px 12px',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border)',
  },
  tab: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 14px',
    border: 'none',
    borderRadius: 6,
    background: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: 13,
    transition: 'all 0.15s',
  },
  tabActive: {
    background: 'var(--accent)',
    color: '#fff',
  },
  tabContent: {
    flex: 1,
    overflow: 'hidden',
  },
  rightPanel: {
    width: 260,
    background: 'var(--bg-secondary)',
    borderLeft: '1px solid var(--border)',
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
  },
  panelTitle: {
    padding: '10px 14px',
    fontSize: 12,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
    color: 'var(--text-secondary)',
    borderBottom: '1px solid var(--border)',
  },
  liveData: {
    padding: 8,
  },
  dataSection: {
    padding: '8px 6px',
    borderBottom: '1px solid var(--border)',
  },
  dataLabel: {
    fontSize: 11,
    color: 'var(--text-secondary)',
    marginBottom: 2,
  },
  dataValue: {
    fontSize: 18,
    fontWeight: 600,
    fontVariantNumeric: 'tabular-nums' as const,
  },
  robotSection: {
    marginTop: 12,
    padding: '8px 6px',
    background: 'var(--bg-tertiary)',
    borderRadius: 6,
  },
  robotName: {
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--accent)',
    marginBottom: 6,
  },
  jointRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '3px 0',
    fontSize: 12,
  },
  jointName: {
    color: 'var(--text-secondary)',
    fontFamily: 'monospace',
  },
  jointValue: {
    fontFamily: 'monospace',
    fontVariantNumeric: 'tabular-nums' as const,
  },
};
