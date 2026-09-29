'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { combineApi, ApiError } from '@/lib/api';
import type { CombineEvent, CombineParticipant, CombineStationRoster } from '@/lib/types';
import { STATION_DEFINITIONS } from '@/components/combine/stations/stationFields';
import { RosterImport } from '@/components/combine/RosterImport';
import { ParticipantFormModal } from '@/components/combine/ParticipantFormModal';
import {
  isWithinReferenceTolerance,
  nearestLadderLoad,
  referenceLoadWarning,
} from '@/lib/combineLandmine';

const STATIONS = Object.keys(STATION_DEFINITIONS) as (keyof typeof STATION_DEFINITIONS)[];

/** Norm keys as `bs_norms_coverage` reports them, in the words used elsewhere. */
const SCORE_KEY_LABELS: Record<string, string> = {
  height_cm: 'CMJ',
  pogo_rsi: 'Pogo',
  landmine_velocity_ms: 'Punch',
  grip_best_kg: 'Grip',
  trunk_rotation_best_kg: 'Rotation',
  air_bike_power_7s_wkg: 'Bike',
};

const GENDER_LABELS: Record<string, string> = { male: 'men', female: 'women' };

/** Under this many reference athletes the engine withholds the band entirely. */
const MIN_NORM_N = 20;

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** A combine is booked a season or so either side of today; anything else is a typo. */
const EVENT_DATE_WINDOW_YEARS = 2;

function yearsFromToday(years: number): string {
  const date = new Date();
  date.setFullYear(date.getFullYear() + years);
  return date.toISOString().slice(0, 10);
}

/** "1 boxer" / "3 boxers" — the count is the whole point of the message. */
function boxers(count: number): string {
  return `${count} ${count === 1 ? 'boxer' : 'boxers'}`;
}

