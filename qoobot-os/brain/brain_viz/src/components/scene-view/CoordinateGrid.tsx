/**
 * src/components/scene-view/CoordinateGrid.tsx — Ground grid + coordinate axes
 */
'use client';

import { Grid } from '@react-three/drei';

export function CoordinateGrid() {
  return (
    <>
      {/* Ground grid */}
      <Grid
        position={[0, 0, 0]}
        args={[2, 2]}
        cellSize={0.1}
        cellThickness={0.5}
        cellColor="#1e1e3a"
        sectionSize={0.5}
        sectionThickness={1}
        sectionColor="#2a2a4a"
        fadeDistance={10}
        infiniteGrid
      />

      {/* Simple axis lines */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([0, 0, 0, 0.3, 0, 0])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#ef4444" />
      </line>
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([0, 0, 0, 0, 0.3, 0])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#22c55e" />
      </line>
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([0, 0, 0, 0, 0, 0.3])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#3b82f6" />
      </line>
    </>
  );
}
