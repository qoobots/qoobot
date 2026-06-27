import React from 'react';
import { useSimStore } from '../store/simStore';
import { Bot, Box, Eye } from 'lucide-react';

export function Sidebar() {
  const robotStates = useSimStore((s) => s.robotStates);
  const objectPoses = useSimStore((s) => s.objectPoses);

  return (
    <div style={styles.sidebar}>
      <div style={styles.header}>场景层次</div>

      {/* 机器人 */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <Bot size={14} />
          <span>机器人 ({Object.keys(robotStates).length})</span>
        </div>
        {Object.entries(robotStates).map(([name, state]) => (
          <div key={name} style={styles.item}>
            <Eye size={12} style={{ opacity: 0.5 }} />
            <span style={styles.itemName}>{name}</span>
            <span style={styles.itemBadge}>
              {Object.keys(state.joints).length} 关节
            </span>
          </div>
        ))}
      </div>

      {/* 物体 */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <Box size={14} />
          <span>物体 ({Object.keys(objectPoses).length})</span>
        </div>
        {Object.entries(objectPoses).map(([name]) => (
          <div key={name} style={styles.item}>
            <Box size={12} style={{ opacity: 0.5 }} />
            <span style={styles.itemName}>{name}</span>
          </div>
        ))}
      </div>

      {/* 摄像机 */}
      <div style={styles.section}>
        <div style={styles.sectionTitle}>
          <Eye size={14} />
          <span>摄像机</span>
        </div>
        <div style={styles.item}>
          <Eye size={12} style={{ opacity: 0.5 }} />
          <span style={styles.itemName}>默认视角</span>
        </div>
        <div style={styles.item}>
          <Eye size={12} style={{ opacity: 0.5 }} />
          <span style={styles.itemName}>俯视</span>
        </div>
        <div style={styles.item}>
          <Eye size={12} style={{ opacity: 0.5 }} />
          <span style={styles.itemName}>机器人视角</span>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  sidebar: {
    width: 220,
    background: 'var(--bg-secondary)',
    borderRight: '1px solid var(--border)',
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
  },
  header: {
    padding: '10px 14px',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
    color: 'var(--text-secondary)',
    borderBottom: '1px solid var(--border)',
  },
  section: {
    padding: '8px 0',
    borderBottom: '1px solid var(--border)',
  },
  sectionTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 14px',
    fontSize: 12,
    fontWeight: 600,
    color: 'var(--text-secondary)',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 14px 4px 24px',
    fontSize: 12,
    cursor: 'pointer',
    transition: 'background 0.1s',
  },
  itemName: {
    flex: 1,
  },
  itemBadge: {
    fontSize: 10,
    color: 'var(--text-secondary)',
    background: 'var(--bg-tertiary)',
    padding: '1px 6px',
    borderRadius: 3,
  },
};
