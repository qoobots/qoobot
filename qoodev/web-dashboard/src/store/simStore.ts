import { create } from 'zustand';

// ── Types ──────────────────────────────────────────────

export interface JointState {
  position: number;
  velocity: number;
  torque: number;
}

export interface RobotState {
  name: string;
  basePose: {
    position: [number, number, number];
    rotation: [number, number, number, number];
  };
  joints: Record<string, JointState>;
  timestamp: number;
}

export interface ObjectPose {
  name: string;
  position: [number, number, number];
  rotation: [number, number, number, number];
}

export interface SimStats {
  simTime: number;
  totalSteps: number;
  realTimeFactor: number;
  stepTimeMs: number;
  physicsTimeMs: number;
  renderTimeMs: number;
}

export interface LogEntry {
  timestamp: number;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  message: string;
  source: string;
}

export interface SensorStats {
  name: string;
  type: string;
  count: number;
  shape: number[];
  min: number;
  max: number;
  mean: number;
  rateHz: number;
}

export interface LatencyStats {
  stage: string;
  count: number;
  meanMs: number;
  p95Ms: number;
  p99Ms: number;
}

export interface SceneSnapshot {
  timestamp: number;
  robots: Record<string, {
    basePose: { position: [number, number, number]; rotation: [number, number, number, number] };
    joints: Record<string, { position: number; velocity: number; torque: number }>;
    timestamp: number;
  }>;
  objects: Record<string, { position: [number, number, number]; rotation: [number, number, number, number] }>;
}

// ── Store ──────────────────────────────────────────────

interface SimStore {
  connected: boolean;
  simState: string;
  stats: SimStats;
  robotStates: Record<string, RobotState>;
  objectPoses: Record<string, ObjectPose>;
  logs: LogEntry[];
  sensorStats: SensorStats[];
  latencyStats: LatencyStats[];
  sceneSnapshot: SceneSnapshot | null;

  setConnected: (v: boolean) => void;
  setSimState: (s: string) => void;
  updateStats: (s: Partial<SimStats>) => void;
  updateScene: (snapshot: SceneSnapshot) => void;
  addLog: (entry: LogEntry) => void;
  setLogs: (entries: LogEntry[]) => void;
  updateSensorStats: (s: SensorStats[]) => void;
  updateLatencyStats: (s: LatencyStats[]) => void;
}

export const useSimStore = create<SimStore>((set) => ({
  connected: false,
  simState: 'STOPPED',
  stats: {
    simTime: 0,
    totalSteps: 0,
    realTimeFactor: 0,
    stepTimeMs: 0,
    physicsTimeMs: 0,
    renderTimeMs: 0,
  },
  robotStates: {},
  objectPoses: {},
  logs: [],
  sensorStats: [],
  latencyStats: [],
  sceneSnapshot: null,

  setConnected: (v) => set({ connected: v }),
  setSimState: (s) => set({ simState: s }),

  updateStats: (s) =>
    set((state) => ({ stats: { ...state.stats, ...s } })),

  updateScene: (snapshot) => {
    const robotStates: Record<string, RobotState> = {};
    const objectPoses: Record<string, ObjectPose> = {};

    if (snapshot.robots) {
      for (const [name, r] of Object.entries(snapshot.robots)) {
        robotStates[name] = {
          name,
          basePose: r.basePose,
          joints: r.joints || {},
          timestamp: r.timestamp,
        };
      }
    }

    if (snapshot.objects) {
      for (const [name, o] of Object.entries(snapshot.objects)) {
        objectPoses[name] = {
          name,
          position: o.position,
          rotation: o.rotation,
        };
      }
    }

    set({ robotStates, objectPoses, sceneSnapshot: snapshot });
  },

  addLog: (entry) =>
    set((state) => ({
      logs: [...state.logs.slice(-999), entry],
    })),

  setLogs: (entries) => set({ logs: entries }),

  updateSensorStats: (s) => set({ sensorStats: s }),
  updateLatencyStats: (s) => set({ latencyStats: s }),
}));
