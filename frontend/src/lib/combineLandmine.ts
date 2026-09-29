/**
 * The landmine ladder and the one load the board ranks.
 *
 * `combine_engine.score_attempt` scores a throw only when its load is within
 * `landmine_reference_tolerance_kg` of `landmine_reference_load_kg`. Everything else
 * about a throw still works when the reference load is not on the ladder — it saves,
 * it fills the station chip, it promotes a VBT profile — so the only symptom is a
 * Punch panel that stays empty all day. These helpers keep the console, where the
 * mistake is made, and the station's "Ref" badge, the only cue that a load counts,
 * on the same rule as the engine.
 *
 * Mirrors `reference_load_error` in backend/app/schemas/combine.py.
 */

/** The engine's test: within tolerance of the reference load, not equal to it. */
export function isWithinReferenceTolerance(
  loadKg: number,
  referenceKg: number,
  toleranceKg: number
): boolean {
  return Math.abs(loadKg - referenceKg) <= (toleranceKg || 0);
}

export function nearestLadderLoad(loads: number[], referenceKg: number): number | null {
  if (loads.length === 0) return null;
  return loads.reduce((best, load) =>
    Math.abs(load - referenceKg) < Math.abs(best - referenceKg) ? load : best
  );
}

/** Why this ladder and reference load would leave the board empty, if they would. */
export function referenceLoadWarning(
  loads: number[],
  referenceKg: number | null | undefined,
  toleranceKg: number
): string | null {
  if (referenceKg == null) return null;
  const nearest = nearestLadderLoad(loads, referenceKg);
  if (nearest === null || isWithinReferenceTolerance(nearest, referenceKg, toleranceKg)) {
    return null;
  }
  return (
    `The reference load ${referenceKg} kg is not on the ladder — the nearest load is ` +
    `${nearest} kg and the tolerance is ${toleranceKg} kg, so no throw would be ranked ` +
    `on the board.`
  );
}
