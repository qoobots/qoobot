/**
 * src/stores/monitorStore.ts — System monitoring store (Zustand)
 *
 * Tracks real-time system health, logs, alerts, and performance metrics
 * for the Brain OS runtime. Used by StatusMonitor panel.
 */
import { create } from 'zustand';
import type { SafetyStatus, JointState } from '@/types/domain';

// ── Types ────────────────────────────────────────────────
export interface LogEntry {
  id: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';
  source: string;
  message: string;
  timestamp: string;
}

export interface MetricSample {
  timestamp: string;
  value: number;
}

export interface PerformanceMetrics {
  cpuPercent: number;
  memoryMB: number;
  gpuPercent: number;
  gpuMemoryMB: number;
  frameRate: number;
  gRPCLatencyMs: number;
  wsLatencyMs: number;
  history: {
    cpu: MetricSample[];
    memory: MetricSample[];
    gpu: MetricSample[];
    frameRate: MetricSample[];
  };
}

export interface ProcessInfo {
  name: string;
  pid: number;
  status: 'running' | 'stopped' | 'error';
  uptimeSec: number;
  cpuPercent: number;
  memoryMB: number;
  restartCount: number;
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'unhealthy';
  components: Record<string, 'ok' | 'warning' | 'error' | 'unknown'>;
  lastCheck: string;
}

// ── Store ────────────────────────────────────────────────
interface MonitorStore {
  // State
  safety: SafetyStatus | null;
  joints: JointState | null;
  logs: LogEntry[];
  metrics: PerformanceMetrics;
  processes: ProcessInfo[];
  health: SystemHealth;
  isRecording: boolean;

  // Actions
  setSafety: (safety: SafetyStatus) => void;
  setJoints: (joints: JointState) => void;
  addLog: (entry: LogEntry) => void;
  addLogs: (entries: LogEntry[]) => void;
  clearLogs: () => void;
  updateMetrics: (partial: Partial<PerformanceMetrics>) => void;
  appendMetricHistory: (
    key: 'cpu' | 'memory' | 'gpu' | 'frameRate',
    sample: MetricSample
  ) => void;
  setProcesses: (processes: ProcessInfo[]) => void;
  setHealth: (health: SystemHealth) => void;
  setRecording: (recording: boolean) => void;
}

let logCounter = 0;
function nextLogId(): string {
  return `log_${Date.now()}_${++logCounter}`;
}

const MAX_LOG_ENTRIES = 500;
const MAX_METRIC_SAMPLES = 120; // 2 minutes at 1Hz

function trimArray<T>(arr: T[], max: number): T[] {
  return arr.length > max ? arr.slice(arr.length - max) : arr;
}

export const useMonitorStore = create<MonitorStore>((set) => ({
  safety: null,
  joints: null,
  logs: [],
  metrics: {
    cpuPercent: 0,
    memoryMB: 0,
    gpuPercent: 0,
    gpuMemoryMB: 0,
    frameRate: 0,
    gRPCLatencyMs: 0,
    wsLatencyMs: 0,
    history: { cpu: [], memory: [], gpu: [], frameRate: [] },
  },
  processes: [],
  health: {
    overall: 'healthy',
    components: {},
    lastCheck: new Date().toISOString(),
  },
  isRecording: false,

  setSafety: (safety) => set({ safety }),
  setJoints: (joints) => set({ joints }),

  addLog: (entry) =>
    set((s) => ({
      logs: trimArray([...s.logs, entry], MAX_LOG_ENTRIES),
    })),

  addLogs: (entries) =>
    set((s) => ({
      logs: trimArray([...s.logs, ...entries], MAX_LOG_ENTRIES),
    })),

  clearLogs: () => set({ logs: [] }),

  updateMetrics: (partial) =>
    set((s) => ({
      metrics: { ...s.metrics, ...partial },
    })),

  appendMetricHistory: (key, sample) =>
    set((s) => ({
      metrics: {
        ...s.metrics,
        history: {
          ...s.metrics.history,
          [key]: trimArray([...s.metrics.history[key], sample], MAX_METRIC_SAMPLES),
        },
      },
    })),

  setProcesses: (processes) => set({ processes }),
  setHealth: (health) => set({ health }),
  setRecording: (recording) => set({ isRecording }),
}));
