/**
 * src/components/scene-view/GSRenderer.tsx — 3D Gaussian Splatting renderer
 *
 * Renders a 3DGS point cloud from brain_ai reconstruction data.
 * Uses instanced Three.js spheres with varying opacity as a
 * lightweight approximation of Gaussian splats.
 */
'use client';

import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface GSData {
  positions: Float32Array;   // N * 3
  colors: Float32Array;      // N * 3 (RGB 0..1)
  opacities: Float32Array;   // N * 1
  scales: Float32Array;      // N * 3
}

interface GSRendererProps {
  data: GSData | null;
  maxSplats?: number;
}

export function GSRenderer({ data, maxSplats = 10000 }: GSRendererProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);

  const splatCount = data ? Math.min(data.positions.length / 3, maxSplats) : 0;

  const { geometry, material } = useMemo(() => {
    const geo = new THREE.SphereGeometry(0.01, 4, 4);
    const mat = new THREE.MeshStandardMaterial({
      roughness: 0.5,
      metalness: 0.1,
      vertexColors: true,
    });
    return { geometry: geo, material: mat };
  }, []);

  // Update instance matrices and colors on each frame
  useFrame(() => {
    if (!meshRef.current || !data || splatCount === 0) return;

    const dummy = new THREE.Matrix4();
    const color = new THREE.Color();

    for (let i = 0; i < splatCount; i++) {
      const idx = i * 3;
      const px = data.positions[idx];
      const py = data.positions[idx + 1];
      const pz = data.positions[idx + 2];

      // Scale from Gaussian scales
      const sx = data.scales ? data.scales[idx] * 2 : 0.02;
      const sy = data.scales ? data.scales[idx + 1] * 2 : 0.02;
      const sz = data.scales ? data.scales[idx + 2] * 2 : 0.02;

      dummy.identity();
      dummy.makeScale(Math.max(sx, 0.005), Math.max(sy, 0.005), Math.max(sz, 0.005));
      dummy.setPosition(px, py, pz);

      meshRef.current.setMatrixAt(i, dummy);

      color.setRGB(
        data.colors[idx],
        data.colors[idx + 1],
        data.colors[idx + 2]
      );
      meshRef.current.setColorAt(i, color);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  });

  if (splatCount === 0) return null;

  // Render as instanced spheres for lightweight visualization
  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, splatCount]}
      frustumCulled={false}
    />
  );
}
