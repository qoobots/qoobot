import React, { useRef, useEffect, useMemo, useState } from 'react';
import { useSimStore, LogEntry } from '../store/simStore';
import { Search, Filter, Download } from 'lucide-react';

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: '#64748b',
  INFO: '#e2e8f0',
  WARN: '#eab308',
  ERROR: '#ef4444',
  FATAL: '#dc2626',
};

export function LogPanel() {
  const logs = useSimStore((s) => s.logs);
  const [filter, setFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const filtered = useMemo(() => {
    return logs.filter((log) => {
      if (levelFilter && log.level !== levelFilter) return false;
      if (filter && !log.message.toLowerCase().includes(filter.toLowerCase())) return false;
      return true;
    });
  }, [logs, filter, levelFilter]);

  const exportLogs = () => {
    const text = logs.map((l) =>
      `[${new Date(l.timestamp * 1000).toISOString()}] [${l.level}] ${l.source ? `[${l.source}] ` : ''}${l.message}`
    ).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `qoodev-logs-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={styles.container}>
      {/* 工具栏 */}
      <div style={styles.toolbar}>
        <div style={styles.searchBox}>
          <Search size={14} style={{ opacity: 0.5 }} />
          <input
            style={styles.searchInput}
            placeholder="搜索日志..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <div style={styles.levelFilters}>
          {['', 'DEBUG', 'INFO', 'WARN', 'ERROR'].map((level) => (
            <button
              key={level}
              style={{
                ...styles.levelBtn,
                ...(levelFilter === level ? { background: 'var(--accent)', color: '#fff' } : {}),
              }}
              onClick={() => setLevelFilter(levelFilter === level ? '' : level)}
            >
              {level || 'ALL'}
            </button>
          ))}
        </div>
        <button style={styles.toolBtn} onClick={exportLogs} title="导出日志">
          <Download size={14} />
        </button>
      </div>

      {/* 日志列表 */}
      <div ref={scrollRef} style={styles.logList}>
        {filtered.length === 0 && (
          <div style={styles.empty}>暂无日志</div>
        )}
        {filtered.map((log, i) => (
          <div key={i} style={styles.logLine}>
            <span style={styles.logTime}>
              {new Date(log.timestamp * 1000).toLocaleTimeString('zh-CN', { hour12: false })}
            </span>
            <span style={{
              ...styles.logLevel,
              color: LEVEL_COLORS[log.level] || '#e2e8f0',
            }}>
              {log.level}
            </span>
            {log.source && (
              <span style={styles.logSource}>[{log.source}]</span>
            )}
            <span style={styles.logMessage}>{log.message}</span>
          </div>
        ))}
      </div>

      {/* 底部统计 */}
      <div style={styles.footer}>
        <span>共 {filtered.length} / {logs.length} 条</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 12px',
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border)',
    flexWrap: 'wrap' as const,
  },
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 8px',
    background: 'var(--bg-tertiary)',
    borderRadius: 6,
    flex: 1,
    maxWidth: 300,
  },
  searchInput: {
    background: 'none',
    border: 'none',
    outline: 'none',
    color: 'var(--text-primary)',
    fontSize: 12,
    width: '100%',
  },
  levelFilters: {
    display: 'flex',
    gap: 3,
  },
  levelBtn: {
    padding: '3px 8px',
    fontSize: 11,
    border: '1px solid var(--border)',
    borderRadius: 4,
    background: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
  },
  toolBtn: {
    padding: '4px 8px',
    border: '1px solid var(--border)',
    borderRadius: 4,
    background: 'transparent',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
  },
  logList: {
    flex: 1,
    overflow: 'auto',
    padding: '4px 0',
    fontFamily: 'monospace',
    fontSize: 12,
    lineHeight: '22px',
  },
  empty: {
    padding: 40,
    textAlign: 'center' as const,
    color: 'var(--text-secondary)',
  },
  logLine: {
    display: 'flex',
    gap: 8,
    padding: '0 12px',
    borderBottom: '1px solid rgba(30, 41, 59, 0.5)',
  },
  logTime: {
    color: '#64748b',
    flexShrink: 0,
  },
  logLevel: {
    flexShrink: 0,
    width: 42,
    fontWeight: 600,
    fontSize: 11,
  },
  logSource: {
    color: '#3b82f6',
    flexShrink: 0,
  },
  logMessage: {
    color: '#e2e8f0',
    wordBreak: 'break-all' as const,
  },
  footer: {
    padding: '6px 12px',
    fontSize: 11,
    color: 'var(--text-secondary)',
    borderTop: '1px solid var(--border)',
    background: 'var(--bg-secondary)',
  },
};
