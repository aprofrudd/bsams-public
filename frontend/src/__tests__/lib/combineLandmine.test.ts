import {
  isWithinReferenceTolerance,
  nearestLadderLoad,
  referenceLoadWarning,
} from '@/lib/combineLandmine';

/**
 * The board ranks a landmine throw only when its load is within tolerance of the
 * event's reference load. Two places have to agree with that rule: the console,
 * where the ladder and the reference load are typed, and the station's "Ref" badge,
 * which is the only on-screen cue that a load counts.
 */

describe('nearestLadderLoad', () => {
  it('returns the closest load on the ladder', () => {
    expect(nearestLadderLoad([12, 17, 22, 27], 20)).toBe(22);
    expect(nearestLadderLoad([10, 15, 20, 25], 20)).toBe(20);
  });

  it('returns null when there is no ladder to be near', () => {
    expect(nearestLadderLoad([], 20)).toBeNull();
  });
});

describe('isWithinReferenceTolerance', () => {
  it('is a tolerance test, not exact equality', () => {
    expect(isWithinReferenceTolerance(22, 22.5, 1)).toBe(true);
    expect(isWithinReferenceTolerance(20, 22.5, 1)).toBe(false);
  });

  it('treats a zero tolerance as exactly the reference load', () => {
    expect(isWithinReferenceTolerance(22, 22, 0)).toBe(true);
    expect(isWithinReferenceTolerance(22, 22.5, 0)).toBe(false);
  });
});

describe('referenceLoadWarning', () => {
  it('names the nearest ladder load when the reference is orphaned', () => {
    const warning = referenceLoadWarning([12, 17, 22, 27], 20, 1);
    expect(warning).toContain('22');
    expect(warning).toContain('20');
  });

  it('says nothing when the reference load is on the ladder', () => {
    expect(referenceLoadWarning([10, 15, 20, 25], 20, 1)).toBeNull();
  });

  it('accepts a reference between two loads when the tolerance covers it', () => {
    expect(referenceLoadWarning([12, 17, 22, 27], 22.5, 1)).toBeNull();
  });

  it('accepts an orphaned reference once the tolerance is widened to reach it', () => {
    expect(referenceLoadWarning([12, 17, 22, 27], 20, 2)).toBeNull();
  });

  it('has nothing to say without a ladder or a reference', () => {
    expect(referenceLoadWarning([], 20, 1)).toBeNull();
    expect(referenceLoadWarning([10, 15], null, 1)).toBeNull();
  });
});
