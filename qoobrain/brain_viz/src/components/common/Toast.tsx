/**
 * src/components/common/Toast.tsx — Toast notification system
 */
'use client';

import React, { useEffect, useState, useCallback, createContext, useContext } from 'react';
import type { NotificationLevel } from '@/types/events';

interface ToastItem {
  id: string;
  level: NotificationLevel;
  message: string;
  detail?: string;
  durationMs?: number;
}

interface ToastContextValue {
  toast: (item: Omit<ToastItem, 'id'>) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let toastCounter = 0;

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (item: Omit<ToastItem, 'id'>) => {
      const id = `toast_${Date.now()}_${++toastCounter}`;
      const toast: ToastItem = { ...item, id };
      setToasts((prev) => [...prev, toast]);

      if (item.durationMs !== 0) {
        setTimeout(() => removeToast(id), item.durationMs ?? 4000);
      }
    },
    [removeToast]
  );

  const levelIcons: Record<NotificationLevel, string> = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };

  const levelClasses: Record<NotificationLevel, string> = {
    success: 'border-l-green-500 bg-green-500/10',
    error: 'border-l-red-500 bg-red-500/10',
    warning: 'border-l-yellow-500 bg-yellow-500/10',
    info: 'border-l-blue-500 bg-blue-500/10',
  };

  const levelTextColors: Record<NotificationLevel, string> = {
    success: 'text-green-400',
    error: 'text-red-400',
    warning: 'text-yellow-400',
    info: 'text-blue-400',
  };

  return (
    <ToastContext.Provider
      value={{
        toast: addToast,
        success: (msg) => addToast({ level: 'success', message: msg }),
        error: (msg) => addToast({ level: 'error', message: msg }),
        warning: (msg) => addToast({ level: 'warning', message: msg }),
        info: (msg) => addToast({ level: 'info', message: msg }),
      }}
    >
      {children}
      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`
              flex items-start gap-3 p-3 rounded-r-lg border-l-4 shadow-lg
              ${levelClasses[t.level]}
              animate-[slideIn_0.3s_ease-out]
            `}
            role="alert"
          >
            <span className={`text-lg font-bold ${levelTextColors[t.level]}`}>
              {levelIcons[t.level]}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-brain-text font-medium">{t.message}</p>
              {t.detail && <p className="text-xs text-brain-muted mt-0.5">{t.detail}</p>}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-brain-muted hover:text-brain-text flex-shrink-0"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <style jsx>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </ToastContext.Provider>
  );
}
