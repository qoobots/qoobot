/**
 * src/stores/sceneStore.ts — 3D Scene store (Zustand)
 */
import { create } from 'zustand';
import type { SceneGraph, Object3D } from '@/types/domain';

interface SceneStore {
  scene: SceneGraph | null;
  selectedObject: Object3D | null;
  updateScene: (scene: SceneGraph) => void;
  selectObject: (object: Object3D | null) => void;
}

export const useSceneStore = create<SceneStore>((set) => ({
  scene: null,
  selectedObject: null,

  updateScene: (scene) => set({ scene }),
  selectObject: (object) => set({ selectedObject: object }),
}));
