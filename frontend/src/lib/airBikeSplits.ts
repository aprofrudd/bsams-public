/**
 * Air bike split-scheme helpers.
 *
 * A 30s sprint test records power at 7s, 27s and exactly one mid split:
 *   '7_14_27' — the original Boxing Science sprint test
 *   '7_17_27' — the combine / conditioning-template protocol
 *
 * Only one of `power_14s` / `power_17s` is populated on any given sprint row, so
 * nothing should read either field directly. Use these helpers instead.
 */

import type { AirBikeSplitScheme, AirBikeSprint } from './types';

export const DEFAULT_SPLIT_SCHEME: AirBikeSplitScheme = '7_14_27';

/** The mid split, in seconds, for a scheme. */
export function midSplitSeconds(scheme: AirBikeSplitScheme | null | undefined): number {
  return scheme === '7_17_27' ? 17 : 14;
}

/** The mid split, in seconds, inferred from a sprint row (falls back to the scheme). */
export function sprintMidSeconds(
  sprint: Pick<AirBikeSprint, 'power_14s' | 'power_17s'>,
  scheme?: AirBikeSplitScheme | null
): number {
  if (sprint.power_17s != null) return 17;
  if (sprint.power_14s != null) return 14;
  return midSplitSeconds(scheme);
}

/** The mid-split power value, whichever protocol was used. Null if neither is set. */
export function sprintMidPower(
  sprint: Pick<AirBikeSprint, 'power_14s' | 'power_17s'>
): number | null {
  if (sprint.power_17s != null) return sprint.power_17s;
  if (sprint.power_14s != null) return sprint.power_14s;
  return null;
}

/** All recorded power values for a sprint, in time order, skipping the absent mid split. */
export function sprintPowers(
  sprint: Pick<AirBikeSprint, 'power_7s' | 'power_14s' | 'power_17s' | 'power_27s'>
): number[] {
  const mid = sprintMidPower(sprint);
  return mid == null ? [sprint.power_7s, sprint.power_27s] : [sprint.power_7s, mid, sprint.power_27s];
}

/** Peak power across a sprint's recorded splits. */
export function sprintMaxPower(
  sprint: Pick<AirBikeSprint, 'power_7s' | 'power_14s' | 'power_17s' | 'power_27s'>
): number {
  return Math.max(...sprintPowers(sprint));
}

/** Axis ticks for a sprint chart, e.g. [7, 17, 27]. */
export function splitTicks(scheme: AirBikeSplitScheme | null | undefined): number[] {
  return [7, midSplitSeconds(scheme), 27];
}

/** Display label for the mid split, e.g. "17s". */
export function midSplitLabel(scheme: AirBikeSplitScheme | null | undefined): string {
  return `${midSplitSeconds(scheme)}s`;
}
