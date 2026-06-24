/**
 * src/utils/formatTime.ts — Time formatting utilities
 *
 * Provides consistent time display across the Brain OS dashboard.
 */

// ── Duration Formatting ──────────────────────────────────
/** Format duration in seconds to a human-readable string. */
export function formatDuration(seconds: number): string {
  if (seconds < 0) return '0.0s';

  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)}ms`;
  }

  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;

  if (minutes < 60) {
    return `${minutes}m ${secs.toFixed(0)}s`;
  }

  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${hours}h ${mins}m ${secs.toFixed(0)}s`;
}

/** Format duration compactly (e.g., for trajectory cards). */
export function formatDurationCompact(seconds: number): string {
  if (seconds < 1) return '<1s';
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${minutes}:${secs.toFixed(0).padStart(2, '0')}`;
}

// ── Timestamp Formatting ─────────────────────────────────
/** Format ISO timestamp to local time string. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 1,
  });
}

/** Format ISO timestamp to full local datetime. */
export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

/** Format elapsed time from ISO timestamp. */
export function formatElapsed(iso: string): string {
  const elapsed = Date.now() - new Date(iso).getTime();
  return formatDuration(elapsed / 1000);
}

// ── Score Formatting ─────────────────────────────────────
/** Format a 0..1 score as a percentage string. */
export function formatScore(score: number): string {
  return `${(score * 100).toFixed(1)}%`;
}

/** Format a 0..1 score as a colored class suffix. */
export function scoreClass(score: number): string {
  if (score >= 0.8) return 'text-green-400';
  if (score >= 0.6) return 'text-yellow-400';
  return 'text-red-400';
}

// ── Countdown Formatting ─────────────────────────────────
/** Format countdown seconds to display string. */
export function formatCountdown(seconds: number): string {
  if (seconds <= 0) return '0s';
  if (seconds < 10) return `${seconds.toFixed(1)}s`;
  return `${Math.round(seconds)}s`;
}

/** Format countdown with urgency indicator. */
export function countdownUrgencyClass(seconds: number): string {
  if (seconds <= 1) return 'text-red-400 animate-pulse';
  if (seconds <= 3) return 'text-yellow-400';
  return 'text-green-400';
}

// ── Number Formatting ────────────────────────────────────
/** Format a large number with comma separators. */
export function formatNumber(n: number): string {
  return n.toLocaleString('zh-CN');
}

/** Format bytes to human-readable size. */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

/** Format frequency in Hz. */
export function formatFrequency(hz: number): string {
  if (hz >= 1000) return `${(hz / 1000).toFixed(1)} kHz`;
  return `${hz.toFixed(1)} Hz`;
}
