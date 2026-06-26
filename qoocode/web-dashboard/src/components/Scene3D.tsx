import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Grid, Stats as DreiStats } from '@react-three/drei';
import * as THREE from 'three';
import { useSimStore } from '../store/simStore';

export function Scene3D() {
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <Canvas
        camera={{ position: [5, 4, 6], fov: 50, near: 0.1, far: 100 }}
        shadows
        gl={{ antialias: true, alpha: false }}
        style={{ background: '#0d1117' }}
      >
        <ambientLight intensity={0.4} />
        <directionalLight
          position={[10, 15, 10]}
          intensity={0.8}
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <pointLight position={[-5, 5, 5]} intensity={0.3} />

        {/* 地面 */}
        <Grid
          position={[0, 0, 0]}
          args={[20, 20]}
          cellSize={0.5}
          cellThickness={0.5}
          cellColor="#1e293b"
          sectionSize={2}
          sectionThickness={1.5}
          sectionColor="#334155"
          fadeDistance={20}
          infiniteGrid
        />

        {/* 坐标轴 */}
        <axesHelper args={[2]} />

        {/* 场景物体 */}
        <SceneObjects />

        {/* 控制器 */}
        <OrbitControls
          enableDamping
          dampingFactor={0.1}
          minDistance={1}
          maxDistance={20}
        />

        {/* 性能统计 */}
        <DreiStats />
      </Canvas>

      {/* 叠加信息 */}
      <div style={styles.overlay}>
        <span style={styles.overlayText}>
          拖拽旋转 | 滚轮缩放 | 右键平移
        </span>
      </div>
    </div>
  );
}

function SceneObjects() {
  const robotStates = useSimStore((s) => s.robotStates);
  const objectPoses = useSimStore((s) => s.objectPoses);

  return (
    <group>
      {/* 机器人 */}
      {Object.entries(robotStates).map(([name, state]) => (
        <RobotModel
          key={name}
          name={name}
          position={state.basePose.position}
          joints={state.joints}
        />
      ))}

      {/* 物体 */}
      {Object.entries(objectPoses).map(([name, pose]) => (
        <mesh
          key={name}
          position={pose.position}
        >
          <boxGeometry args={[0.3, 0.3, 0.3]} />
          <meshStandardMaterial color="#475569" wireframe />
        </mesh>
      ))}
    </group>
  );
}

interface RobotModelProps {
  name: string;
  position: [number, number, number];
  joints: Record<string, { position: number; velocity: number; torque: number }>;
}

function RobotModel({ name, position, joints }: RobotModelProps) {
  const groupRef = useRef<THREE.Group>(null);
  const armRef = useRef<THREE.Group>(null);

  // 提取关节角度
  const jointValues = useMemo(() => {
    const values: number[] = [];
    const sorted = Object.entries(joints).sort(([a], [b]) => a.localeCompare(b));
    for (const [, state] of sorted) {
      values.push(state.position);
    }
    return values;
  }, [joints]);

  const j1 = jointValues[0] || 0;
  const j2 = jointValues[1] || 0;

  return (
    <group ref={groupRef} position={position}>
      {/* 基座 */}
      <mesh position={[0, 0, 0.1]}>
        <boxGeometry args={[0.5, 0.5, 0.1]} />
        <meshStandardMaterial color="#1e40af" />
      </mesh>

      {/* 底座旋转 */}
      <group rotation={[0, 0, j1]}>
        <mesh position={[0, 0, 0.25]}>
          <cylinderGeometry args={[0.12, 0.15, 0.2, 16]} />
          <meshStandardMaterial color="#2563eb" />
        </mesh>

        {/* 大臂 */}
        <group
          ref={armRef}
          position={[0, 0, 0.35]}
          rotation={[j2, 0, 0]}
        >
          <mesh position={[0, 0, 0.2]}>
            <boxGeometry args={[0.08, 0.08, 0.4]} />
            <meshStandardMaterial color="#3b82f6" />
          </mesh>

          {/* 小臂 */}
          <mesh position={[0, 0, 0.45]}>
            <boxGeometry args={[0.06, 0.06, 0.3]} />
            <meshStandardMaterial color="#60a5fa" />
          </mesh>

          {/* 末端执行器 */}
          <mesh position={[0, 0, 0.62]}>
            <boxGeometry args={[0.06, 0.06, 0.08]} />
            <meshStandardMaterial color="#f43f5e" />
          </mesh>
        </group>
      </group>

      {/* 名称标签 */}
      <sprite position={[0, 0, 1.0]} scale={[0.8, 0.3, 1]}>
        <spriteMaterial color="#fff" opacity={0.8} />
        {/* Text would go here with a proper text renderer */}
      </sprite>
    </group>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'absolute',
    bottom: 12,
    right: 12,
    zIndex: 10,
  },
  overlayText: {
    fontSize: 11,
    color: '#475569',
    fontFamily: 'monospace',
  },
};
