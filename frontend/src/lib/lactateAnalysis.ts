/**
 * Client-side lactate threshold detection engine.
 *
 * TypeScript port of backend/app/services/lactate_engine.py.
 * Piecewise regression breakpoint detection to identify LT1 and LT2.
 */

interface FitResult {
  slope: number;
  intercept: number;
  sse: number;
}

export interface PiecewiseSegmentResult {
  start_x: number;
  end_x: number;
  slope: number;
  intercept: number;
}

export interface BreakpointResult {
  lt1_x: number;
  lt1_lactate: number;
  lt2_x: number;
  lt2_lactate: number;
  segments: PiecewiseSegmentResult[];
  total_sse: number;
  r_squared: number;
}

export function fitSegment(xs: number[], ys: number[]): FitResult | null {
  const n = xs.length;
  if (n === 0) return null;
  if (n === 1) return { slope: 0, intercept: ys[0], sse: 0 };

  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumX2 = 0;
  for (let i = 0; i < n; i++) {
    sumX += xs[i];
    sumY += ys[i];
    sumXY += xs[i] * ys[i];
    sumX2 += xs[i] * xs[i];
  }

  const denom = n * sumX2 - sumX * sumX;
  if (denom === 0) {
    const meanY = sumY / n;
    let sse = 0;
    for (let i = 0; i < n; i++) {
      sse += (ys[i] - meanY) ** 2;
    }
    return { slope: 0, intercept: meanY, sse };
  }

  const slope = (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;

  let sse = 0;
  for (let i = 0; i < n; i++) {
    sse += (ys[i] - (slope * xs[i] + intercept)) ** 2;
  }

  return { slope, intercept, sse };
}

export function detectBreakpoints(
  intensities: number[],
  lactates: number[]
): BreakpointResult | null {
  const n = intensities.length;
  if (n < 5 || n !== lactates.length) return null;

  // Sort by intensity ascending
  const pairs = intensities
    .map((x, i) => ({ x, y: lactates[i] }))
    .sort((a, b) => a.x - b.x);
  const xs = pairs.map((p) => p.x);
  const ys = pairs.map((p) => p.y);

  // All identical intensities
  if (xs[0] === xs[n - 1]) return null;

  let bestSse = Infinity;
  let bestI = -1;
  let bestJ = -1;

  // Segment 1: [0..i] (>=2 pts), Segment 2: [i+1..j] (>=1 pt), Segment 3: [j+1..n-1] (>=2 pts)
  for (let i = 1; i < n - 3; i++) {
    for (let j = i + 1; j < n - 2; j++) {
      const seg1 = fitSegment(xs.slice(0, i + 1), ys.slice(0, i + 1));
      const seg2 = fitSegment(xs.slice(i + 1, j + 1), ys.slice(i + 1, j + 1));
      const seg3 = fitSegment(xs.slice(j + 1), ys.slice(j + 1));

      if (!seg1 || !seg2 || !seg3) continue;

      const totalSse = seg1.sse + seg2.sse + seg3.sse;
      if (totalSse < bestSse) {
        bestSse = totalSse;
        bestI = i;
        bestJ = j;
      }
    }
  }

  if (bestI < 0) return null;

  // Refit best segments
  const seg1 = fitSegment(xs.slice(0, bestI + 1), ys.slice(0, bestI + 1))!;
  const seg2 = fitSegment(xs.slice(bestI + 1, bestJ + 1), ys.slice(bestI + 1, bestJ + 1))!;
  const seg3 = fitSegment(xs.slice(bestJ + 1), ys.slice(bestJ + 1))!;

  // LT1 = midpoint between last of segment 1 and first of segment 2
  const lt1X = (xs[bestI] + xs[bestI + 1]) / 2;
  // LT2 = midpoint between last of segment 2 and first of segment 3
  const lt2X = (xs[bestJ] + xs[bestJ + 1]) / 2;

  // Evaluate regression lines at breakpoint X values
  const lt1Lactate = seg1.slope * lt1X + seg1.intercept;
  const lt2Lactate = seg2.slope * lt2X + seg2.intercept;

  // Calculate R²
  const meanY = ys.reduce((a, b) => a + b, 0) / n;
  const ssTotal = ys.reduce((acc, y) => acc + (y - meanY) ** 2, 0);
  const rSquared = ssTotal > 0 ? 1 - bestSse / ssTotal : 1;

  const segments: PiecewiseSegmentResult[] = [
    {
      start_x: xs[0],
      end_x: xs[bestI],
      slope: seg1.slope,
      intercept: seg1.intercept,
    },
    {
      start_x: xs[bestI + 1],
      end_x: xs[bestJ],
      slope: seg2.slope,
      intercept: seg2.intercept,
    },
    {
      start_x: xs[bestJ + 1],
      end_x: xs[n - 1],
      slope: seg3.slope,
      intercept: seg3.intercept,
    },
  ];

  return {
    lt1_x: Math.round(lt1X * 100) / 100,
    lt1_lactate: Math.round(lt1Lactate * 100) / 100,
    lt2_x: Math.round(lt2X * 100) / 100,
    lt2_lactate: Math.round(lt2Lactate * 100) / 100,
    segments,
    total_sse: Math.round(bestSse * 1000000) / 1000000,
    r_squared: Math.round(rSquared * 10000) / 10000,
  };
}
