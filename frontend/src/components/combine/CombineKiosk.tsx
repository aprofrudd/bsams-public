'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { CombineLeaderboard, CombineStation } from '@/lib/types';
import { combineApi } from '@/lib/api';
import { useCombinePolling } from '@/lib/hooks/useCombinePolling';
import { useCombineRotation } from '@/lib/hooks/useCombineRotation';
import { useWakeLock } from '@/lib/hooks/useWakeLock';
import {
  CONNECTION_COLORS,
  CONNECTION_LABELS,
  KIOSK_PANELS,
  clampRotateSeconds,
  connectionState,
  normalisePanelParam,
  panelLabel,
} from '@/lib/combineDisplay';
import { StationPanel } from './StationPanel';
import { SummaryPanel } from './SummaryPanel';
import { OverallPanel } from './OverallPanel';

const POLL_MS = 5000;

/**
 * The gym big screen.
 *
 * Public and unauthenticated — it is driven entirely by the share token in the URL.
 * `?panel=cmj` pins one station so two screens can show different tests;
 * `?rotate=15` changes the dwell; `?wc=57kg` filters to a weight category.
 *
 * The parameters are typed by hand onto a TV browser, so they are read
 * forgivingly: an unrecognised panel rotates and the dwell is clamped to 5-300s,
 * because a mistyped link that shows nothing is the worst outcome in a full hall.
 */
export function CombineKiosk({ token }: { token: string }) {
  const searchParams = useSearchParams();
  // `?panel=` seeds the pin; after that the button owns it. history.replaceState
  // does not re-run useSearchParams, so local state is the source of truth once
  // touched, and the URL is kept in step only so a refresh or a copied link lands
  // on the same panel.
  const [pinOverride, setPinOverride] = useState<string | null | undefined>(undefined);
  const pinned =
    pinOverride === undefined ? normalisePanelParam(searchParams.get('panel')) : pinOverride;

  const setPin = useCallback((next: string | null) => {
    setPinOverride(next);
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    if (next) url.searchParams.set('panel', next);
    else url.searchParams.delete('panel');
    window.history.replaceState(null, '', url.toString());
  }, []);
  const rotateSeconds = clampRotateSeconds(searchParams.get('rotate'));
  const filters = useMemo(
    () => ({
      weight_category: searchParams.get('wc') ?? undefined,
      age_group: searchParams.get('age') ?? undefined,
      club: searchParams.get('club') ?? undefined,
    }),
    [searchParams]
  );

  const url = useMemo(
    () => combineApi.publicLeaderboardPath(token, filters),
    [token, filters]
  );

  const { data, error, loading, staleSeconds, lastUpdated } = useCombinePolling<CombineLeaderboard>(
    url,
    POLL_MS
  );

  const { acquire, release } = useWakeLock();
  useEffect(() => {
    void acquire();
    return release;
  }, [acquire, release]);

  // Skip stations nobody has reached yet — an empty panel wastes 20 seconds of screen
  // time — but never leave the board with nothing on it.
  const available = useMemo(() => {
    if (!data) return [];
    const anyResults = data.stations.some((s) => s.completed > 0);
    const withResults = KIOSK_PANELS.filter((key) => {
      // The summary is worth showing as soon as anything has been logged — it is
      // the only panel that reports the stations still at zero.
      if (key === 'summary') return anyResults;
      if (key === 'overall') return data.overall.some((e) => e.eligible);
      return (data.stations.find((s) => s.station === key)?.completed ?? 0) > 0;
    });
    return withResults.length > 0 ? withResults : [KIOSK_PANELS[0]];
  }, [data]);

  const { active, index, total, isPinned } = useCombineRotation(available as string[], {
    intervalMs: rotateSeconds * 1000,
    pinned,
  });

  const state = connectionState(staleSeconds, Boolean(error));

  if (loading && !data) {
    return (
      <div className="flex h-screen items-center justify-center bg-primary">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-accent border-t-transparent" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-primary px-8 text-center">
        <h1 className="font-heading text-[4vh] font-bold uppercase tracking-wider text-accent">
          Board unavailable
        </h1>
        <p className="text-[2.4vh] text-white/60">
          {error ?? 'This link may have expired or been turned off.'}
        </p>
      </div>
    );
  }

  const panel =
    active && active !== 'overall' && active !== 'summary'
      ? data.stations.find((s) => s.station === (active as CombineStation))
      : undefined;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-primary px-[3vw] py-[2.5vh] text-white">
      <header className="flex shrink-0 items-center justify-between pb-[2vh]">
        <div className="flex items-baseline gap-[1.5vw]">
          <h1 className="font-heading text-[3vh] font-bold uppercase tracking-widest text-white">
            {data.event_name}
          </h1>
          {data.venue && (
            <span className="text-[1.8vh] uppercase tracking-widest text-white/30">
              {data.venue}
            </span>
          )}
        </div>

        <div className="flex items-center gap-[1.5vw]">
          <span className="text-[1.8vh] uppercase tracking-widest text-white/40">
            {data.participant_count} boxers
          </span>
          <span className="flex items-center gap-[0.6vw]">
            <span
              className={`inline-block h-[1.2vh] w-[1.2vh] rounded-full ${
                state === 'live' ? 'animate-pulse' : ''
              }`}
              style={{ backgroundColor: CONNECTION_COLORS[state] }}
            />
            <span
              className="text-[1.8vh] font-semibold uppercase tracking-widest"
              style={{ color: CONNECTION_COLORS[state] }}
            >
              {CONNECTION_LABELS[state]}
            </span>
          </span>
        </div>
      </header>

      {state === 'offline' && (
        <div className="mb-[1.5vh] shrink-0 rounded-lg bg-red-500/15 px-[1.5vw] py-[1vh] text-center text-[2vh] text-red-300">
          Showing results from{' '}
          {lastUpdated?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) ?? 'earlier'}
          {' '}— trying to reconnect
        </div>
      )}

      <main className="min-h-0 flex-1">
        {active === 'summary' ? (
          <SummaryPanel board={data} />
        ) : active === 'overall' ? (
          <OverallPanel board={data} />
        ) : panel ? (
          <StationPanel panel={panel} participantCount={data.participant_count} />
        ) : null}
      </main>

      {/* The dots double as the pin control. A TV is never touched, so this stays
          quiet; it is for the operator's laptop or a tablet held at the desk. */}
      <footer className="flex shrink-0 items-center justify-center gap-[0.8vw] pt-[1.5vh]">
        {total > 1 &&
          available.map((key, dot) => (
            <button
              key={key}
              type="button"
              onClick={() => setPin(pinned === key ? null : key)}
              aria-label={`${pinned === key ? 'Unpin' : 'Pin'} the ${panelLabel(key)} panel`}
              className={`h-[0.9vh] rounded-full transition-all ${
                dot === index ? 'w-[3vw] bg-accent' : 'w-[0.9vh] bg-white/20 hover:bg-white/50'
              }`}
            />
          ))}
        {active && (
          <button
            type="button"
            onClick={() => setPin(isPinned ? null : active)}
            className="ml-[1vw] rounded px-[0.8vw] py-[0.3vh] text-[1.5vh] uppercase tracking-widest text-white/35 transition-colors hover:bg-white/10 hover:text-white/80"
          >
            {isPinned ? `Pinned · ${panelLabel(active)} · resume` : `Pin ${panelLabel(active)}`}
          </button>
        )}
      </footer>
    </div>
  );
}
