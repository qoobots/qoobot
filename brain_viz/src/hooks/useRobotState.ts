/**
 * src/hooks/useRobotState.ts — Robot state subscription hook
 *
 * Provides reactive access to robot state with derived values
 * (joint limits, gripper status, kinematic chain status).
 */
'use client';

import { useCallback, useMemo } from 'react';
import { useRobotStore } from '@/stores/robotStore';
import type { RobotState, SafetyLevel, JointState } from '@/types/domain';

interface UseRobotStateReturn {
  robotState: RobotState | null;
  connected: boolean;
  joints: JointState | null;
  gripperPosition: number;
  safetyLevel: SafetyLevel;
  isEmergencyStopped: boolean;
  isGripperOpen: boolean;
  isGripperClosed: boolean;
  jointCount: number;
  jointNames: string[];
  jointPositionsDeg: number[];
  hasJointsAtLimit: boolean;
  setConnected: (connected: boolean) => void;
  requestEmergencyStop: () => void;
  releaseEmergencyStop: () => void;
}

const JOINT_LIMIT_THRESHOLD_DEG = 1.0; // within 1° of limit
const GRIPPER_OPEN_THRESHOLD = 0.8;
const GRIPPER_CLOSED_THRESHOLD = 0.2;

export function useRobotState(): UseRobotStateReturn {
  const robotState = useRobotStore((s) => s.state);
  const connected = useRobotStore((s) => s.connected);
  const setConnected = useRobotStore((s) => s.setConnected);
  const setSafety = useRobotStore((s) => s.setSafetyLevel);
  const setEmergency = useRobotStore((s) => s.setEmergencyStop);

  // Derived state
  const joints = useMemo(() => robotState?.joints ?? null, [robotState]);
  const gripperPosition = robotState?.gripper_position ?? 0;
  const safetyLevel = robotState?.safety_level ?? 'NORMAL';
  const isEmergencyStopped = robotState?.emergency_stop ?? false;

  const isGripperOpen = gripperPosition > GRIPPER_OPEN_THRESHOLD;
  const isGripperClosed = gripperPosition < GRIPPER_CLOSED_THRESHOLD;

  const jointCount = joints?.names.length ?? 0;
  const jointNames = joints?.names ?? [];

  const jointPositionsDeg = useMemo(
    () => (joints?.positions ?? []).map((rad) => (rad * 180) / Math.PI),
    [joints?.positions]
  );

  const hasJointsAtLimit = false; // Requires joint limit config from URDF

  const requestEmergencyStop = useCallback(() => {
    setSafety('EMERGENCY');
    setEmergency(true);
  }, [setSafety, setEmergency]);

  const releaseEmergencyStop = useCallback(() => {
    setSafety('NORMAL');
    setEmergency(false);
  }, [setSafety, setEmergency]);

  return {
    robotState,
    connected,
    joints,
    gripperPosition,
    safetyLevel,
    isEmergencyStopped,
    isGripperOpen,
    isGripperClosed,
    jointCount,
    jointNames,
    jointPositionsDeg,
    hasJointsAtLimit,
    setConnected,
    requestEmergencyStop,
    releaseEmergencyStop,
  };
}
