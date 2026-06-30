/**
 * src/styles/theme.ts — Brain OS design tokens
 *
 * Centralized theme configuration used by Tailwind and
 * any programmatic styling (e.g., Three.js color materials).
 */

// ── Color Palette ────────────────────────────────────────
export const colors = {
  // Background hierarchy
  bg: {
    primary:   '#0a0a1a',  // brain-bg (deep blue-black)
    secondary: '#10102a',  // brain-panel
    tertiary:  '#1a1a3a',  // brain-surface
    elevated:  '#1e1e40',  // hover/active states
  },

  // Foreground
  text: {
    primary:   '#e8e8f0',  // brain-text
    secondary: '#a0a0c0',  // brain-muted
    disabled:  '#5a5a7a',
    inverse:   '#0a0a1a',
  },

  // Borders & dividers
  border: {
    default:   '#2a2a4a',  // brain-border
    light:     '#3a3a5a',
    focus:     '#6366f1',  // brain-accent (indigo)
  },

  // Accent colors
  accent: {
    primary:   '#6366f1',  // indigo-500
    hover:     '#818cf8',  // indigo-400
    active:    '#4f46e5',  // indigo-600
  },

  // Semantic colors
  semantic: {
    success:   '#22c55e',  // green-500
    warning:   '#eab308',  // yellow-500
    danger:    '#ef4444',  // red-500
    info:      '#3b82f6',  // blue-500
    critical:  '#dc2626',  // red-600
  },

  // Strategy colors
  strategy: {
    optimal:     '#f59e0b',  // amber-500
    conservative:'#22c55e',  // green-500
    aggressive:  '#ef4444',  // red-500
    exploratory: '#3b82f6',  // blue-500
    reverse:     '#8b5cf6',  // violet-500
  },

  // Safety level colors
  safety: {
    normal:    '#22c55e',
    warning:   '#eab308',
    critical:  '#ef4444',
    emergency: '#dc2626',
  },

  // Chart colors (for score charts, metrics)
  chart: [
    '#6366f1', '#22c55e', '#f59e0b', '#ef4444',
    '#3b82f6', '#8b5cf6', '#ec4899', '#14b8a6',
  ],
} as const;

// ── Spacing Scale ────────────────────────────────────────
export const spacing = {
  xs:  '0.25rem',   // 4px
  sm:  '0.5rem',    // 8px
  md:  '0.75rem',   // 12px
  lg:  '1rem',      // 16px
  xl:  '1.5rem',    // 24px
  '2xl':'2rem',     // 32px
  '3xl':'3rem',     // 48px
} as const;

// ── Typography ───────────────────────────────────────────
export const typography = {
  fontFamily: {
    sans:  '"Inter", "Noto Sans SC", system-ui, sans-serif',
    mono:  '"JetBrains Mono", "Fira Code", monospace',
    display:'"Inter", "Noto Sans SC", system-ui, sans-serif',
  },
  fontSize: {
    xs:    '0.75rem',   // 12px
    sm:    '0.875rem',  // 14px
    base:  '1rem',      // 16px
    lg:    '1.125rem',  // 18px
    xl:    '1.25rem',   // 20px
    '2xl': '1.5rem',    // 24px
    '3xl': '1.875rem',  // 30px
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
} as const;

// ── Border Radius ────────────────────────────────────────
export const borderRadius = {
  sm:    '0.25rem',  // 4px
  md:    '0.375rem', // 6px
  lg:    '0.5rem',   // 8px
  xl:    '0.75rem',  // 12px
  full:  '9999px',
} as const;

// ── Shadows ──────────────────────────────────────────────
export const shadows = {
  sm:    '0 1px 2px 0 rgba(0, 0, 0, 0.3)',
  md:    '0 4px 6px -1px rgba(0, 0, 0, 0.4)',
  lg:    '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
  xl:    '0 20px 25px -5px rgba(0, 0, 0, 0.6)',
  glow:  '0 0 15px 2px rgba(99, 102, 241, 0.3)', // accent glow
} as const;

// ── Animation ────────────────────────────────────────────
export const animation = {
  duration: {
    fast:    '150ms',
    normal:  '200ms',
    slow:    '300ms',
    slower:  '500ms',
  },
  easing: {
    default: 'cubic-bezier(0.4, 0, 0.2, 1)',
    in:      'cubic-bezier(0.4, 0, 1, 1)',
    out:     'cubic-bezier(0, 0, 0.2, 1)',
    inOut:   'cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const;

// ── Z-Index Scale ────────────────────────────────────────
export const zIndex = {
  base:     0,
  dropdown: 10,
  sticky:   20,
  overlay:  30,
  modal:    40,
  toast:    50,
  tooltip:  60,
} as const;

// ── Three.js Specific ────────────────────────────────────
export const three = {
  grid: {
    size: 10,
    divisions: 20,
    color: '#2a2a4a',
    centerColor: '#6366f1',
  },
  ghostTrail: {
    defaultColor: '#6366f1',
    defaultOpacity: 0.6,
    defaultLineWidth: 2,
    highlightOpacity: 1.0,
    highlightLineWidth: 4,
  },
  camera: {
    defaultPosition: [6, 4, 8] as [number, number, number],
    defaultTarget: [0, 0.5, 0] as [number, number, number],
    near: 0.1,
    far: 50,
    fov: 50,
  },
} as const;
