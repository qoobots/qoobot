/**
 * src/components/scene-view/SceneLighting.tsx — Scene lighting setup
 */
'use client';

export function SceneLighting() {
  return (
    <>
      <ambientLight intensity={0.3} />
      <directionalLight
        position={[5, 8, 5]}
        intensity={0.8}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <pointLight position={[-2, 3, -2]} intensity={0.3} color="#6366f1" />
    </>
  );
}
