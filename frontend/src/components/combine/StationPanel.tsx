'use client';

import type { CombineStationPanel } from '@/lib/types';
import {
  BAND_COLORS,
  BAND_LABELS,
  formatStat,
  progressLabel,
  sideLabel,
} from '@/lib/combineDisplay';
import { LeaderboardPanel } from './LeaderboardPanel';
import { DistributionPanel } from './DistributionPanel';

/**
 * One station, filling a gym TV.
 *
 * Type is sized in vh rather than fixed pixels so the same board is legible on a
 * 55" screen across a hall and on a 27" monitor beside the coach. Rule of thumb:
 * glyph height ~= viewing distance / 200.
 */
export function StationPanel({
  panel,
  participantCount,
}: {
  panel: CombineStationPanel;
  participantCount: number;
}) {
  const leader = panel.results[0];
  const unit = panel.unit ? ` ${panel.unit}` : '';
  // Landmine is thrown both sides and the board ranks the better of the two, so
  // the leader's number means little without saying which arm threw it.
  const leaderSide = leader ? sideLabel(leader.side) : '';

  return (
    <div className="flex h-full flex-col gap-[1.5vh]">
      <header className="flex items-end justify-between">
        <div>
          <h2 className="font-heading text-[5vh] font-bold uppercase leading-none tracking-wider text-accent">
            {panel.label}
          </h2>
          <p className="mt-[0.5vh] text-[1.8vh] uppercase tracking-widest text-white/40">
            {progressLabel(panel.completed, participantCount)} complete
            {panel.cohort_basis === 'event' && ' · compared with the whole room'}
          </p>
        </div>

        {leader && (
          <div className="text-right">
            <p className="text-[1.8vh] uppercase tracking-widest text-white/40">Leader</p>
            <p className="text-[3.2vh] font-semibold leading-tight text-white">
              {leader.display_name}
            </p>
            <p className="font-mono text-[7vh] font-bold leading-none tabular-nums text-accent">
              {leader.display_value ?? '—'}
              {leaderSide && (
                <span className="ml-[0.6vw] text-[3vh] text-white/50">{leaderSide}</span>
              )}
            </p>
            {leader.bs_band && (
              <p
                className="mt-[0.5vh] text-[2vh] font-bold uppercase tracking-widest"
                style={{ color: BAND_COLORS[leader.bs_band] }}
              >
                {BAND_LABELS[leader.bs_band]}
              </p>
            )}
          </div>
        )}
      </header>

      <div className="min-h-0 flex-1">
        <LeaderboardPanel panel={panel} />
      </div>

      {panel.stats.n > 1 && (
        <div className="h-[22vh] shrink-0 rounded-xl border border-secondary-muted/40 bg-primary-dark/40 p-[1vh]">
          <div className="flex items-baseline justify-between px-[1vh] pb-[0.5vh]">
            <span className="text-[1.8vh] uppercase tracking-widest text-white/40">
              The whole room
            </span>
            <span className="font-mono text-[1.8vh] tabular-nums text-white/50">
              avg {formatStat(panel.stats.mean, panel.decimals)}
              {unit} · median {formatStat(panel.stats.median, panel.decimals)}
              {unit} · best {formatStat(panel.stats.max, panel.decimals)}
              {unit}
            </span>
          </div>
          <div className="h-[calc(100%-3vh)]">
            <DistributionPanel panel={panel} />
          </div>
        </div>
      )}
    </div>
  );
}
