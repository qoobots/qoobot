/**
 * src/utils/ros2three.ts — ROS 2 coordinate conversions to Three.js
 *
 * ROS uses:  x=forward, y=left, z=up (right-handed)
 * Three.js:  x=right, y=up, z=forward (right-handed, Y-up)
 *
 * Conversion: ROS(x,y,z) → Three(x=-y, y=z, z=x)
 */

import * as THREE from 'three';

// ── Position Conversion ──────────────────────────────────
/**
 * Convert ROS 2 position to Three.js position.
 * ROS (forward, left, up) → Three (right, up, forward)
 */
export function rosPositionToThree(ros: { x: number; y: number; z: number }): THREE.Vector3 {
  return new THREE.Vector3(-ros.y, ros.z, ros.x);
}

/** Batch convert an array of ROS positions to Three.js positions. */
export function rosPositionsToThree(
  positions: { x: number; y: number; z: number }[]
): THREE.Vector3[] {
  return positions.map(rosPositionToThree);
}

// ── Orientation Conversion ───────────────────────────────
/**
 * Convert ROS quaternion to Three.js quaternion.
 * ROS (x,y,z,w) → Three (-y, z, x, w)
 */
export function rosQuatToThree(
  ros: { x: number; y: number; z: number; w: number }
): THREE.Quaternion {
  return new THREE.Quaternion(-ros.y, ros.z, ros.x, ros.w);
}

/**
 * Convert ROS Euler angles (ZYX intrinsic) to Three.js Euler.
 * ROS typically uses roll-pitch-yaw around XYZ.
 * Three needs Y-up adaptation.
 */
export function rosEulerToThree(
  roll: number, pitch: number, yaw: number
): THREE.Euler {
  // ROS: roll(X), pitch(Y), yaw(Z)
  // Three: -pitch(Y), yaw(Z), roll(X) ... with Y-up rotation
  return new THREE.Euler(yaw, roll, -pitch, 'ZYX');
}

// ── Pose Conversion ──────────────────────────────────────
export interface ROSPose {
  position: { x: number; y: number; z: number };
  orientation?: { x: number; y: number; z: number; w: number };
}

/** Convert a full ROS pose to Three.js Matrix4. */
export function rosPoseToMatrix4(pose: ROSPose): THREE.Matrix4 {
  const pos = rosPositionToThree(pose.position);
  const quat = pose.orientation
    ? rosQuatToThree(pose.orientation)
    : new THREE.Quaternion();
  const m = new THREE.Matrix4();
  m.compose(pos, quat, new THREE.Vector3(1, 1, 1));
  return m;
}

// ── Bounding Box Conversion ──────────────────────────────
/** Convert ROS 3D bounding box corners to Three.js corners. */
export function rosBBoxCornersToThree(
  corners: [number, number, number][]
): THREE.Vector3[] {
  return corners.map(([x, y, z]) => rosPositionToThree({ x, y, z }));
}

// ── Occupancy Grid Conversion ────────────────────────────
export interface ROSOccupancyGrid {
  data: number[];       // flattened row-major [z * height * width + y * width + x]
  width: number;
  height: number;
  depth?: number;
  resolution: number;
  origin: ROSPose;
}

/** Convert ROS occupancy grid to a Three.js Group of cubes. */
export function rosOccupancyToMeshGroup(
  grid: ROSOccupancyGrid,
  threshold = 50  // occupancy > 50% = occupied
): THREE.Group {
  const group = new THREE.Group();
  const res = grid.resolution;
  const origin = rosPositionToThree(grid.origin.position);
  const depth = grid.depth || 1;

  for (let z = 0; z < depth; z++) {
    for (let y = 0; y < grid.height; y++) {
      for (let x = 0; x < grid.width; x++) {
        const idx = z * grid.height * grid.width + y * grid.width + x;
        if (grid.data[idx] > threshold) {
          const cube = new THREE.Mesh(
            new THREE.BoxGeometry(res * 0.9, res * 0.9, res * 0.9),
            new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: grid.data[idx] / 100 })
          );
          cube.position.copy(origin).add(new THREE.Vector3(
            x * res - (grid.width * res) / 2,
            y * res - (grid.height * res) / 2,
            z * res - (depth * res) / 2
          ));
          group.add(cube);
        }
      }
    }
  }
  return group;
}

// ── Scale Conversion ─────────────────────────────────────
/** Default ROS → Three scaling (meters to units, typically 1:1). */
export const ROS_SCALE = 1.0;

/** Scale a ROS dimension to Three.js units. */
export function rosScale(value: number): number {
  return value * ROS_SCALE;
}

/** Convert a ROS Vector3 dimension to Three.js scale. */
export function rosDimToThree(ros: { x: number; y: number; z: number }): THREE.Vector3 {
  return new THREE.Vector3(ros.y * ROS_SCALE, ros.z * ROS_SCALE, ros.x * ROS_SCALE);
}

// ── Coordinate Axis Helper ───────────────────────────────
/** Get the unit axis vectors in Three.js space corresponding to ROS axes. */
export const ROS_AXES_IN_THREE = {
  x: new THREE.Vector3(0, 0, 1),   // ROS forward → Three +Z
  y: new THREE.Vector3(-1, 0, 0),  // ROS left → Three -X
  z: new THREE.Vector3(0, 1, 0),   // ROS up → Three +Y
} as const;
