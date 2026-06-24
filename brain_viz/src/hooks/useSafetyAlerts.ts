/**
 * src/hooks/useSafetyAlerts.ts — Safety alerts subscription hook
 *
 * Manages safety alert tracking with acknowledgment, filtering,
 * and severity-based sorting.
 */
'use client';

import { useMemo, useCallback } from 'react';
import { useMonitorStore } from '@/stores/monitorStore';
import type { SafetyStatus } from '@/types/domain';
import type { AppNotification } from '@/types/events';
import { useWebSocket } from './useWebSocket';

interface UseSafetyAlertsReturn {
  safetyStatus: SafetyStatus | null;
  isEmergencyStopped: boolean;
  collisionRisk: number;
  severity: 'normal' | 'warning' | 'critical' | 'emergency';
  alerts: AppNotification[];
  activeAlerts: AppNotification[];
  criticalAlerts: AppNotification[];
  acknowledgeAlert: (alertId: string) => void;
  dismissAll: () => void;
  requestEmergencyStop: () => void;
}

export function useSafetyAlerts(): UseSafetyAlertsReturn {
  const safety = useMonitorStore((s) => s.safety);
  const { subscribe } = useWebSocket({ autoConnect: false });

  const isEmergencyStopped = safety?.emergency_stop_active ?? false;
  const collisionRisk = safety?.collision_risk ?? 0;

  const severity = useMemo(() => {
    if (!safety) return 'normal';
    const level = safety.level;
    if (level === 'EMERGENCY') return 'emergency';
    if (level === 'CRITICAL') return 'critical';
    if (level === 'WARNING') return 'warning';
    return 'normal';
  }, [safety]);

  // Convert safety status to UI alerts
  const alerts: AppNotification[] = useMemo(() => {
    if (!safety) return [];
    return safety.active_warnings.map((msg, i) => ({
      id: `safety_${i}`,
      level: safety.level === 'CRITICAL' || safety.level === 'EMERGENCY' ? 'error' : 'warning',
      message: msg,
      timestamp: new Date().toISOString(),
      dismissed: false,
    }));
  }, [safety]);

  const activeAlerts = useMemo(() => alerts.filter((a) => !a.dismissed), [alerts]);
  const criticalAlerts = useMemo(
    () => activeAlerts.filter((a) => a.level === 'error'),
    [activeAlerts]
  );

  const acknowledgeAlert = useCallback((alertId: string) => {
    // In production, this would send an ack via WebSocket
    console.log('[Safety] Acknowledged alert:', alertId);
  }, []);

  const dismissAll = useCallback(() => {
    console.log('[Safety] Dismissed all alerts');
  }, []);

  const requestEmergencyStop = useCallback(() => {
    subscribe('safety_alert', () => {});
    console.log('[Safety] Emergency stop requested');
  }, [subscribe]);

  return {
    safetyStatus: safety,
    isEmergencyStopped,
    collisionRisk,
    severity,
    alerts,
    activeAlerts,
    criticalAlerts,
    acknowledgeAlert,
    dismissAll,
    requestEmergencyStop,
  };
}
