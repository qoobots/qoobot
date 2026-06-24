/**
 * src/components/dashboard/TopBar.tsx — Top navigation bar
 */
'use client';

import { Menu, Bot, Wifi, WifiOff } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import { useRobotStore } from '@/stores/robotStore';
import { SAFETY_COLORS, SAFETY_LABELS } from '@/types/enums';

export function TopBar() {
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const toggleTheme = useUIStore((s) => s.toggleTheme);
  const theme = useUIStore((s) => s.theme);
  const robotState = useRobotStore((s) => s.state);
  const connected = useRobotStore((s) => s.connected);

  const safetyLevel = robotState?.safety_level ?? 'NORMAL';
  const safetyColor = SAFETY_COLORS[safetyLevel];

  return (
    <header className="h-12 flex items-center justify-between px-4 bg-brain-panel border-b border-brain-border shrink-0">
      <div className="flex items-center gap-3">
        <button onClick={toggleSidebar} className="btn-ghost p-1">
          <Menu size={18} />
        </button>
        <div className="flex items-center gap-2">
          <Bot size={20} className="text-brain-accent" />
          <span className="font-mono font-bold text-sm tracking-wide">
            BRAIN OS
          </span>
          <span className="text-brain-muted text-xs">v0.1.0</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Connection status */}
        <div className="flex items-center gap-1.5 text-xs">
          {connected
            ? <Wifi size={14} className="text-brain-safe" />
            : <WifiOff size={14} className="text-brain-danger" />
          }
          <span className={connected ? 'text-brain-safe' : 'text-brain-danger'}>
            {connected ? '已连接' : '未连接'}
          </span>
        </div>

        {/* Safety indicator */}
        <div className="flex items-center gap-1.5 text-xs">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: safetyColor }}
          />
          <span style={{ color: safetyColor }}>
            {SAFETY_LABELS[safetyLevel]}
          </span>
        </div>

        {/* Theme toggle */}
        <button onClick={toggleTheme} className="btn-ghost text-xs">
          {theme === 'dark' ? '☀' : '☾'}
        </button>
      </div>
    </header>
  );
}
