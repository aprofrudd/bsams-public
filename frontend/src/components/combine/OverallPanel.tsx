'use client';

import type { CombineLeaderboard } from '@/lib/types';
import { ACCENT, MUTED, ordinal, positionPct, scaleDomain, tiedRanks } from '@/lib/combineDisplay';

/**
 * The Combine Score board.
 *
 * The score covers only the stations each boxer has actually completed, so nobody is
 * punished for the timetable. Anyone below the completion threshold is still listed,
 * marked "not yet ranked" — vanishing from the board mid-morning would be worse than
 * appearing provisionally.
 *
 * The score itself is deliberately NOT on the wall. It is a composite of six tests on a
 * scale that needs explaining, and explaining it in small text under a TV does not work:
 * a boxer wants to know where they came, not that they are 1.03 SD above the room. The
 * number still exists, still orders this list and still reaches coaches through the API;
 * here it survives only as the position of a dot.
 *
 * Dots rather than bars, for the same reason as the station panels: scores cluster
 * in the 50s, and bars from zero made first and tenth look identical.
 */
export function OverallPanel({ board }: { board: CombineLeaderboard }) {
  const entries = board.overall;
  const ranked = entries.filter((e) => e.eligible).slice(0, 10);
  const provisional = entries.filter((e) => !e.eligible).length;

  if (ranked.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-[2vh]">
        <h2 className="font-heading text-[5vh] font-bold uppercase tracking-wider text-accent">
          Combine Score
        </h2>
        <p className="text-[3vh] text-white/40">
          Scores appear once boxers have completed enough stations
        </p>
      </div>
    );
  }

  const { lo, hi } = scaleDomain(ranked.map((e) => e.combine_score));
  // "beat 33 of 38" is the line a 15-year-old reads without help, and it is a fact about
  // the ranking rather than the scale: counted from the scores themselves, so it is exactly
  // true on either basis, and boxers who tie have beaten the same people. Below two ranked
  // boxers there is nobody to have beaten, so it says nothing at all.
  const eligible = entries.filter((e) => e.eligible);
  const beatenBy = (score: number) => eligible.filter((o) => o.combine_score < score).length;
  // The score is ranked at one decimal, so two boxers can genuinely share a place.
  const tied = tiedRanks(entries.filter((e) => e.eligible));

  return (
    <div className="flex h-full flex-col gap-[1.5vh]">
      <header>
        <h2 className="font-heading text-[5vh] font-bold uppercase leading-none tracking-wider text-accent">
          Combine Score
        </h2>
        <p className="mt-[0.5vh] text-[1.8vh] uppercase tracking-widest text-white/40">
          Average standing across every station completed
          {provisional > 0 && ` · ${provisional} still in progress`}
        </p>
      </header>

      <ol className="flex min-h-0 flex-1 flex-col overflow-hidden">
        {ranked.map((entry) => {
          const isLeader = entry.rank === 1;
          return (
            <li
              key={entry.bib ?? entry.display_name}
              className="flex min-h-0 flex-1 items-center gap-[1.2vw] leading-none"
            >
              <span
                className="w-[5vw] shrink-0 text-right font-mono text-[2.3vh] font-bold tabular-nums"
                style={{ color: isLeader ? ACCENT : '#ffffff55' }}
              >
                {ordinal(entry.rank, entry.rank != null && tied.has(entry.rank))}
              </span>

              <span className="flex w-[20vw] shrink-0 flex-col justify-center gap-[0.2vh]">
                <span
                  className={`truncate text-[2.7vh] ${
                    isLeader ? 'font-bold text-white' : 'font-semibold text-white/85'
                  }`}
                >
                  {entry.display_name}
                  {entry.club && (
                    <span className="ml-[0.8vw] text-[1.8vh] font-normal text-white/35">
                      {entry.club}
                    </span>
                  )}
                </span>
                {eligible.length > 1 && (
                  <span className="text-[1.6vh] font-normal text-white/40">
                    beat {beatenBy(entry.combine_score)} of {eligible.length}
                  </span>
                )}
              </span>

              <span className="relative h-full max-h-[3.2vh] flex-1">
                <span className="absolute inset-x-0 top-1/2 h-px -translate-y-1/2 bg-white/[0.08]" />
                <span
                  className="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
                  style={{
                    left: `${positionPct(entry.combine_score, lo, hi)}%`,
                    width: isLeader ? '2.2vh' : '1.6vh',
                    height: isLeader ? '2.2vh' : '1.6vh',
                    backgroundColor: isLeader ? ACCENT : MUTED,
                    border: `2px solid ${isLeader ? '#ffffff' : '#ffffff55'}`,
                  }}
                />
              </span>

              <span className="w-[4vw] shrink-0 text-right text-[1.7vh] text-white/35">
                {entry.stations_completed}/6
              </span>
            </li>
          );
        })}
      </ol>

      {/* No axis numbers: the dots show who is close to whom, which needs no scale. */}
      <div className="flex items-center gap-[1.2vw] text-[1.6vh] text-white/30">
        <span className="w-[5vw] shrink-0" />
        <span className="shrink-0">position across the stations each boxer has completed</span>
      </div>
    </div>
  );
}
