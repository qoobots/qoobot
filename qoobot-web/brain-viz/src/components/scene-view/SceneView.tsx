/**
 * src/components/scene-view/SceneView.tsx — Main 3D scene viewport
 *
 * Renders the robot workspace using Three.js via @react-three/fiber.
 * Shows: robot model, detected objects, ghost trails, danger zones.
 */
'use client';

import { Suspense, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Grid, GizmoHelper, GizmoViewport } from '@react-three/drei';
import { SceneLighting } from './SceneLighting';
import { CoordinateGrid } from './CoordinateGrid';
import { GhostTrail } from './GhostTrail';
import { useTrajectoryStore } from '@/stores/trajectoryStore';
import { useSceneStore } from '@/stores/sceneStore';

function SceneContent() {
  const trajectories = useTrajectoryStore((s) => s.trajectories);
  const scene = useSceneStore((s) => s.scene);

  return (
    <>
      <SceneLighting />
      <CoordinateGrid />

      {/* Render ghost trails */}
      {trajectories.map((traj) => (
        <GhostTrail key={traj.id} trajectory={traj} />
      ))}

      {/* Robot base reference */}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[0.2, 0.02, 0.2]} />
        <meshStandardMaterial color="#6366f1" />
      </mesh>

      {/* Detected objects */}
      {scene?.objects.map((obj) => (
        <mesh key={obj.id} position={obj.centroid}>
          <boxGeometry args={[0.05, 0.05, 0.05]} />
          <meshStandardMaterial color="#22c55e" wireframe />
        </mesh>
      ))}
    </>
  );
}

export function SceneView() {
  return (
    <div className="w-full h-full relative">
      <Canvas
        camera={{ position: [2, 1.5, 2], fov: 50, near: 0.01, far: 50 }}
        shadows
      >
        <Suspense fallback={null}>
          <SceneContent />
          <OrbitControls
            enableDamping
            dampingFactor={0.1}
            target={[0.3, 0.2, 0.3]}
          />
          <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
            <GizmoViewport axisColors={['#ef4444', '#22c55e', '#3b82f6']} />
          </GizmoHelper>
        </Suspense>
      </Canvas>

      {/* Overlay: No connection placeholder */}
      <div className="absolute bottom-4 left-4 text-xs text-brain-muted bg-brain-panel/80 px-2 py-1 rounded">
        Three.js Scene · Brain OS
      </div>
    </div>
  );
}
