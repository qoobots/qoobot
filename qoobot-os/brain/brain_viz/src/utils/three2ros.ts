/**
 * src/utils/three2ros.ts — Three.js coordinate conversions to ROS 2
 *
 * Inverse of ros2three.ts.
 * Three.js: x=right, y=up, z=forward
 * ROS 2:    x=forward, y=left, z=up
 *
 * Conversion: Three(x,y,z) → ROS(x=z, y=-x, z=y)
 */

import * as THREE from 'three';

// ── Position Conversion ──────────────────────────────────
/**
 * Convert Three.js position to ROS 2 position.
 * Three (right, up, forward) → ROS (forward, left, up)
 */
export function threePositionToROS(
  three: THREE.Vector3 | { x: number; y: number; z: number }
): { x: number; y: number; z: number } {
  return { x: three.z, y: -three.x, z: three.y };
}

// ── Orientation Conversion ───────────────────────────────
/**
 * Convert Three.js quaternion to ROS quaternion.
 * Three (x,y,z,w) → ROS (z, -x, y, w)
 */
export function threeQuatToROS(
  quat: THREE.Quaternion | { x: number; y: number; z: number; w: number }
): { x: number; y: number; z: number; w: number } {
  return { x: quat.z, y: -quat.x, z: quat.y, w: quat.w };
}

// ── Euler Conversion ─────────────────────────────────────
/**
 * Convert Three.js Euler angles to ROS roll-pitch-yaw.
 */
export function threeEulerToROS(euler: THREE.Euler): {
  roll: number; pitch: number; yaw: number;
} {
  return { roll: euler.y, pitch: -euler.z, yaw: euler.x };
}

// ── Pose Conversion ──────────────────────────────────────
export interface ROSOutputPose {
  position: { x: number; y: number; z: number };
  orientation: { x: number; y: number; z: number; w: number };
}

/** Convert a Three.js Matrix4 to a ROS pose. */
export function matrix4ToROSPose(m: THREE.Matrix4): ROSOutputPose {
  const pos = new THREE.Vector3();
  const quat = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  m.decompose(pos, quat, scale);
  return {
    position: threePositionToROS(pos),
    orientation: threeQuatToROS(quat),
  };
}

/** Convert Three.js position + quaternion to ROS pose. */
export function toROSPose(
  position: THREE.Vector3,
  quaternion: THREE.Quaternion
): ROSOutputPose {
  return {
    position: threePositionToROS(position),
    orientation: threeQuatToROS(quaternion),
  };
}

// ── Waypoint Conversion ──────────────────────────────────
export interface ROSWaypoint {
  position: { x: number; y: number; z: number };
  orientation?: { x: number; y: number; z: number; w: number };
}

/** Convert an array of Three.js points to ROS waypoints. */
export function threePointsToROSWaypoints(
  points: THREE.Vector3[],
  defaultOrientation?: THREE.Quaternion
): ROSWaypoint[] {
  const orient = defaultOrientation || new THREE.Quaternion();
  return points.map((p) => ({
    position: threePositionToROS(p),
    orientation: threeQuatToROS(orient),
  }));
}

// ── Bounding Box Conversion ──────────────────────────────
/** Convert a Three.js Box3 to ROS format corners. */
export function threeBoxToROSCorners(box: THREE.Box3): [number, number, number][] {
  const corners: [number, number, number][] = [];
  const min = box.min;
  const max = box.max;

  const threePoints = [
    new THREE.Vector3(min.x, min.y, min.z),
    new THREE.Vector3(max.x, min.y, min.z),
    new THREE.Vector3(min.x, max.y, min.z),
    new THREE.Vector3(max.x, max.y, min.z),
    new THREE.Vector3(min.x, min.y, max.z),
    new THREE.Vector3(max.x, min.y, max.z),
    new THREE.Vector3(min.x, max.y, max.z),
    new THREE.Vector3(max.x, max.y, max.z),
  ];

  for (const p of threePoints) {
    const ros = threePositionToROS(p);
    corners.push([ros.x, ros.y, ros.z]);
  }
  return corners;
}
