import {
  clampRotateSeconds,
  connectionState,
  jitterForBib,
  normalisePanelParam,
  ordinal,
  sideLabel,
  stackedOffsets,
  tiedRanks,
  topRows,
  formatValue,
  progressLabel,
  scaleDomain,
  positionPct,
} from '@/lib/combineDisplay';
import type { CombineResultRow } from '@/lib/types';

function row(bib: number): CombineResultRow {
  return {
    bib,
    display_name: `Boxer ${bib}`,
    weight_category: null,
    age_group: null,
    value: 40,
    display_value: '40.0 cm',
    rank: bib,
    attempts: 1,
    z_cohort: 0,
    bs_band: null,
    asymmetry_pct: null,
    dominant_side: null,
  };
}

describe('jitterForBib', () => {
  it('is stable across calls so dots do not jump on every poll', () => {
    expect(jitterForBib(12)).toBe(jitterForBib(12));
  });

  it('separates neighbouring bibs', () => {
    expect(jitterForBib(1)).not.toBe(jitterForBib(2));
  });

  it('stays inside the plot band', () => {
    for (let bib = 1; bib <= 60; bib += 1) {
      const value = jitterForBib(bib);
      expect(value).toBeGreaterThanOrEqual(0.15);
      expect(value).toBeLessThanOrEqual(0.85);
    }
  });

  it('handles a missing bib', () => {
    expect(jitterForBib(null)).toBeCloseTo(0.15);
  });
});

describe('ordinal', () => {
  it.each([
    [1, '1st'],
    [2, '2nd'],
    [3, '3rd'],
    [4, '4th'],
    [11, '11th'],
    [12, '12th'],
    [13, '13th'],
    [21, '21st'],
    [22, '22nd'],
  ])('renders %i as %s', (rank, expected) => {
    expect(ordinal(rank)).toBe(expected);
  });

  it('renders an unranked boxer as a dash', () => {
    expect(ordinal(null)).toBe('—');
  });

  it('marks a shared rank with an equals sign', () => {
    // Two boxers on 50.7 cm are both second; "2nd" twice reads as a board bug.
    expect(ordinal(2, true)).toBe('=2nd');
    expect(ordinal(1, true)).toBe('=1st');
  });

  it('leaves a clear rank alone', () => {
    expect(ordinal(2, false)).toBe('2nd');
  });

  it('still dashes an unranked boxer', () => {
    expect(ordinal(null, true)).toBe('—');
  });
});

describe('tiedRanks', () => {
  it('finds the ranks more than one boxer holds', () => {
    const tied = tiedRanks([{ rank: 1 }, { rank: 2 }, { rank: 2 }, { rank: 4 }]);
    expect(tied.has(2)).toBe(true);
    expect(tied.has(1)).toBe(false);
    expect(tied.size).toBe(1);
  });

  it('ignores boxers with no rank', () => {
    expect(tiedRanks([{ rank: null }, { rank: null }]).size).toBe(0);
  });
});

describe('stackedOffsets', () => {
  it('stacks tied values in bib order rather than overlapping them', () => {
    const offsets = stackedOffsets([{ bib: 9, value: 2.5 }, { bib: 3, value: 2.5 }], 2);
    expect(offsets[0]).not.toBe(offsets[1]);
    // Lowest bib at the bottom of the stack, so the column does not reorder itself
    // between polls.
    expect(offsets[1]).toBeLessThan(offsets[0]);
  });

  it('treats values equal at the panel precision as tied', () => {
    // Pogo is ranked and shown to 2 dp: 2.504 and 2.501 both read 2.50 on the wall.
    const offsets = stackedOffsets([{ bib: 1, value: 2.504 }, { bib: 2, value: 2.501 }], 2);
    expect(offsets[0]).not.toBe(offsets[1]);
    expect(offsets[0] + offsets[1]).toBeCloseTo(1, 5);
  });

  it('leaves a value nobody matched on its stable jitter', () => {
    const offsets = stackedOffsets([{ bib: 7, value: 41 }, { bib: 8, value: 45 }], 1);
    expect(offsets[0]).toBe(jitterForBib(7));
    expect(offsets[1]).toBe(jitterForBib(8));
  });

  it('keeps a large tie inside the plot band and separated', () => {
    const points = Array.from({ length: 12 }, (_, i) => ({ bib: i + 1, value: 2.5 }));
    const offsets = stackedOffsets(points, 2);
    expect(new Set(offsets).size).toBe(12);
    offsets.forEach((offset) => {
      expect(offset).toBeGreaterThanOrEqual(0.12);
      expect(offset).toBeLessThanOrEqual(0.88);
    });
  });

  it('puts a boxer with no bib at the top of the stack', () => {
    const offsets = stackedOffsets([{ bib: null, value: 2.5 }, { bib: 4, value: 2.5 }], 2);
    expect(offsets[0]).toBeGreaterThan(offsets[1]);
  });
});

