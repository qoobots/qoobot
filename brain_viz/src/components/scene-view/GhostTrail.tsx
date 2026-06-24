/**
 * src/components/scene-view/GhostTrail.tsx — Renders a semi-transparent trajectory trail
 *
 * Sprint 1: Simple line rendering.
 * Sprint 5: Full ghost trail with animated flow, keyframe annotations.
 */
'use client';

import { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { Line } from '@react-three/drei';
import type { Trajectory } from '@/types/domain';
import { STRATEGY_COLORS } from '@/types/enums';
import { useTrajectoryStore } from '@/stores/trajectoryStore';

interface GhostTrailProps {
  trajectory: Trajectory;
}

export function GhostTrail({ trajectory }: GhostTrailProps) {
  const selectedId = useTrajectoryStore((s) => s.selectedId);
  const isSelected = selectedId === trajectory.id;
  const color = STRATEGY_COLORS[trajectory.strategy];
  const opacity = isSelected ? 0.8 : 0.3;

  const points = useMemo(() => {
    if (!trajectory.waypoints?.length) {
      // Default demo points
      return [
        new THREE.Vector3(0, 0.15, 0),
        new THREE.Vector3(0.1, 0.2, 0.05),
        new THREE.Vector3(0.2, 0.25, 0.1),
        new THREE.Vector3(0.3, 0.3, 0.15),
      ];
    }
    return trajectory.waypoints.map(
      (wp) => new THREE.Vector3(wp.x, wp.y, wp.z)
    );
  }, [trajectory.waypoints]);

  return (
    <Line
      points={points}
      color={color}
      lineWidth={isSelected ? 3 : 1.5}
      opacity={opacity}
      transparent
      dashed={!isSelected}
    />
  );
}
