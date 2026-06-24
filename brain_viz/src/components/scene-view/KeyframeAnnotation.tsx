/**
 * src/components/scene-view/KeyframeAnnotation.tsx — Keyframe annotations in 3D scene
 *
 * Renders numbered waypoint markers along trajectories with tooltip labels.
 */
'use client';

import React, { useMemo } from 'react';
import * as THREE from 'three';
import { Text } from '@react-three/drei';
import type { Waypoint } from '@/types/domain';
import { hexToRgb, STRATEGY_RGB } from '@/utils/colorMap';

interface KeyframeAnnotationProps {
  waypoints: Waypoint[];
  strategy: string;
  startIndex?: number;
  showLabels?: boolean;
  labelInterval?: number;
}

export function KeyframeAnnotation({
  waypoints,
  strategy,
  startIndex = 0,
  showLabels = true,
  labelInterval = 3,
}: KeyframeAnnotationProps) {
  const color = STRATEGY_RGB[strategy] || hexToRgb('#6366f1');

  const markers = useMemo(() => {
    return waypoints
      .filter((_, i) => i % labelInterval === 0 || i === waypoints.length - 1)
      .map((wp, filteredIdx) => ({
        position: new THREE.Vector3(wp.x, wp.y, wp.z),
        label: `${startIndex + filteredIdx * labelInterval}`,
        isEndpoint: filteredIdx === 0 || filteredIdx === waypoints.length / labelInterval - 1,
      }));
  }, [waypoints, startIndex, labelInterval]);

  // Sphere geometry for keyframe markers
  const markerGeo = useMemo(() => new THREE.SphereGeometry(0.03, 8, 8), []);
  const markerMat = useMemo(
    () => new THREE.MeshBasicMaterial({ color: new THREE.Color(color[0], color[1], color[2]) }),
    [color]
  );

  return (
    <group>
      {markers.map((m, i) => (
        <group key={`kf_${i}`}>
          <mesh geometry={markerGeo} material={markerMat} position={m.position} />
          {showLabels && (
            <Text
              position={[m.position.x, m.position.y + 0.08, m.position.z]}
              fontSize={0.06}
              color="#e8e8f0"
              anchorX="center"
              anchorY="bottom"
              outlineWidth={0.01}
              outlineColor="#0a0a1a"
            >
              {m.label}
            </Text>
          )}
        </group>
      ))}
    </group>
  );
}
