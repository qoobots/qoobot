/**
 * src/components/dashboard/Sidebar.tsx — Left sidebar navigation
 */
'use client';

import { MessageSquare, MousePointer2, Activity, Code2 } from 'lucide-react';
import { useUIStore } from '@/stores/uiStore';
import type { PanelId } from '@/stores/uiStore';

const navItems: { id: PanelId; label: string; icon: React.ReactNode }[] = [
  { id: 'chat',   label: '对话',   icon: <MessageSquare size={18} /> },
  { id: 'hitl',   label: 'HITL',  icon: <MousePointer2 size={18} /> },
  { id: 'status', label: '状态',   icon: <Activity size={18} /> },
  { id: 'dev',    label: '开发',   icon: <Code2 size={18} /> },
];

export function Sidebar() {
  const sidebarOpen  = useUIStore((s) => s.sidebarOpen);
  const activePanel  = useUIStore((s) => s.activePanel);
  const setActivePanel = useUIStore((s) => s.setActivePanel);

  if (!sidebarOpen) return null;

  return (
    <aside className="w-14 bg-brain-panel border-r border-brain-border flex flex-col items-center py-2 gap-1 shrink-0">
      {navItems.map((item) => (
        <button
          key={item.id}
          onClick={() => setActivePanel(item.id)}
          className={`w-10 h-10 flex items-center justify-center rounded-lg transition-colors duration-200
            ${activePanel === item.id
              ? 'bg-brain-accent/20 text-brain-accent'
              : 'text-brain-muted hover:text-brain-text hover:bg-brain-border/50'
            }`}
          title={item.label}
        >
          {item.icon}
        </button>
      ))}
    </aside>
  );
}
