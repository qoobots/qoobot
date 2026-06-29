/**
 * src/components/scene-view/TrajectoryHighlight.tsx — Animated trajectory highlight
 *
 * Renders an animated "particle" traveling along the selected trajectory
 * to help the user visualize the robot's planned path.
 */
'use client';

import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';
import { CatmullRomCurve3, TubeGeometry } from 'three';
import type { Trajectory } from '@/types/domain';
import { hexToRgb, STRATEGY_RGB } from '@/utils/colorMap';

interface TrajectoryHighlightProps {
  trajectory: Trajectory | null;
  animate?: boolean;
  tubeRadius?: number;
  particleSpeed?: number;
}

export function TrajectoryHighlight({
  trajectory,
  animate = true,
  tubeRadius = 0.01,
  particleSpeed = 0.5,
}: TrajectoryHighlightProps) {
  const particleRef = useRef<THREE.Mesh>(null);
  const progressRef = useRef(0);

  const color = trajectory
    ? STRATEGY_RGB[trajectory.strategy] || hexToRgb('#6366f1')
    : hexToRgb('#6366f1');

  const curve = useMemo(() => {
    if (!trajectory || trajectory.waypoints.length < 2) return null;
    const points = trajectory.waypoints.map(
      (wp) => new THREE.Vector3(wp.x, wp.y, wp.z)
    );
    return new CatmullRomCurve3(points);
  }, [trajectory]);

  const tubeGeo = useMemo(() => {
    if (!curve) return null;
    return new TubeGeometry(curve, 64, tubeRadius, 8, false);
  }, [curve, tubeRadius]);

  const particleGeo = useMemo(() => new THREE.SphereGeometry(0.04, 8, 8), []);
  const particleMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: new THREE.Color(color[0], color[1], color[2]),
        emissive: new THREE.Color(color[0], color[1], color[2]),
        emissiveIntensity: 1.5,
      }),
    [color]
  );

  // Animate the particle along the curve
  useFrame((_, delta) => {
    if (!particleRef.current || !curve || !animate) return;

    progressRef.current += delta * particleSpeed;
    if (progressRef.current > 1) progressRef.current = 0;

    const pt = curve.getPointAt(progressRef.current);
    particleRef.current.position.copy(pt);
  });

  if (!trajectory || !curve) return null;

  return (
    <group>
      {/* Transparent tube along trajectory */}
      {tubeGeo && (
        <mesh geometry={tubeGeo}>
          <meshBasicMaterial
            color={new THREE.Color(color[0], color[1], color[2])}
            transparent
            opacity={0.3}
            depthWrite={false}
          />
        </mesh>
      )}
      {/* Animated particle */}
      {animate && (
        <mesh ref={particleRef} geometry={particleGeo} material={particleMat} />
      )}
    </group>
  );
}
