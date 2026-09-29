'use client';

import type { CombineLeaderboard, CombineStationPanel } from '@/lib/types';
import {
  ACCENT,
  BAND_COLORS,
  formatStat,
  formatValue,
  sideLabel,
  tiedRanks,
} from '@/lib/combineDisplay';

/**
 * Every station on one screen: top three and the group average.
 *
 * The rotating panels give one test the whole screen; this gives the whole event at
 * a glance. Six cards means smaller type than a single-station panel, so it reads
 * from across a room but not from the very back of a hall — it is the overview
 * screen, with the rotation doing the "readable from anywhere" job.
 */
function StationCard({
  panel,
  participantCount,
}: {
  panel: CombineStationPanel;
  participantCount: number;
}) {
  const top3 = panel.results.slice(0, 3);
  const unit = panel.unit ? ` ${panel.unit}` : '';
  // Ties come from the whole field, not just the three shown: a boxer can be
  // "=3rd" with the boxer who shares the rank further down the list.
  const tied = tiedRanks(panel.results);

  return (
    <div className="flex min-h-0 flex-col rounded-xl border border-secondary-muted/40 bg-primary-dark/50 p-[1.4vh]">
      <header className="flex items-baseline justify-between gap-2">
        <h3 className="truncate font-heading text-[2.4vh] font-bold uppercase leading-none tracking-wider text-accent">
          {panel.short_label}
        </h3>
        <span className="shrink-0 font-mono text-[1.5vh] tabular-nums text-white/35">
          {panel.completed}/{participantCount}
        </span>
      </header>

      {top3.length === 0 ? (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-[1.8vh] text-white/25">Not started</p>
        </div>
      ) : (
        <ol className="mt-[1vh] flex min-h-0 flex-1 flex-col justify-evenly">
          {top3.map((row) => {
            const isLeader = row.rank === 1;
            const side = sideLabel(row.side);
            return (
              <li
                key={row.bib ?? row.display_name}
                className="flex items-baseline gap-[0.6vw] leading-none"
              >
                <span
                  className="w-[2.2vw] shrink-0 text-right font-mono text-[1.9vh] font-bold tabular-nums"
                  style={{ color: isLeader ? ACCENT : '#ffffff45' }}
                >
                  {row.rank == null ? '—' : `${tied.has(row.rank) ? '=' : ''}${row.rank}`}
                </span>
                <span
                  className={`min-w-0 flex-1 truncate text-[2.2vh] ${
                    isLeader ? 'font-bold text-white' : 'font-medium text-white/75'
                  }`}
                >
                  {row.display_name}
                </span>
                {row.bs_band && isLeader && (
                  <span
                    className="shrink-0 text-[1.2vh] font-bold uppercase tracking-widest"
                    style={{ color: BAND_COLORS[row.bs_band] }}
                  >
                    {row.bs_band === 'above_average' ? 'above avg' : row.bs_band}
                  </span>
                )}
                <span
                  className={`shrink-0 font-mono text-[2.4vh] tabular-nums ${
                    isLeader ? 'font-bold text-accent' : 'font-semibold text-white/90'
                  }`}
                >
                  {formatValue(row.value, panel.decimals)}
                </span>
                {side && (
                  <span className="shrink-0 font-mono text-[1.5vh] font-bold text-white/40">
                    {side}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
      )}

      <footer className="mt-[1vh] flex items-baseline justify-between border-t border-white/10 pt-[0.8vh]">
        <span className="text-[1.4vh] uppercase tracking-widest text-white/35">Group average</span>
        <span className="font-mono text-[2.2vh] font-semibold tabular-nums text-white">
          {formatStat(panel.stats.mean, panel.decimals)}
          <span className="text-[1.4vh] font-normal text-white/40">{unit}</span>
        </span>
      </footer>
    </div>
  );
}

export function SummaryPanel({ board }: { board: CombineLeaderboard }) {
  const leader = board.overall.find((e) => e.eligible && e.rank === 1);
  // Same rule as the Combine Score panel: who you beat, counted from the ranking, so the
  // two screens cannot disagree. The composite number is a coach's tool and stays off both.
  const ranked = board.overall.filter((e) => e.eligible);
  const rankedCount = ranked.length;
  const leaderBeat = leader
    ? ranked.filter((o) => o.combine_score < leader.combine_score).length
    : 0;

  return (
    <div className="flex h-full flex-col gap-[1.5vh]">
      <header className="flex items-end justify-between">
        <div>
          <h2 className="font-heading text-[4.2vh] font-bold uppercase leading-none tracking-wider text-accent">
            Every station
          </h2>
          <p className="mt-[0.5vh] text-[1.7vh] uppercase tracking-widest text-white/40">
            Top three and the group average
          </p>
        </div>
        {leader && (
          <div className="text-right">
            <p className="text-[1.7vh] uppercase tracking-widest text-white/40">
              Leading overall
            </p>
            <p className="text-[3vh] font-bold leading-tight text-white">
              {leader.display_name}
            </p>
            <p className="font-mono text-[2vh] tabular-nums text-accent">
              {rankedCount > 1 && `beat ${leaderBeat} of ${rankedCount} · `}
              {leader.stations_completed}/6 stations
            </p>
          </div>
        )}
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-3 grid-rows-2 gap-[1.2vh]">
        {board.stations.map((panel) => (
          <StationCard
            key={panel.station}
            panel={panel}
            participantCount={board.participant_count}
          />
        ))}
      </div>
    </div>
  );
}
