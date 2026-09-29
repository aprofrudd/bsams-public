/**
 * Display helpers for the combine kiosk.
 *
 * Kept out of the components so the formatting rules — which drive what a room of
 * teenagers sees — can be tested directly.
 */

import type { CombineBsBand, CombineResultRow, CombineStation } from './types';

/** Panels the kiosk can show, in rotation order. */
export const KIOSK_PANELS: (CombineStation | 'overall' | 'summary')[] = [
  // Leads the rotation: the whole event at a glance before the detail panels.
  'summary',
  'cmj',
  'pogo',
  'landmine',
  'grip',
  'trunk_rotation',
  'air_bike',
  'overall',
];

/**
 * Short names for the pin control, matching the backend's STATION_SPECS short labels.
 * The button sits on a TV at a distance, so these stay to one or two words.
 */
export const PANEL_LABELS: Record<string, string> = {
  summary: 'Every station',
  cmj: 'CMJ',
  pogo: 'Pogo',
  landmine: 'Punch',
  grip: 'Grip',
  trunk_rotation: 'Rotation',
  air_bike: 'Bike',
  overall: 'Combine Score',
};

export function panelLabel(key: string | null | undefined): string {
  return (key && PANEL_LABELS[key]) || 'this panel';
}

export const BAND_LABELS: Record<CombineBsBand, string> = {
  elite: 'ELITE',
  above_average: 'ABOVE AVERAGE',
  average: 'AVERAGE',
  developing: 'DEVELOPING',
};

/** Status colours are reserved for status — never reused as a series colour. */
export const BAND_COLORS: Record<CombineBsBand, string> = {
  elite: '#22c55e',
  above_average: '#33CBF4',
  average: '#eab308',
  developing: '#ef4444',
};

export const ACCENT = '#33CBF4';
export const MUTED = '#2D5585';
export const GRID = '#2D5585';

/**
 * A stable vertical offset for a dot plot.
 *
 * Random jitter would make every dot jump on each five-second poll, which reads as
 * the board glitching. Deriving it from the bib keeps each boxer's dot still.
 */
export function jitterForBib(bib: number | null | undefined): number {
  const seed = typeof bib === 'number' ? bib : 0;
  return 0.15 + ((seed * 37) % 70) / 100;
}

/**
 * 1 -> "1st". Used for the big rank numerals.
 *
 * `tied` prefixes an equals sign: the engine ranks on the value the board prints,
 * so two identical jumps really are both first, and showing "1st" and "2nd" would
 * read as a scoring error to the boxer who matched the leader.
 */
export function ordinal(rank: number | null | undefined, tied = false): string {
  if (rank == null) return '—';
  const prefix = tied ? '=' : '';
  const mod100 = rank % 100;
  const suffix =
    mod100 >= 11 && mod100 <= 13
      ? 'th'
      : { 1: 'st', 2: 'nd', 3: 'rd' }[rank % 10] ?? 'th';
  return `${prefix}${rank}${suffix}`;
}

/** The ranks more than one boxer holds, so they can be marked "=2nd". */
export function tiedRanks(rows: { rank: number | null }[]): Set<number> {
  const counts = new Map<number, number>();
  rows.forEach((row) => {
    if (row.rank == null) return;
    counts.set(row.rank, (counts.get(row.rank) ?? 0) + 1);
  });
  const tied = new Set<number>();
  counts.forEach((count, rank) => {
    if (count > 1) tied.add(rank);
  });
  return tied;
}

export interface StackedPoint {
  bib: number | null;
  value: number;
}

/**
 * Vertical offsets for a dot plot, stacking boxers who share a value.
 *
 * Ties are common once values are rounded to what the board shows — a whole squad
 * can land on 2.50 RSI — and stacked dots say "four boxers here" where overlapping
 * dots say "one". Everyone else keeps the stable per-bib jitter, so a dot only
 * moves when a result changes, not on every five-second poll.
 */
export function stackedOffsets(points: StackedPoint[], decimals: number): number[] {
  const groups = new Map<string, number[]>();
  points.forEach((point, index) => {
    const key = Number.isFinite(point.value) ? point.value.toFixed(decimals) : `unknown-${index}`;
    const group = groups.get(key);
    if (group) group.push(index);
    else groups.set(key, [index]);
  });

  const offsets = points.map((point) => jitterForBib(point.bib));

  groups.forEach((indices) => {
    if (indices.length < 2) return;
    // Bib order, so the column is the same on every poll.
    const ordered = [...indices].sort((a, b) => {
      const left = points[a].bib;
      const right = points[b].bib;
      if (left == null) return 1;
      if (right == null) return -1;
      return left - right;
    });
    const spacing = Math.min(0.16, 0.72 / (ordered.length - 1));
    ordered.forEach((pointIndex, slot) => {
      offsets[pointIndex] = 0.5 + (slot - (ordered.length - 1) / 2) * spacing;
    });
  });

  return offsets;
}