export default function CombineConsolePage({
  params,
}: {
  params: { eventId: string };
}) {
  const { eventId } = params;
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [event, setEvent] = useState<CombineEvent | null>(null);
  const [participants, setParticipants] = useState<CombineParticipant[]>([]);
  const [progress, setProgress] = useState<CombineStationRoster[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  // null = closed; 'new' = adding; otherwise the participant being edited
  const [editing, setEditing] = useState<CombineParticipant | 'new' | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [showPaste, setShowPaste] = useState(false);
  const [venueDraft, setVenueDraft] = useState<string | null>(null);
  const [dateDraft, setDateDraft] = useState<string | null>(null);
  // Outlives the toast: a boxer whose result never reached their athlete record has
  // to stay on screen until someone acts on it.
  const [unsynced, setUnsynced] = useState(0);
  // Settings are typed, not stepped: each holds a draft until it is committed, so a
  // half-typed ladder never reaches the stations.
  const [ladderDraft, setLadderDraft] = useState<string | null>(null);
  const [refLoadDraft, setRefLoadDraft] = useState<string | null>(null);
  const [toleranceDraft, setToleranceDraft] = useState<string | null>(null);

  useEffect(() => {
    if (loading) return;
    // Come back to this console after signing in, rather than landing on /training.
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (user.role === 'athlete') router.replace('/training');
  }, [loading, user, router, pathname]);

  const load = useCallback(async () => {
    try {
      const [loadedEvent, roster] = await Promise.all([
        combineApi.getEvent(eventId),
        combineApi.listParticipants(eventId),
      ]);
      setEvent(loadedEvent);
      setParticipants(roster);
      setProgress(
        await Promise.all(STATIONS.map((station) => combineApi.stationRoster(eventId, station)))
      );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load this combine');
    }
  }, [eventId]);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 3000);
    return () => clearTimeout(id);
  }, [toast]);

  async function patch(update: Parameters<typeof combineApi.updateEvent>[1]) {
    setBusy(true);
    try {
      setEvent(await combineApi.updateEvent(eventId, update));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update the combine');
    } finally {
      setBusy(false);
    }
  }

  /**
   * One path for the actions that change what the room sees.
   *
   * Each one confirms where it is destructive, blocks a double tap, says what went
   * wrong, and says what went right — a silent button is indistinguishable from a
   * broken one when the TV is behind you.
   */
  async function runAction<T>(
    action: () => Promise<T>,
    opts: {
      confirm?: string;
      // A formatter where the toast has to report what came back, rather than assume
      // it went well: re-sync says how many boxers did not write.
      success: string | ((result: T) => string);
      failure: string;
    }
  ): Promise<T | undefined> {
    if (busy) return undefined;
    if (opts.confirm && !window.confirm(opts.confirm)) return undefined;
    setBusy(true);
    try {
      const result = await action();
      await load();
      setError(null);
      setToast(typeof opts.success === 'function' ? opts.success(result) : opts.success);
      return result;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : opts.failure);
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  async function copyShareLink() {
    if (!event) return;
    const url = `${window.location.origin}${event.share_url_path}`;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Could not copy — the link is shown below.');
    }
  }

  if (loading || !user || user.role === 'athlete') return null;

  if (!event) {
    return error ? (
      <div className="card">
        <p className="text-red-300">{error}</p>
        <Link href="/combine" className="mt-3 inline-block text-accent">
          Back to combines
        </Link>
      </div>
    ) : (
      <div className="flex justify-center py-16">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  // Arrow consts, not declarations: these close over the loaded `event` above, and a
  // hoisted function would not.
  const commitLadder = () => {
    const draft = ladderDraft;
    setLadderDraft(null);
    if (draft === null || draft.trim() === event.landmine_loads_kg.join(', ')) return;

    const loads = draft
      .split(',')
      .map((part) => part.trim())
      .filter(Boolean)
      .map(Number);
    if (
      loads.length === 0 ||
      loads.length > 12 ||
      loads.some((load) => !Number.isFinite(load) || load <= 0 || load > 100)
    ) {
      setError('Landmine loads must be 1 to 12 numbers, each between 0 and 100 kg.');
      return;
    }
    // A new ladder that leaves the reference load stranded is refused by the API,
    // and the admin cannot move the reference first either — it would then be off
    // the old ladder. So move it onto the nearest new load in the same PATCH, and
    // say so rather than changing the scored load silently.
    const nearest = nearestLadderLoad(loads, event.landmine_reference_load_kg);
    if (
      nearest != null &&
      !isWithinReferenceTolerance(
        nearest,
        event.landmine_reference_load_kg,
        event.landmine_reference_tolerance_kg
      )
    ) {
      setToast(`Reference load moved to ${nearest} kg — the board only ranks that load.`);
      void patch({ landmine_loads_kg: loads, landmine_reference_load_kg: nearest });
      return;
    }
    void patch({ landmine_loads_kg: loads });
  };

  const commitReferenceLoad = () => {
    const draft = refLoadDraft;
    setRefLoadDraft(null);
    if (draft === null) return;
    const value = Number(draft.trim());
    if (!draft.trim() || !Number.isFinite(value) || value <= 0 || value > 100) {
      setError('The reference load must be a number between 0 and 100 kg.');
      return;
    }
    // The mistake this catches: the real ladder typed in, the default reference
    // load left behind. Every throw would still save and none would be ranked.
    const warning = referenceLoadWarning(
      event.landmine_loads_kg,
      value,
      event.landmine_reference_tolerance_kg
    );
    if (warning) {
      setError(warning);
      return;
    }
    if (value !== event.landmine_reference_load_kg) {
      void patch({ landmine_reference_load_kg: value });
    }
  };

  const commitTolerance = () => {
    const draft = toleranceDraft;
    setToleranceDraft(null);
    if (draft === null) return;
    const value = Number(draft.trim());
    if (!draft.trim() || !Number.isFinite(value) || value < 0 || value > 10) {
      setError('The tolerance must be a number between 0 and 10 kg.');
      return;
    }
    if (value !== event.landmine_reference_tolerance_kg) {
      void patch({ landmine_reference_tolerance_kg: value });
    }
  };

  const dateMin = yearsFromToday(-EVENT_DATE_WINDOW_YEARS);
  const dateMax = yearsFromToday(EVENT_DATE_WINDOW_YEARS);

  const commitEventDate = () => {
    const draft = dateDraft;
    setDateDraft(null);
    if (draft === null || draft === event.event_date) return;
    // A type="date" input publishes a complete value for every intermediate year a
    // keyboard edit passes through, so "0002-09-19" is a real onChange. The API moves
    // the share link's expiry to whatever date it is sent, and rotating the link
    // recomputes it the same way — so a mangled year kills the board, and once an
    // attempt exists the date is frozen and it cannot be corrected on the day.
    if (!/^\d{4}-\d{2}-\d{2}$/.test(draft) || draft < dateMin || draft > dateMax) {
      setError(`The event date must be a date between ${dateMin} and ${dateMax}.`);
      return;
    }
    void patch({ event_date: draft });
  };

  // Standing warning, not just an on-commit one: an event configured through the
  // API, or before this check existed, shows the same empty Punch panel.
  const ladderWarning = referenceLoadWarning(
    event.landmine_loads_kg,
    event.landmine_reference_load_kg,
    event.landmine_reference_tolerance_kg
  );

  const missingBodyMass = participants.filter(
    (p) => p.body_mass_kg == null && p.withdrawn_at == null
  ).length;
  const consentGiven = Boolean(event.public_display_consent_confirmed_at);
  const isLive = event.status === 'live';
  const isAdmin = user.role === 'admin';
  const linkExpired = new Date(event.share_token_expires_at).getTime() < Date.now();

  // Which norms are too thin to band. Counts only — a mean or an SD here would hand
  // over the reference distribution.
  const thinNorms = Object.entries(event.bs_norms_coverage ?? {}).flatMap(([key, byGender]) =>
    Object.entries(byGender)
      .filter(([, n]) => n < MIN_NORM_N)
      .map(([gender, n]) => `${SCORE_KEY_LABELS[key] ?? key} (${GENDER_LABELS[gender] ?? gender}) ${n}`)
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link
            href="/combine"
            className="text-xs uppercase tracking-widest text-white/40 hover:text-white/70"
          >
            ← Combines
          </Link>
          <h1 className="section-title text-2xl">{event.event_name}</h1>
          <p className="text-sm text-white/40">
            {new Date(event.event_date).toLocaleDateString('en-GB', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}{' '}
            · {event.participant_count} boxers
          </p>
          {/* Editable in place — a location typed at 8am should be fixable at 9am,
              and it is what the big screen shows beside the event name. The date sits
              beside it: a combine booked for the wrong Saturday is caught here, and
              moving it also moves the share link's expiry. */}
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <input
              value={venueDraft ?? event.venue ?? ''}
              onChange={(e) => setVenueDraft(e.target.value)}
              onBlur={() => {
                const next = (venueDraft ?? '').trim();
                if (venueDraft !== null && next !== (event.venue ?? '')) {
                  void patch({ venue: next });
                }
                setVenueDraft(null);
              }}
              placeholder="+ Add a location"
              aria-label="Location"
              className="w-full max-w-xs rounded border border-transparent bg-transparent px-2 py-1 text-sm text-white/60 transition-colors placeholder:text-white/25 hover:border-secondary-muted/60 focus:border-accent focus:text-white focus:outline-none"
            />
            {/* Draft-plus-commit like the venue beside it, and deliberately not
                disabled while a PATCH is in flight: a field the operator may still be
                typing into must not swallow the rest of the year. */}
            <input
              type="date"
              value={dateDraft ?? event.event_date}
              onChange={(e) => setDateDraft(e.target.value)}
              onBlur={commitEventDate}
              onKeyDown={(e) => {
                if (e.key === 'Enter') e.currentTarget.blur();
              }}
              min={dateMin}
              max={dateMax}
              aria-label="Event date"
              className="rounded border border-transparent bg-transparent px-2 py-1 text-sm text-white/60 transition-colors hover:border-secondary-muted/60 focus:border-accent focus:text-white focus:outline-none"
            />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => patch({ status: isLive ? 'closed' : 'live' })}
            disabled={busy || (!isLive && !consentGiven)}
            title={!consentGiven ? 'Confirm public display first' : undefined}
            className="btn-primary disabled:opacity-40"
          >
            {isLive ? 'Close event' : 'Go live'}
          </button>
          <button
            type="button"
            onClick={async () => {
              const board = await runAction(() => combineApi.sync(eventId), {
                // No confirm: re-syncing rebuilds the same rows from the attempts.
                success: (result) =>
                  (result.unsynced_count ?? 0) > 0
                    ? `Re-synced — ${boxers(result.unsynced_count ?? 0)} did not fully write`
                    : 'Results re-synced',
                failure: 'Could not re-sync results',
              });
              // Read from the POST, not from state refreshed by load(): the coach GET
              // hardcodes 0, so a board-sourced count would reset itself immediately.
              // A failed re-sync leaves the standing warning alone.
              if (board) setUnsynced(board.unsynced_count ?? 0);
            }}
            disabled={busy}
            className="btn-secondary disabled:opacity-40"
          >
            Re-sync results
          </button>
          {isAdmin && (
            <button
              type="button"
              onClick={() =>
                runAction(() => combineApi.refreshNorms(eventId), {
                  success: 'Boxing Science bands refreshed',
                  failure: 'Could not refresh the bands',
                })
              }
              disabled={busy}
              className="btn-secondary disabled:opacity-40"
            >
              Refresh Boxing Science bands
            </button>
          )}
        </div>
      </div>

      {isAdmin && (
        <p className="text-xs text-white/40">
          Boxing Science bands:{' '}
          {event.bs_norms_updated_at
            ? `refreshed ${formatDateTime(event.bs_norms_updated_at)}`
            : 'never refreshed — the board shows no bands until you do'}
          {thinNorms.length > 0 && (
            <span className="text-amber-300">
              {' '}
              · fewer than {MIN_NORM_N} reference athletes, so no band: {thinNorms.join(', ')}
            </span>
          )}
        </p>
      )}

      {error && <p className="rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</p>}

      {/* Standing, not a three-second toast: pressing Re-sync again is exactly what
          does not fix this, so it has to outlast a glance away from the console. */}
      {unsynced > 0 && (
        <p className="rounded-lg bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
          {boxers(unsynced)} did not fully write to their athlete record. Every attempt is still
          saved — check the backend logs, then re-sync again.
        </p>
      )}

      {/* Public display consent — required before any name reaches the wall */}
      {!consentGiven && (
        <div className="card border-amber-400/40 bg-amber-400/5">
          <h2 className="section-title text-sm text-amber-300">Before you go live</h2>
          <p className="mt-2 text-sm leading-relaxed text-white/70">
            The big screen is a public link with no login. Most of these boxers are under 18, so
            confirm you have consent to show their names and results on a screen anyone in the room
            can see. You can switch to initials or bib numbers below instead.
          </p>
          <button
            type="button"
            onClick={() => patch({ public_display_consent_confirmed: true })}
            disabled={busy}
            className="btn-primary mt-3 disabled:opacity-40"
          >
            I have consent to display these results
          </button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Stations */}
        <section className="card">
          <h2 className="section-title text-sm">Stations</h2>
          <ul className="mt-3 space-y-2">
            {progress.map((station) => (
              <li key={station.station}>
                <Link
                  href={`/combine/${eventId}/station/${station.station}`}
                  className="flex min-h-[56px] items-center gap-3 rounded-lg bg-primary px-3 transition-all hover:bg-secondary-muted/20"
                >
                  <span className="flex-1 font-semibold text-white">{station.label}</span>
                  <span className="w-28">
                    <span className="block h-1.5 overflow-hidden rounded-full bg-secondary-muted/30">
                      <span
                        className="block h-full rounded-full bg-accent"
                        style={{
                          width: `${station.total ? (station.done / station.total) * 100 : 0}%`,
                        }}
                      />
                    </span>
                  </span>
                  <span className="w-16 text-right font-mono text-sm tabular-nums text-white/50">
                    {station.done}/{station.total}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        {/* Big screen */}
        <section className="card">
          <h2 className="section-title text-sm">Big screen</h2>
          <p className="mt-2 text-sm text-white/50">
            Open this on the gym TV. It needs no login and updates every few seconds.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <a
              href={event.share_url_path}
              target="_blank"
              rel="noreferrer"
              className="btn-primary"
            >
              Open board
            </a>
            <button type="button" onClick={copyShareLink} className="btn-secondary">
              {copied ? 'Copied' : 'Copy link'}
            </button>
            <button
              type="button"
              onClick={() =>
                runAction(() => combineApi.rotateToken(eventId), {
                  confirm:
                    'Create a new link? The TV goes blank until someone opens the board again on the new link.',
                  success: 'New link created — reopen the board on the TV',
                  failure: 'Could not create a new link',
                })
              }
              disabled={busy}
              className="btn-secondary disabled:opacity-40"
            >
              New link
            </button>
            <button
              type="button"
              onClick={() =>
                runAction(() => combineApi.revokeToken(eventId), {
                  confirm:
                    'Turn the board off? Every screen showing it clears within about a minute.',
                  success: 'Board turned off',
                  failure: 'Could not turn the board off',
                })
              }
              disabled={busy}
              className="btn-secondary disabled:opacity-40"
            >
              Turn off
            </button>
          </div>
          <p className="mt-2 break-all font-mono text-xs text-white/30">{event.share_url_path}</p>
          {event.share_revoked_at ? (
            <p className="mt-1 text-xs text-amber-300">
              This link is switched off. Use “New link” to bring the board back.
            </p>
          ) : (
            <p className={`mt-1 text-xs ${linkExpired ? 'text-amber-300' : 'text-white/30'}`}>
              {linkExpired
                ? `This link expired on ${formatDateTime(event.share_token_expires_at)}. Use “New link” to bring the board back.`
                : `Link valid until ${formatDateTime(event.share_token_expires_at)}`}
            </p>
          )}

          <div className="mt-4 space-y-2">
            <label className="text-xs uppercase tracking-widest text-white/40">
              Names on the screen
            </label>
            <div className="flex flex-wrap gap-1">
              {(
                [
                  ['full', 'Full name'],
                  ['first_initial', 'Jack R.'],
                  ['first_only', 'First name'],
                  ['bib', 'Bib only'],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => patch({ public_name_style: value })}
                  className={`min-h-[44px] rounded-lg px-3 text-sm transition-all ${
                    event.public_name_style === value
                      ? 'bg-accent text-[#090A3D]'
                      : 'bg-secondary-muted/20 text-white/60'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <label className="flex min-h-[44px] items-center gap-2 text-sm text-white/60">
              <input
                type="checkbox"
                checked={event.show_club}
                onChange={(e) => patch({ show_club: e.target.checked })}
              />
              Show club names
            </label>
          </div>
        </section>
      </div>

      {/* Event settings — set before the first attempt */}
      <section className="card">
        <h2 className="section-title text-sm">Event settings</h2>
        <p className="mt-2 text-sm text-white/50">
          Set these before the first boxer steps up. The ladder is what the landmine station
          offers, and the board ranks the reference load only.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-widest text-white/40">
              Landmine loads (kg)
            </label>
            <input
              value={ladderDraft ?? event.landmine_loads_kg.join(', ')}
              onChange={(e) => setLadderDraft(e.target.value)}
              onBlur={commitLadder}
              disabled={busy}
              placeholder="10, 15, 20, 25"
              aria-label="Landmine loads in kilograms"
              className="input mt-1 w-full"
            />
            <p className="mt-1 text-xs text-white/30">
              1 to 12 loads, each between 0 and 100 kg, separated by commas.
            </p>
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">
              Reference load (kg)
            </label>
            <input
              value={refLoadDraft ?? String(event.landmine_reference_load_kg)}
              onChange={(e) => setRefLoadDraft(e.target.value)}
              onBlur={commitReferenceLoad}
              disabled={busy}
              inputMode="decimal"
              aria-label="Landmine reference load"
              className="input mt-1 w-full"
            />
            <p className="mt-1 text-xs text-white/30">
              Must be one of the ladder loads — it is the only one the board ranks.
            </p>
            {ladderWarning && (
              <p className="mt-1 text-xs text-amber-200">{ladderWarning}</p>
            )}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">
              Reference tolerance (kg)
            </label>
            <input
              value={toleranceDraft ?? String(event.landmine_reference_tolerance_kg)}
              onChange={(e) => setToleranceDraft(e.target.value)}
              onBlur={commitTolerance}
              disabled={busy}
              inputMode="decimal"
              aria-label="Landmine reference tolerance"
              className="input mt-1 w-full"
            />
            <p className="mt-1 text-xs text-white/30">
              How far off the reference load an attempt can be and still count.
            </p>
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-widest text-white/40">RFD unit</label>
            <div className="mt-1 flex flex-wrap gap-1">
              {(
                [
                  ['n_s', 'N/s'],
                  ['kg_s', 'kg/s'],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => patch({ rfd_unit: value })}
                  disabled={busy}
                  className={`min-h-[44px] rounded-lg px-4 text-sm transition-all disabled:opacity-40 ${
                    event.rfd_unit === value
                      ? 'bg-accent text-[#090A3D]'
                      : 'bg-secondary-muted/20 text-white/60'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-1 text-xs text-white/30">
              What the dynamometers here read. Results are stored in N/s either way — kg/s is
              converted on the way in, so set this before the grip and rotation stations start.
            </p>
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs uppercase tracking-widest text-white/40">
              Combine Score basis
            </label>
            <div className="mt-1 flex flex-wrap gap-1">
              {(
                [
                  ['z', 'T-score, 50 is the room average'],
                  ['percentile', 'Percentile, share of the room beaten'],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => patch({ overall_score_basis: value })}
                  disabled={busy}
                  className={`min-h-[44px] rounded-lg px-4 text-sm transition-all disabled:opacity-40 ${
                    event.overall_score_basis === value
                      ? 'bg-accent text-[#090A3D]'
                      : 'bg-secondary-muted/20 text-white/60'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <p className="mt-1 text-xs text-white/30">
              The board relabels itself to match and the order barely moves — percentiles only
              stop one freak result on a skewed test inflating a score. Safe to change mid-event:
              scores are worked out fresh on every board refresh.
            </p>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="section-title text-sm">Roster</h2>
          <div className="flex flex-wrap items-center gap-3">
            {missingBodyMass > 0 && (
              <span
                className="text-sm text-amber-300"
                title="Body mass is needed for W/kg on the air bike"
              >
                {missingBodyMass} missing body mass
              </span>
            )}
            <button
              type="button"
              onClick={() => setShowPaste((v) => !v)}
              className="text-sm text-accent/80 hover:text-accent"
            >
              {showPaste ? 'Hide paste import' : 'Paste a list'}
            </button>
            <button type="button" onClick={() => setEditing('new')} className="btn-primary">
              + Add boxer
            </button>
          </div>
        </div>

        {showPaste && (
          <div className="mt-3 rounded-lg border border-secondary-muted/40 p-3">
            <RosterImport eventId={eventId} onImported={load} />
          </div>
        )}

        <ul className="mt-3 max-h-96 space-y-1 overflow-y-auto">
          {participants.map((participant) => (
            <li key={participant.id}>
              <button
                type="button"
                onClick={() => setEditing(participant)}
                className={`flex min-h-[48px] w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-all hover:bg-secondary-muted/25 active:scale-[0.99] ${
                  participant.withdrawn_at ? 'bg-primary/40 opacity-50' : 'bg-primary'
                }`}
              >
                <span className="w-8 font-mono text-sm tabular-nums text-white/40">
                  {participant.bib}
                </span>
                <span className="flex-1 truncate text-sm text-white">
                  {participant.name}
                  {participant.withdrawn_at && (
                    <span className="ml-2 text-xs uppercase tracking-widest text-white/30">
                      withdrawn
                    </span>
                  )}
                </span>
                <span className="hidden text-xs text-white/40 sm:inline">
                  {[participant.weight_category, participant.club].filter(Boolean).join(' · ')}
                </span>
                <span
                  className={`w-16 text-right font-mono text-xs tabular-nums ${
                    participant.body_mass_kg == null ? 'text-amber-300' : 'text-white/40'
                  }`}
                >
                  {participant.body_mass_kg != null ? `${participant.body_mass_kg} kg` : 'no mass'}
                </span>
              </button>
            </li>
          ))}
          {participants.length === 0 && (
            <li className="py-6 text-center text-sm text-white/30">
              No boxers yet — add them one at a time, or paste a list.
            </li>
          )}
        </ul>
      </section>

      <ParticipantFormModal
        eventId={eventId}
        participant={editing === 'new' ? null : editing}
        existingParticipants={participants}
        isOpen={editing !== null}
        onClose={() => setEditing(null)}
        onSaved={(message) => {
          setToast(message);
          void load();
        }}
      />

      {toast && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-accent px-6 py-3 font-semibold text-[#090A3D] shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
