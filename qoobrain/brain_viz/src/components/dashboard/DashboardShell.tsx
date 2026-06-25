/**
 * src/components/dashboard/DashboardShell.tsx — Main dashboard shell layout
 */
'use client';

import { TopBar } from './TopBar';
import { Sidebar } from './Sidebar';
import { useUIStore } from '@/stores/uiStore';

interface DashboardShellProps {
  children: React.ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);

  return (
    <div className="h-screen w-screen flex flex-col bg-brain-bg text-brain-text">
      {/* Top navigation bar */}
      <TopBar />

      <div className="flex-1 flex overflow-hidden">
        {/* Left sidebar */}
        <Sidebar />

        {/* Main content area */}
        <main className="flex-1 flex overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}
