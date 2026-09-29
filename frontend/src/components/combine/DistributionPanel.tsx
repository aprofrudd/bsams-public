'use client';

import {
  Cell,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
} from 'recharts';
import type { CombineStationPanel } from '@/lib/types';
import { ACCENT, GRID, MUTED, formatValue, scaleDomain, stackedOffsets } from '@/lib/combineDisplay';

/**
 * Where everyone sits — one dot per boxer on a single value axis.
 *
 * This is the panel that answers "where am I?" for the 30 boxers who are not in
 * the top ten. Mean is dashed, median solid, and the shaded band is one standard
 * deviation either side of the mean.
 *
 * The vertical offsets are derived from the bib rather than randomised, so a dot
 * stays where it was on the previous poll, and boxers who share a value are stacked
 * into a column — four dots on 2.50 RSI have to read as four boxers, not one.
 */
export function DistributionPanel({ panel }: { panel: CombineStationPanel }) {
  const rows = panel.results.filter((row) => row.value != null);
  const offsets = stackedOffsets(
    rows.map((row) => ({ bib: row.bib, value: row.value as number })),
    panel.decimals
  );
  const points = rows.map((row, index) => ({
    x: row.value as number,
    y: offsets[index],
    isLeader: row.rank === 1,
    name: row.display_name,
    // Keyed by bib so a cell keeps its identity between polls; the name is only a
    // fallback for a boxer with no bib.
    key: row.bib != null ? `bib-${row.bib}` : `name-${row.display_name}`,
  }));

  if (points.length === 0) return null;

  const { mean, sd, median } = panel.stats;
  // The same padding rule as the leaderboard track, rather than a fixed 0.5 that is
  // half the range on RSI and invisible on watts.
  const { lo, hi } = scaleDomain(points.map((point) => point.x), 0.12);

  return (
    <div className="h-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 24, bottom: 24, left: 24 }}>
          <XAxis
            type="number"
            dataKey="x"
            domain={[lo, hi]}
            tick={{ fill: '#ffffff99', fontSize: 18 }}
            tickLine={{ stroke: GRID }}
            axisLine={{ stroke: GRID }}
            tickFormatter={(value: number) => formatValue(value, panel.decimals)}
          />
          <YAxis type="number" dataKey="y" domain={[0, 1]} hide />
          {mean != null && sd != null && sd > 0 && (
            <ReferenceArea
              x1={mean - sd}
              x2={mean + sd}
              fill={ACCENT}
              fillOpacity={0.08}
              strokeOpacity={0}
            />
          )}
          {median != null && (
            <ReferenceLine
              x={median}
              stroke="#ffffff99"
              strokeWidth={2}
              // Bottom-left, so it cannot collide with the avg label when the mean
              // and median sit close together — which is most of the time.
              label={{ value: 'median', position: 'insideBottomLeft', fill: '#ffffff99', fontSize: 15 }}
            />
          )}
          {mean != null && (
            <ReferenceLine
              x={mean}
              stroke="#ffffff66"
              strokeDasharray="6 6"
              strokeWidth={2}
              label={{ value: 'avg', position: 'insideTopRight', fill: '#ffffff80', fontSize: 15 }}
            />
          )}
          <Scatter data={points} isAnimationActive={false}>
            {points.map((point) => (
              <Cell
                key={point.key}
                fill={point.isLeader ? ACCENT : MUTED}
                stroke="#ffffff"
                strokeWidth={point.isLeader ? 2 : 1}
                r={point.isLeader ? 13 : 9}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
