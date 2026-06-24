/**
 * src/components/dashboard/ThemeProvider.tsx — Theme provider component
 *
 * Manages dark/light theme switching and applies theme
 * to the document root.
 */
'use client';

import React, { useEffect, createContext, useContext, useState, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';

interface ThemeContextValue {
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  setTheme: (theme: 'dark' | 'light') => void;
  isDark: boolean;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'dark',
  toggleTheme: () => {},
  setTheme: () => {},
  isDark: true,
});

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const themeFromStore = useUIStore((s) => s.theme);
  const toggleThemeStore = useUIStore((s) => s.toggleTheme);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const stored = localStorage.getItem('brain_os_theme') as 'dark' | 'light' | null;
    if (stored && stored !== themeFromStore) {
      toggleThemeStore();
    }
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    if (themeFromStore === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
    localStorage.setItem('brain_os_theme', themeFromStore);
  }, [themeFromStore, mounted]);

  const setTheme = useCallback((theme: 'dark' | 'light') => {
    if (theme !== themeFromStore) {
      toggleThemeStore();
    }
  }, [themeFromStore, toggleThemeStore]);

  return (
    <ThemeContext.Provider
      value={{
        theme: themeFromStore,
        toggleTheme: toggleThemeStore,
        setTheme,
        isDark: themeFromStore === 'dark',
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}
