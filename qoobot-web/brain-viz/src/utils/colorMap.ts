/**
 * src/utils/colorMap.ts — Color mapping utilities for 3D visualization
 *
 * Provides gradient-based and categorical color mappings for
 * various data types in the 3D scene and UI.
 */

import { colors } from '@/styles/theme';

export type Color = [number, number, number]; // RGB 0..1

// ── Hex ↔ RGB Conversion ─────────────────────────────────
export function hexToRgb(hex: string): Color {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r / 255, g / 255, b / 255];
}

export function rgbToHex([r, g, b]: Color): string {
  const toHex = (v: number) => Math.round(v * 255).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

// ── Gradients ────────────────────────────────────────────
/** Map a value in [0, 1] to a green→yellow→red heatmap. */
export function heatmapColor(t: number): Color {
  const clamped = Math.max(0, Math.min(1, t));
  if (clamped < 0.5) {
    // green → yellow
    const s = clamped * 2;
    return [s, 1, 0];
  } else {
    // yellow → red
    const s = (clamped - 0.5) * 2;
    return [1, 1 - s, 0];
  }
}

/** Map a confidence value [0, 1] to a blue→cyan→green gradient. */
export function confidenceColor(confidence: number): Color {
  const c = Math.max(0, Math.min(1, confidence));
  if (c < 0.5) {
    const s = c * 2;
    return [s * 0.5, 0.5 + s * 0.5, 1];
  } else {
    const s = (c - 0.5) * 2;
    return [0.5 + s * 0.5, 1, 1 - s * 0.5];
  }
}

/** Interpolate between two colors. t: 0→colorA, 1→colorB. */
export function lerpColor(a: Color, b: Color, t: number): Color {
  const ct = Math.max(0, Math.min(1, t));
  return [
    a[0] + (b[0] - a[0]) * ct,
    a[1] + (b[1] - a[1]) * ct,
    a[2] + (b[2] - a[2]) * ct,
  ];
}

// ── Strategy Colors (Three.js RGB) ───────────────────────
export const STRATEGY_RGB: Record<string, Color> = {
  OPTIMAL:      hexToRgb(colors.strategy.optimal),
  CONSERVATIVE: hexToRgb(colors.strategy.conservative),
  AGGRESSIVE:   hexToRgb(colors.strategy.aggressive),
  EXPLORATORY:  hexToRgb(colors.strategy.exploratory),
  REVERSE:      hexToRgb(colors.strategy.reverse),
};

// ── Safety Colors (Three.js RGB) ─────────────────────────
export const SAFETY_RGB: Record<string, Color> = {
  NORMAL:    hexToRgb(colors.safety.normal),
  WARNING:   hexToRgb(colors.safety.warning),
  CRITICAL:  hexToRgb(colors.safety.critical),
  EMERGENCY: hexToRgb(colors.safety.emergency),
};

// ── Object Class Colors ──────────────────────────────────
export function getObjectClassColor(label: string): Color {
  const lower = label.toLowerCase();
  if (lower.includes('cup') || lower.includes('bottle') || lower.includes('mug')) {
    return hexToRgb('#f472b6'); // pink
  }
  if (lower.includes('box') || lower.includes('cube') || lower.includes('container')) {
    return hexToRgb('#fbbf24'); // amber
  }
  if (lower.includes('table') || lower.includes('desk') || lower.includes('shelf')) {
    return hexToRgb('#a78bfa'); // violet
  }
  if (lower.includes('robot') || lower.includes('arm') || lower.includes('gripper')) {
    return hexToRgb('#6366f1'); // indigo (accent)
  }
  if (lower.includes('obstacle') || lower.includes('wall')) {
    return hexToRgb('#ef4444'); // red
  }
  // hash-based deterministic color for unknown labels
  const hash = lower.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
  const hue = (hash * 137) % 360; // golden ratio hash
  const [r, g, b] = hslToRgb(hue, 0.6, 0.5);
  return [r, g, b];
}

// ── Internal: HSL → RGB ──────────────────────────────────
function hslToRgb(h: number, s: number, l: number): Color {
  h /= 360;
  const a = s * Math.min(l, 1 - l);
  const f = (n: number) => {
    const k = (n + h * 12) % 12;
    return l - a * Math.max(-1, Math.min(k - 3, Math.min(9 - k, 1)));
  };
  return [f(0), f(8), f(4)];
}

// ── Occupancy Grid Colors ────────────────────────────────
export function occupancyColor(logOdds: number, minLogOdds = -3, maxLogOdds = 3): Color {
  const clamped = Math.max(minLogOdds, Math.min(maxLogOdds, logOdds));
  const t = (clamped - minLogOdds) / (maxLogOdds - minLogOdds);
  // unknown (gray) → free (green) → occupied (red)
  if (t < 0.3) return [0.3, 0.3, 0.4];  // unknown / gray-blue
  if (t < 0.5) return [0.2, 0.6, 0.2];  // free / green
  if (t < 0.7) return [0.8, 0.6, 0.2];  // uncertain / yellow
  return [0.8, 0.2, 0.2];                // occupied / red
}
