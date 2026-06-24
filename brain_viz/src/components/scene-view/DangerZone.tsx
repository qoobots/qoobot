/**
 * src/components/scene-view/DangerZone.tsx — Workspace danger zone visualization
 *
 * Renders a translucent red zone around the robot when safety
 * is at CRITICAL or EMERGENCY level.
 */
'use client';

import React, { useMemo } from 'react';
import * as THREE from 'three';
import { useMonitorStore } from '@/stores/monitorStore';
import { useRobotStore } from '@/stores/robotStore';

export function DangerZone() {
  const safety = useMonitorStore((s) => s.safety);
  const robotState = useRobotStore((s) => s.state);
  const emergencyStop = robotState?.emergency_stop ?? false;

  const isActive = safety?.level === 'CRITICAL' || safety?.level === 'EMERGENCY' || emergencyStop;

  const zoneGeometry = useMemo(() => new THREE.CylinderGeometry(0.5, 0.5, 1.5, 32), []);

  if (!isActive) return null;

  const color = emergencyStop ? '#dc2626' : '#ef4444';
  const opacity = emergencyStop ? 0.35 : 0.15;

  return (
    <mesh
      position={[0, 0.75, 0.3]}
      geometry={zoneGeometry}
      renderOrder={1}
    >
      <meshBasicMaterial
        color={color}
        transparent
        opacity={opacity}
        depthWrite={false}
        side={THREE.DoubleSide}
      />
    </mesh>
  );
}