/** Landmine only: "L" / "R" beside the value, because both sides are thrown. */
export function sideLabel(side: string | null | undefined): string {
  if (!side) return '';
  const letter = side.trim().charAt(0).toUpperCase();
  return letter === 'L' || letter === 'R' ? letter : '';
}

export const DEFAULT_ROTATE_SECONDS = 20;
const MIN_ROTATE_SECONDS = 5;
const MAX_ROTATE_SECONDS = 300;

/**
 * `?panel=` from the URL, or null to rotate.
 *
 * Case-insensitive because the link is typed by hand onto a TV browser, and an
 * unrecognised value rotates rather than pinning the board to a panel that does
 * not exist — a blank screen in the hall is the one outcome worth ruling out.
 */
export function normalisePanelParam(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const key = raw.trim().toLowerCase();
  return (KIOSK_PANELS as string[]).includes(key) ? key : null;
}

/** `?rotate=` in seconds, clamped so the board neither flickers nor freezes. */
export function clampRotateSeconds(
  raw: string | null | undefined,
  fallback = DEFAULT_ROTATE_SECONDS
): number {
  if (raw == null || raw.trim() === '') return fallback;
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(MAX_ROTATE_SECONDS, Math.max(MIN_ROTATE_SECONDS, parsed));
}

export type ConnectionState = 'live' | 'reconnecting' | 'offline';

/**
 * How the board describes its own freshness.
 *
 * A frozen board that still says LIVE is the worst outcome on a testing day, so
 * this errs towards admitting a problem early.
 */
export function connectionState(staleSeconds: number, hasError: boolean): ConnectionState {
  if (staleSeconds >= 120) return 'offline';
  if (hasError || staleSeconds >= 20) return 'reconnecting';
  return 'live';
}

export const CONNECTION_LABELS: Record<ConnectionState, string> = {
  live: 'LIVE',
  reconnecting: 'RECONNECTING',
  offline: 'OFFLINE',
};

export const CONNECTION_COLORS: Record<ConnectionState, string> = {
  live: '#22c55e',
  reconnecting: '#eab308',
  offline: '#ef4444',
};

/** How many rows a leaderboard panel shows before the "and N more" strip. */
export const LEADERBOARD_LIMIT = 10;

export function topRows(
  results: CombineResultRow[],
  limit = LEADERBOARD_LIMIT
): { rows: CombineResultRow[]; remaining: number } {
  return {
    rows: results.slice(0, limit),
    remaining: Math.max(0, results.length - limit),
  };
}

/** Two-decimal-safe formatting that never prints "41.20000000000001". */
export function formatValue(value: number | null | undefined, decimals: number): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toFixed(decimals);
}

export function formatStat(value: number | null | undefined, decimals: number): string {
  return value == null ? '—' : value.toFixed(decimals);
}

/**
 * The value range a panel plots across.
 *
 * Deliberately NOT anchored at zero. A bar has to start at zero because its length
 * is the encoding — but a dot encodes position, so zooming to the data is the
 * honest way to show that 45.7 and 50.7 cm are genuinely different performances.
 * Padded so the fastest and slowest are not pinned to the edges.
 */
export function scaleDomain(
  values: number[],
  padRatio = 0.08
): { lo: number; hi: number } {
  const present = values.filter((v) => Number.isFinite(v));
  if (present.length === 0) return { lo: 0, hi: 1 };
  const min = Math.min(...present);
  const max = Math.max(...present);
  if (min === max) {
    // Everyone identical — centre them rather than dividing by zero.
    const pad = Math.abs(min) * 0.1 || 1;
    return { lo: min - pad, hi: max + pad };
  }
  const pad = (max - min) * padRatio;
  return { lo: min - pad, hi: max + pad };
}

/** Where a value sits across the track, 0-100. */
export function positionPct(value: number, lo: number, hi: number): number {
  if (!Number.isFinite(value) || hi <= lo) return 50;
  return Math.min(100, Math.max(0, ((value - lo) / (hi - lo)) * 100));
}

/** "18 of 40" progress wording for the panel header. */
export function progressLabel(completed: number, total: number): string {
  return `${completed} of ${total}`;
}
