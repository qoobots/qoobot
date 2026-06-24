/**
 * src/hooks/useSceneData.ts — Scene data subscription hook
 *
 * Provides reactive access to the 3D scene graph with
 * filtering and selection utilities.
 */
'use client';

import { useMemo, useCallback } from 'react';
import { useSceneStore } from '@/stores/sceneStore';
import type { SceneGraph, Object3D } from '@/types/domain';

interface UseSceneDataReturn {
  scene: SceneGraph | null;
  objects: Object3D[];
  selectedObject: Object3D | null;
  objectCount: number;
  hasScene: boolean;
  timestamp: string | null;
  robotPose: [number, number, number, number, number, number, number] | null;
  highConfidenceObjects: Object3D[];
  lowConfidenceObjects: Object3D[];
  selectObject: (object: Object3D | null) => void;
  getObjectsByLabel: (label: string) => Object3D[];
  getObjectById: (id: string) => Object3D | undefined;
  filterByConfidence: (minConfidence: number) => Object3D[];
}

const HIGH_CONFIDENCE = 0.7;
const LOW_CONFIDENCE = 0.3;

export function useSceneData(): UseSceneDataReturn {
  const scene = useSceneStore((s) => s.scene);
  const selectedObject = useSceneStore((s) => s.selectedObject);
  const selectObject = useSceneStore((s) => s.selectObject);

  const objects = useMemo(() => scene?.objects ?? [], [scene]);
  const objectCount = objects.length;
  const hasScene = scene !== null;
  const timestamp = scene?.timestamp ?? null;
  const robotPose = scene?.robot_pose ?? null;

  const highConfidenceObjects = useMemo(
    () => objects.filter((o) => o.confidence >= HIGH_CONFIDENCE),
    [objects]
  );

  const lowConfidenceObjects = useMemo(
    () => objects.filter((o) => o.confidence < LOW_CONFIDENCE),
    [objects]
  );

  const getObjectsByLabel = useCallback(
    (label: string): Object3D[] => {
      const lower = label.toLowerCase();
      return objects.filter((o) => o.label.toLowerCase().includes(lower));
    },
    [objects]
  );

  const getObjectById = useCallback(
    (id: string): Object3D | undefined => objects.find((o) => o.id === id),
    [objects]
  );

  const filterByConfidence = useCallback(
    (minConfidence: number): Object3D[] =>
      objects.filter((o) => o.confidence >= minConfidence),
    [objects]
  );

  return {
    scene,
    objects,
    selectedObject,
    objectCount,
    hasScene,
    timestamp,
    robotPose,
    highConfidenceObjects,
    lowConfidenceObjects,
    selectObject,
    getObjectsByLabel,
    getObjectById,
    filterByConfidence,
  };
}