describe('normalisePanelParam', () => {
  it('accepts a panel key whatever the case', () => {
    expect(normalisePanelParam('CMJ')).toBe('cmj');
    expect(normalisePanelParam(' Overall ')).toBe('overall');
    expect(normalisePanelParam('air_bike')).toBe('air_bike');
  });

  it('rotates rather than showing a blank screen for an unknown panel', () => {
    expect(normalisePanelParam('bogus')).toBeNull();
    expect(normalisePanelParam('')).toBeNull();
    expect(normalisePanelParam(null)).toBeNull();
  });
});

describe('clampRotateSeconds', () => {
  it('takes a sensible dwell as typed', () => {
    expect(clampRotateSeconds('15')).toBe(15);
  });

  it('falls back when the parameter is absent or nonsense', () => {
    expect(clampRotateSeconds(null)).toBe(20);
    expect(clampRotateSeconds('abc')).toBe(20);
  });

  it('clamps a dwell nobody could read, or one that never moves', () => {
    expect(clampRotateSeconds('0')).toBe(5);
    expect(clampRotateSeconds('-4')).toBe(5);
    expect(clampRotateSeconds('99999')).toBe(300);
  });
});

describe('sideLabel', () => {
  it('marks which side a landmine throw came from', () => {
    expect(sideLabel('left')).toBe('L');
    expect(sideLabel('Right')).toBe('R');
  });

  it('is blank for a station without sides', () => {
    expect(sideLabel(null)).toBe('');
    expect(sideLabel(undefined)).toBe('');
  });
});

describe('connectionState', () => {
  it('is live while polls are landing', () => {
    expect(connectionState(3, false)).toBe('live');
  });

  it('admits a problem after 20 seconds without data', () => {
    expect(connectionState(25, false)).toBe('reconnecting');
  });

  it('admits a problem immediately on an error', () => {
    expect(connectionState(1, true)).toBe('reconnecting');
  });

  it('goes offline after two minutes', () => {
    expect(connectionState(130, true)).toBe('offline');
  });
});

describe('topRows', () => {
  it('caps the board and reports the remainder', () => {
    const results = Array.from({ length: 38 }, (_, i) => row(i + 1));
    const { rows, remaining } = topRows(results);
    expect(rows).toHaveLength(10);
    expect(remaining).toBe(28);
  });

  it('reports no remainder for a short board', () => {
    const { rows, remaining } = topRows([row(1), row(2)]);
    expect(rows).toHaveLength(2);
    expect(remaining).toBe(0);
  });
});

describe('formatValue', () => {
  it('respects the station decimals', () => {
    expect(formatValue(41.234, 1)).toBe('41.2');
    expect(formatValue(2.5, 2)).toBe('2.50');
  });

  it('renders a missing value as a dash', () => {
    expect(formatValue(null, 1)).toBe('—');
  });
});

describe('progressLabel', () => {
  it('reads as plain English on the panel header', () => {
    expect(progressLabel(18, 40)).toBe('18 of 40');
  });
});

describe('scaleDomain', () => {
  it('zooms to the data rather than anchoring at zero', () => {
    // Bars must start at zero; dots must not, or a real 10% spread looks like none.
    const { lo, hi } = scaleDomain([45.7, 47.2, 50.7]);
    expect(lo).toBeGreaterThan(45);
    expect(lo).toBeLessThan(45.7);
    expect(hi).toBeGreaterThan(50.7);
  });

  it('pads so the best and worst are not pinned to the edges', () => {
    const { lo, hi } = scaleDomain([10, 20]);
    expect(lo).toBeLessThan(10);
    expect(hi).toBeGreaterThan(20);
  });

  it('handles a cohort where everyone scored the same', () => {
    const { lo, hi } = scaleDomain([40, 40, 40]);
    expect(hi).toBeGreaterThan(lo);
  });

  it('handles an empty cohort', () => {
    expect(scaleDomain([])).toEqual({ lo: 0, hi: 1 });
  });
});

describe('positionPct', () => {
  it('places the ends and the middle', () => {
    expect(positionPct(0, 0, 100)).toBe(0);
    expect(positionPct(50, 0, 100)).toBe(50);
    expect(positionPct(100, 0, 100)).toBe(100);
  });

  it('spreads a tight cluster across the full track', () => {
    const { lo, hi } = scaleDomain([45.7, 50.7]);
    const worst = positionPct(45.7, lo, hi);
    const best = positionPct(50.7, lo, hi);
    // The whole point: a 10% spread must not render as two near-identical marks.
    expect(best - worst).toBeGreaterThan(50);
  });

  it('clamps anything outside the domain', () => {
    expect(positionPct(-5, 0, 10)).toBe(0);
    expect(positionPct(50, 0, 10)).toBe(100);
  });

  it('centres rather than dividing by zero on a degenerate domain', () => {
    expect(positionPct(5, 10, 10)).toBe(50);
  });
});
