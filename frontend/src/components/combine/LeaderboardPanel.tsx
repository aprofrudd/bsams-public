'use client';

import type { CombineStationPanel } from '@/lib/types';
import {
  ACCENT,
  MUTED,
  formatValue,
  ordinal,
  positionPct,
  scaleDomain,
  sideLabel,
  tiedRanks,
  topRows,
} from '@/lib/combineDisplay';

/**
 * Top of the board as a ranked dot plot.
 *
 * This was bars, and bars were the wrong mark. A bar's length is its encoding, so
 * it has to start at zero — which for a cohort jumping 45-51 cm meant ten bars of
 * near-identical length and no visible difference between first and tenth.
 *
 * A dot encodes position, not length, so the scale can zoom to the data honestly.
 * The same 10% spread now uses the full width of the screen. The axis labels below
 * state the range so nobody reads a dot near the left edge as "nearly zero".
 *
 * Hand-built rather than Recharts: ten rows need to align perfectly with the name
 * and value columns at vh-relative type sizes, which is fiddly to pin down inside a
 * responsive chart and trivial in flexbox.
 */
export function LeaderboardPanel({ panel }: { panel: CombineStationPanel }) {
  const { rows, remaining } = topRows(panel.results);
  // Ranks are shared across the whole field, so a boxer can be "=10th" with
  // someone who did not make the top ten.
  const tied = tiedRanks(panel.results);

  if (rows.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-[3vh] text-white/40">First results coming soon</p>
      </div>
    );
  }

  // Scale to the rows actually shown, not the whole room.
  //
  // Scaling to the full cohort pushes the top ten into the right-hand third and
  // undoes the point of the exercise — first and tenth end up a few pixels apart.
  // The strip below is where the whole room is shown honestly; up here the job is
  // separating the leaders, and the axis labels state the range so it cannot be
  // misread as running from zero.
  const shownValues = rows.map((r) => r.value).filter((v): v is number => v != null);
  const { lo, hi } = scaleDomain(shownValues);
  const mean = panel.stats.mean;
  // The room average often sits below the top ten's range; showing it pinned to the
  // edge would be a lie, so it is drawn only when it genuinely falls inside.
  const meanPct =
    mean != null && mean >= lo && mean <= hi ? positionPct(mean, lo, hi) : null;

  return (
    <div className="flex h-full flex-col">
      <ol className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {rows.map((row) => {
          const isLeader = row.rank === 1;
          const pct = row.value != null ? positionPct(row.value, lo, hi) : 0;
          const side = sideLabel(row.side);
          return (
            <li
              key={row.bib ?? row.display_name}
              className="flex min-h-0 flex-1 items-center gap-[1.2vw] leading-none"
            >
              <span
                className="w-[5vw] shrink-0 text-right font-mono text-[2.3vh] font-bold tabular-nums"
                style={{ color: isLeader ? ACCENT : '#ffffff55' }}
              >
                {ordinal(row.rank, row.rank != null && tied.has(row.rank))}
              </span>

              <span
                className={`w-[17vw] shrink-0 truncate text-[2.7vh] ${
                  isLeader ? 'font-bold text-white' : 'font-semibold text-white/85'
                }`}
              >
                {row.display_name}
              </span>

              {/* Track: a full-width rule identical on every row, so it encodes
                  nothing — it is there to carry the eye from the name to the dot. */}
              <span className="relative h-full max-h-[3.2vh] flex-1">
                <span className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-white/[0.08]" />
                {meanPct != null && (
                  <span
                    className="absolute top-0 h-full w-px bg-white/25"
                    style={{ left: `${meanPct}%` }}
                  />
                )}
                <span
                  className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${pct}%`,
                    width: isLeader ? '2.2vh' : '1.6vh',
                    height: isLeader ? '2.2vh' : '1.6vh',
                    backgroundColor: isLeader ? ACCENT : MUTED,
                    border: `2px solid ${isLeader ? '#ffffff' : '#ffffff55'}`,
                  }}
                />
              </span>

              <span
                className={`w-[9vw] shrink-0 text-right font-mono text-[3vh] tabular-nums ${
                  isLeader ? 'font-bold text-accent' : 'font-semibold text-white'
                }`}
              >
                {formatValue(row.value, panel.decimals)}
                {side && (
                  <span className="ml-[0.4vw] text-[2vh] font-semibold text-white/45">{side}</span>
                )}
              </span>
            </li>
          );
        })}
      </ol>

      {/* The scale is stated, because the dots do not start at zero. */}
      <div className="flex items-center gap-[1.2vw] pt-[0.8vh] text-[1.6vh] text-white/30">
        <span className="w-[5vw] shrink-0" />
        <span className="w-[17vw] shrink-0">
          {remaining > 0 && `and ${remaining} more below`}
        </span>
        <span className="relative flex-1">
          <span className="absolute left-0">
            {formatValue(lo, panel.decimals)}
            {panel.unit ? ` ${panel.unit}` : ''}
          </span>
          {meanPct != null && (
            <span
              className="absolute -translate-x-1/2 text-white/40"
              style={{ left: `${meanPct}%` }}
            >
              avg
            </span>
          )}
          <span className="absolute right-0">
            {formatValue(hi, panel.decimals)}
            {panel.unit ? ` ${panel.unit}` : ''}
          </span>
        </span>
        <span className="w-[9vw] shrink-0" />
      </div>
    </div>
  );
}
