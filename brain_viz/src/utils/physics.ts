/**
 * src/utils/physics.ts — Physics and geometry utility functions
 *
 * Helper calculations for collision detection, distance computation,
 * trajectory validation, and spatial queries used in the 3D frontend.
 */

import * as THREE from 'three';

// ── Distance Calculations ────────────────────────────────
/** Euclidean distance between two 3D points. */
export function distance(a: THREE.Vector3, b: THREE.Vector3): number {
  return a.distanceTo(b);
}

/** Squared distance (avoids sqrt for comparisons). */
export function distanceSq(a: THREE.Vector3, b: THREE.Vector3): number {
  return a.distanceToSquared(b);
}

/** Total path length of an array of 3D points. */
export function pathLength(points: THREE.Vector3[]): number {
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    total += points[i - 1].distanceTo(points[i]);
  }
  return total;
}

// ── Bounding Box Operations ──────────────────────────────
/** Create a THREE.Box3 from corner points. */
export function boxFromCorners(corners: [number, number, number][]): THREE.Box3 {
  const box = new THREE.Box3();
  for (const c of corners) {
    box.expandByPoint(new THREE.Vector3(c[0], c[1], c[2]));
  }
  return box;
}

/** Check if two boxes intersect. */
export function boxesIntersect(a: THREE.Box3, b: THREE.Box3): boolean {
  return a.intersectsBox(b);
}

/** Compute the minimum distance between two boxes. */
export function boxDistance(a: THREE.Box3, b: THREE.Box3): number {
  if (a.intersectsBox(b)) return 0;

  const dx = Math.max(0, Math.abs(a.max.x + a.min.x - b.max.x - b.min.x) / 2 - (a.max.x - a.min.x + b.max.x - b.min.x) / 2);
  const dy = Math.max(0, Math.abs(a.max.y + a.min.y - b.max.y - b.min.y) / 2 - (a.max.y - a.min.y + b.max.y - b.min.y) / 2);
  const dz = Math.max(0, Math.abs(a.max.z + a.min.z - b.max.z - b.min.z) / 2 - (a.max.z - a.min.z + b.max.z - b.min.z) / 2);

  return Math.sqrt(dx * dx + dy * dy + dz * dz);
}

// ── Sphere-Sphere Collision ──────────────────────────────
/** Check if two spheres overlap. */
export function spheresOverlap(
  c1: THREE.Vector3, r1: number,
  c2: THREE.Vector3, r2: number
): boolean {
  return c1.distanceToSquared(c2) <= (r1 + r2) * (r1 + r2);
}

/** Distance between sphere centers minus radii. */
export function sphereSeparation(
  c1: THREE.Vector3, r1: number,
  c2: THREE.Vector3, r2: number
): number {
  return c1.distanceTo(c2) - r1 - r2;
}

// ── Point-in-Volume Tests ────────────────────────────────
/** Check if a point is inside a cylinder (height along Y). */
export function pointInCylinder(
  point: THREE.Vector3,
  baseCenter: THREE.Vector3,
  radius: number,
  height: number
): boolean {
  const dx = point.x - baseCenter.x;
  const dz = point.z - baseCenter.z;
  const dy = point.y - baseCenter.y;

  if (dy < 0 || dy > height) return false;
  return dx * dx + dz * dz <= radius * radius;
}

/** Check if a point is inside an axis-aligned box. */
export function pointInAABB(point: THREE.Vector3, box: THREE.Box3): boolean {
  return box.containsPoint(point);
}

// ── Velocity & Acceleration ──────────────────────────────
/** Compute instantaneous velocity between two poses (m/s). */
export function computeVelocity(
  p1: THREE.Vector3, p2: THREE.Vector3,
  dtSec: number
): THREE.Vector3 {
  return p2.clone().sub(p1).divideScalar(dtSec);
}

/** Compute acceleration between two velocity vectors. */
export function computeAcceleration(
  v1: THREE.Vector3, v2: THREE.Vector3,
  dtSec: number
): THREE.Vector3 {
  return v2.clone().sub(v1).divideScalar(dtSec);
}

// ── Interpolation ────────────────────────────────────────
/** Linear interpolation between two 3D points. */
export function lerp3(a: THREE.Vector3, b: THREE.Vector3, t: number): THREE.Vector3 {
  return a.clone().lerp(b, t);
}

/** Spherical linear interpolation between two quaternions. */
export function slerp(a: THREE.Quaternion, b: THREE.Quaternion, t: number): THREE.Quaternion {
  return a.clone().slerp(b, t);
}

/** Catmull-Rom spline interpolation for smooth trajectory. */
export function catmullRomInterpolate(
  points: THREE.Vector3[], t: number, closed = false
): THREE.Vector3 {
  const catmullRom = new THREE.CatmullRomCurve3(points, closed);
  return catmullRom.getPointAt(t);
}

// ── Workspace Validation ─────────────────────────────────
/** Check if a point is within the robot workspace. */
export function inWorkspace(
  point: THREE.Vector3,
  workspaceCenter: THREE.Vector3 = new THREE.Vector3(0, 0.5, 0),
  workspaceRadius: number = 0.8
): boolean {
  return point.distanceTo(workspaceCenter) <= workspaceRadius;
}

/** Check if a pose is reachable by the arm (Kinova Gen3 approximate). */
export function isReachable(
  point: THREE.Vector3,
  armBase: THREE.Vector3 = new THREE.Vector3(0, 0, 0.3),
  minReach: number = 0.15,
  maxReach: number = 0.85
): boolean {
  const d = point.distanceTo(armBase);
  return d >= minReach && d <= maxReach && point.y >= -0.05;
}

// ── Trajectory Smoothness ────────────────────────────────
/** Compute jerk magnitude at waypoint i (third derivative proxy). */
export function computeJerk(
  waypoints: THREE.Vector3[],
  index: number,
  dtSec: number
): number {
  if (index < 2 || index >= waypoints.length - 1 || dtSec <= 0) return 0;

  const a1 = waypoints[index].clone().sub(waypoints[index - 1])
    .sub(waypoints[index - 1].clone().sub(waypoints[index - 2]));
  const a2 = waypoints[index + 1].clone().sub(waypoints[index])
    .sub(waypoints[index].clone().sub(waypoints[index - 1]));

  return a2.distanceTo(a1) / (dtSec * dtSec);
}

/** Compute trajectory average smoothness (lower = smoother). */
export function trajectorySmoothness(
  waypoints: THREE.Vector3[],
  dtSec: number
): number {
  if (waypoints.length < 4) return 0;

  let totalJerk = 0;
  for (let i = 2; i < waypoints.length - 1; i++) {
    totalJerk += computeJerk(waypoints, i, dtSec);
  }
  return totalJerk / (waypoints.length - 3);
}
