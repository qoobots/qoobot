/**
 * src/stores/uiStore.ts — UI state store (Zustand)
 */
import { create } from 'zustand';

type PanelId = 'chat' | 'hitl' | 'status' | 'dev';

interface UIStore {
  sidebarOpen: boolean;
  activePanel: PanelId;
  theme: 'dark' | 'light';
  toggleSidebar: () => void;
  setActivePanel: (panel: PanelId) => void;
  toggleTheme: () => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  activePanel: 'chat',
  theme: 'dark',

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setActivePanel: (panel) => set({ activePanel: panel }),
  toggleTheme: () => set((s) => ({ theme: s.theme === 'dark' ? 'light' : 'dark' })),
}));
