/**
 * src/hooks/useKeyboardControls.ts — Keyboard shortcuts hook
 *
 * Global keyboard shortcut handler for the Brain OS dashboard.
 * Maps keyboard combinations to UI actions.
 */
'use client';

import { useEffect, useCallback } from 'react';
import { useUIStore } from '@/stores/uiStore';
import { useTrajectoryStore } from '@/stores/trajectoryStore';
import type { KeyboardShortcut } from '@/types/events';
import { DEFAULT_SHORTCUTS } from '@/types/events';

interface UseKeyboardControlsOptions {
  shortcuts?: KeyboardShortcut[];
  enabled?: boolean;
}

interface UseKeyboardControlsReturn {
  registerShortcut: (shortcut: KeyboardShortcut, handler: () => void) => () => void;
  shortcuts: KeyboardShortcut[];
}

export function useKeyboardControls(
  options: UseKeyboardControlsOptions = {}
): UseKeyboardControlsReturn {
  const { enabled = true } = options;
  const shortcuts = options.shortcuts ?? DEFAULT_SHORTCUTS;

  const setActivePanel = useUIStore((s) => s.setActivePanel);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);
  const toggleGhost = useTrajectoryStore((s) => s.toggleGhostTrails);

  const executeAction = useCallback(
    (action: string) => {
      switch (action) {
        case 'panel:chat':
          setActivePanel('chat');
          break;
        case 'panel:hitl':
          setActivePanel('hitl');
          break;
        case 'panel:status':
          setActivePanel('status');
          break;
        case 'panel:dev':
          setActivePanel('dev');
          break;
        case 'toggle:ghost':
          toggleGhost();
          break;
        case 'cancel':
          // Generic cancel - handled by focused component
          break;
        case 'emergency_stop':
          console.log('[Keyboard] Emergency stop triggered');
          break;
        case 'toggle:sidebar':
          toggleSidebar();
          break;
      }
    },
    [setActivePanel, toggleGhost, toggleSidebar]
  );

  const registerShortcut = useCallback(
    (shortcut: KeyboardShortcut, handler: () => void): (() => void) => {
      // Custom shortcut registration (for dynamic use)
      return () => {
        // no-op cleanup
      };
    },
    []
  );

  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't capture when typing in input fields
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable
      ) {
        return;
      }

      for (const shortcut of shortcuts) {
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase() ||
          (shortcut.key === ' ' && e.key === ' ');
        const ctrlMatch = e.ctrlKey === shortcut.ctrlKey;
        const shiftMatch = e.shiftKey === shortcut.shiftKey;

        if (keyMatch && ctrlMatch && shiftMatch) {
          e.preventDefault();
          executeAction(shortcut.action);
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, shortcuts, executeAction]);

  return { registerShortcut, shortcuts };
}
