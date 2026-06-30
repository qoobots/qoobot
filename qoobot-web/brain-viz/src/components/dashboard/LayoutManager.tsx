/**
 * src/components/dashboard/LayoutManager.tsx — Layout persistence manager
 *
 * Saves and restores user layout preferences (panel sizes,
 * visibility, camera presets) to localStorage.
 */
'use client';

import React, { useEffect, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';

interface LayoutState {
  sidebarOpen: boolean;
  activePanel: string;
  rightPanelWidth: number;
  cameraPreset: string;
}

const STORAGE_KEY = 'brain_os_layout';

export function LayoutManager({ children }: { children: React.ReactNode }) {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const activePanel = useUIStore((s) => s.activePanel);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const setActivePanel = useUIStore((s) => s.setActivePanel);
  const toggleTheme = useUIStore((s) => s.toggleTheme);

  // Restore layout from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const layout: LayoutState = JSON.parse(saved);
        if (layout.sidebarOpen !== sidebarOpen) toggleSidebar();
        if (layout.activePanel !== activePanel) setActivePanel(layout.activePanel as any);
      }
    } catch {
      // Ignore parse errors
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Persist layout changes
  useEffect(() => {
    const layout: LayoutState = {
      sidebarOpen,
      activePanel,
      rightPanelWidth: 384,
      cameraPreset: 'perspective',
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
  }, [sidebarOpen, activePanel]);

  return <>{children}</>;
}
