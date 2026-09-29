'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { combineApi, ApiError } from '@/lib/api';
import type {
  CombineAttempt,
  CombineEvent,
  CombineStation,
  CombineStationRoster,
} from '@/lib/types';
import { isWithinReferenceTolerance } from '@/lib/combineLandmine';
import { NumericKeypad } from '@/components/ui/NumericKeypad';
import { ParticipantPicker } from './ParticipantPicker';
import {
  STATION_DEFINITIONS,
  buildMeasures,
  guardValue,
  isImplausible,
  liveAsymmetry,
  livePogoRsi,
  missingRequired,
  newClientAttemptId,
  rangeError,
  stationFields,
  type FieldValues,
} from './stationFields';

const ROSTER_POLL_MS = 15000;
/** How long a tapped result stays armed for removal before it disarms itself. */
const VOID_ARM_MS = 4000;

/**
 * A station screen: pick a boxer on the left, enter their attempt on the right.
 *
 * The flow is deliberately short — pick, type, save — and it stays on the boxer
 * afterwards, because most stations give each boxer several attempts.
 *
 * Two rules come from the day itself. Nothing destructive happens on one tap, and
 * a save that fails is retried with the same `client_attempt_id`, so a lost
 * response cannot become a second logged attempt.
 */
export function StationEntryScreen({
  event,
  station,
}: {
  event: CombineEvent;
  station: CombineStation;
}) {
  const definition = STATION_DEFINITIONS[station];

  const settings = useMemo(
    () => ({
      rfd_unit: event.rfd_unit,
      landmine_velocity_metric: event.landmine_velocity_metric,
    }),
    [event.rfd_unit, event.landmine_velocity_metric]
  );
  const fields = useMemo(() => stationFields(station, settings), [station, settings]);

  const [roster, setRoster] = useState<CombineStationRoster | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [values, setValues] = useState<FieldValues>({});
  const [activeField, setActiveField] = useState<string>(fields[0].key);
  const [showOptional, setShowOptional] = useState(false);
  const [attempts, setAttempts] = useState<CombineAttempt[]>([]);
  const [loadKg, setLoadKg] = useState<number>(event.landmine_reference_load_kg);
  const [side, setSide] = useState<'left' | 'right' | null>(null);
  const [sprintNumber, setSprintNumber] = useState<number>(1);
  // Identifies the payload, not the tap: minted afresh whenever the payload
  // changes, and deliberately kept across a failed or timed-out save.
  const [attemptId, setAttemptId] = useState<string>(newClientAttemptId);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rosterError, setRosterError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmOutlier, setConfirmOutlier] = useState(false);
  const [armedVoidId, setArmedVoidId] = useState<string | null>(null);

  const loadRoster = useCallback(async (): Promise<CombineStationRoster | null> => {
    try {
      const next = await combineApi.stationRoster(event.id, station);
      setRoster(next);
      setRosterError(null);
      return next;
    } catch (err) {
      // Kept apart from save errors: a background poll failing must not look like
      // the attempt in front of the operator having failed.
      setRosterError(err instanceof Error ? err.message : 'Could not refresh the roster');
      return null;
    }
  }, [event.id, station]);

  useEffect(() => {
    void loadRoster();
    const id = setInterval(() => {
      if (!document.hidden) void loadRoster();
    }, ROSTER_POLL_MS);
    return () => clearInterval(id);
  }, [loadRoster]);

  const loadAttempts = useCallback(
    async (participantId: string) => {
      try {
        setAttempts(await combineApi.listAttempts(event.id, { participantId, station }));
      } catch {
        // Leave the chips alone — they belong to this boxer, and picking another
        // clears them. Blanking here would suggest the attempts were lost.
      }
    },
    [event.id, station]
  );

  useEffect(() => {
    if (selectedId) void loadAttempts(selectedId);
  }, [selectedId, loadAttempts]);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 2600);
    return () => clearTimeout(id);
  }, [toast]);

  useEffect(() => {
    if (!armedVoidId) return;
    const id = setTimeout(() => setArmedVoidId(null), VOID_ARM_MS);
    return () => clearTimeout(id);
  }, [armedVoidId]);

  // The bike is two sprints per boxer, so offer the one they have not done.
  useEffect(() => {
    if (station !== 'air_bike') return;
    const logged = attempts
      .map((attempt) => Number(attempt.measures?.sprint_number))
      .filter((number) => Number.isFinite(number));
    setSprintNumber([1, 2].find((number) => !logged.includes(number)) ?? 2);
  }, [station, attempts]);

  const selected = roster?.entries.find((e) => e.participant_id === selectedId) ?? null;

  const cohortMax = useMemo(
    () =>
      roster?.entries.reduce<number | null>(
        (max, entry) =>
          entry.best_value != null ? Math.max(max ?? 0, entry.best_value) : max,
        null
      ) ?? null,
    [roster]
  );

  const missing = missingRequired(station, values, settings);
  const outOfRange = rangeError(station, values, settings);
  const needsSide = station === 'landmine' && side == null;
  const canSave =
    selected != null && missing.length === 0 && !outOfRange && !needsSide && !saving;

  const isReferenceLoad = isWithinReferenceTolerance(
    loadKg,
    event.landmine_reference_load_kg,
    event.landmine_reference_tolerance_kg
  );
  const guard = guardValue(station, values, {
    bodyMassKg: selected?.body_mass_kg ?? null,
    isReferenceLoad,
    velocityMetric: event.landmine_velocity_metric,
  });
  const outlier = guard != null && isImplausible(guard, cohortMax);

  /** A changed payload deserves a new id; an unchanged one being retried must not. */
  function markPayloadChanged() {
    setAttemptId(newClientAttemptId());
    setConfirmOutlier(false);
    setArmedVoidId(null);
  }

  function resetFields() {
    setValues({});
    setActiveField(fields[0].key);
    markPayloadChanged();
  }

  function selectParticipant(participantId: string) {
    setSelectedId(participantId);
    setAttempts([]);
    setSide(null);
    resetFields();
    setError(null);
  }

  /** Only on request: one logged jump rarely means the boxer is finished. */
  async function nextBoxer() {
    const fresh = (await loadRoster()) ?? roster;
    const next = (fresh?.entries ?? []).find(
      (entry) => entry.status === 'todo' && entry.participant_id !== selectedId
    );
    if (next) {
      selectParticipant(next.participant_id);
      return;
    }
    setSelectedId(null);
    setAttempts([]);
    setSide(null);
    resetFields();
  }

  async function save() {
    if (!selected || !canSave) return;
    if (outlier && !confirmOutlier) {
      setConfirmOutlier(true);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const measures = buildMeasures(station, values, {
        load_kg: loadKg,
        sprint_number: sprintNumber,
        side: side ?? undefined,
        rfd_unit: event.rfd_unit,
      });
      const saved = await combineApi.submitAttempt(event.id, {
        participant_id: selected.participant_id,
        measures,
        // Makes a retry or a double-tapped save idempotent server-side.
        client_attempt_id: attemptId,
      });
      setToast(`${selected.name} — ${saved.display_value ?? 'saved'}`);
      resetFields();
      await Promise.all([loadRoster(), loadAttempts(selected.participant_id)]);
    } catch (err) {
      // An ApiError already carries operator-facing copy, including the timeout's
      // "tap SAVE again" — and the attempt id is untouched, so that retry is safe.
      setError(
        err instanceof ApiError ? err.message : 'Could not save — check the connection'
      );
    } finally {
      setSaving(false);
    }
  }

  /** First tap arms, second removes: a stray touch on an iPad has no undo. */
  function tapAttempt(id: string) {
    if (armedVoidId !== id) {
      setArmedVoidId(id);
      return;
    }
    setArmedVoidId(null);
    void voidAttempt(id);
  }

  async function voidAttempt(attemptToVoid: string) {
    if (!selected) return;
    try {
      await combineApi.deleteAttempt(attemptToVoid);
      await Promise.all([loadRoster(), loadAttempts(selected.participant_id)]);
      setToast('Attempt removed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove that attempt');
    }
  }

  const visibleFields = fields.filter((f) => !f.optional || showOptional);
  const activeDefinition = fields.find((f) => f.key === activeField) ?? fields[0];

  const rsi = station === 'pogo' ? livePogoRsi(values) : null;
  const asymmetry =
    station === 'grip' || station === 'trunk_rotation' ? liveAsymmetry(values) : null;
  const missingBodyMass = station === 'air_bike' && selected != null && selected.body_mass_kg == null;
  const saveHint = outOfRange ?? (needsSide ? 'Pick which arm threw before saving' : null);

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(300px,1fr)_2fr]">
      <section className="card h-[calc(100vh-11rem)] min-h-[520px]">
        <ParticipantPicker
          entries={roster?.entries ?? []}
          selectedId={selectedId}
          onSelect={selectParticipant}
          done={roster?.done ?? 0}
          total={roster?.total ?? 0}
        />
      </section>

      <section className="card flex min-h-[520px] flex-col gap-4">
        {!selected ? (
          <div className="flex flex-1 items-center justify-center text-center">
            <p className="text-lg text-white/40">
              Pick a boxer to log a {definition.shortLabel} attempt
            </p>
          </div>
        ) : (
          <>
            <header className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs uppercase tracking-widest text-white/40">
                  Bib {selected.bib}
                </p>
                <h2 className="text-3xl font-bold leading-tight text-white">{selected.name}</h2>
                <p className="text-sm text-white/40">
                  {[selected.weight_category, selected.club].filter(Boolean).join(' · ') || '—'}
                </p>
              </div>

              <div className="flex flex-col items-end gap-2">
                <button
                  type="button"
                  onClick={nextBoxer}
                  className="min-h-[44px] rounded-lg bg-secondary-muted/25 px-4 text-sm font-semibold text-white/80 transition-all active:scale-[0.97]"
                >
                  Next boxer →
                </button>

                {attempts.length > 0 && (
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-widest text-white/40">Logged</p>
                    <div className="mt-1 flex flex-wrap justify-end gap-1">
                      {attempts.map((attempt) => (
                        <button
                          key={attempt.id}
                          type="button"
                          onClick={() => tapAttempt(attempt.id)}
                          title="Tap to remove this attempt"
                          className={`rounded-md px-2 py-1 font-mono text-sm tabular-nums transition-all active:scale-[0.97] ${
                            armedVoidId === attempt.id
                              ? 'bg-red-500/30 text-red-100'
                              : 'bg-secondary-muted/25 text-white/80 hover:bg-red-500/20 hover:text-red-200'
                          }`}
                        >
                          {armedVoidId === attempt.id
                            ? 'Tap again to remove'
                            : (attempt.display_value ?? '—')}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </header>

            {missingBodyMass && (
              <p className="rounded-lg bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
                No body mass for {selected.name} — the board ranks the bike in W/kg, so this
                sprint stays unranked until they are weighed in. Save it anyway; a later
                weigh-in fills it in.
              </p>
            )}

            {station === 'landmine' && (
              <div className="flex flex-wrap gap-6">
                <div>
                  <p className="text-xs uppercase tracking-widest text-white/40">Load</p>
                  <div className="mt-1 flex flex-wrap gap-2">
                    {event.landmine_loads_kg.map((load) => (
                      <button
                        key={load}
                        type="button"
                        onClick={() => {
                          setLoadKg(load);
                          markPayloadChanged();
                        }}
                        className={`relative min-h-[48px] min-w-[72px] rounded-lg px-3 font-semibold transition-all active:scale-[0.97] ${
                          loadKg === load
                            ? 'bg-accent text-[#090A3D]'
                            : 'bg-secondary-muted/20 text-white/70'
                        }`}
                      >
                        {load} kg
                        {/* The same tolerance test the engine scores on: an exact
                            match would hide the badge on a legitimately
                            within-tolerance ladder, and a badge that can be absent
                            for no reason is no signal at all. */}
                        {isWithinReferenceTolerance(
                          load,
                          event.landmine_reference_load_kg,
                          event.landmine_reference_tolerance_kg
                        ) && (
                          <span className="absolute -right-1 -top-1 rounded bg-accent px-1 text-[9px] font-bold uppercase text-[#090A3D]">
                            Ref
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs uppercase tracking-widest text-white/40">Side</p>
                  <div className="mt-1 flex gap-2">
                    {([
                      ['left', 'Left'],
                      ['right', 'Right'],
                    ] as const).map(([option, label]) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => {
                          setSide(option);
                          markPayloadChanged();
                        }}
                        className={`min-h-[48px] min-w-[72px] rounded-lg px-3 font-semibold transition-all active:scale-[0.97] ${
                          side === option
                            ? 'bg-accent text-[#090A3D]'
                            : 'bg-secondary-muted/20 text-white/70'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {station === 'air_bike' && (
              <div>
                <p className="text-xs uppercase tracking-widest text-white/40">Sprint</p>
                <div className="mt-1 flex gap-2">
                  {[1, 2].map((number) => (
                    <button
                      key={number}
                      type="button"
                      onClick={() => {
                        setSprintNumber(number);
                        markPayloadChanged();
                      }}
                      className={`min-h-[48px] flex-1 rounded-lg font-semibold transition-all active:scale-[0.97] ${
                        sprintNumber === number
                          ? 'bg-accent text-[#090A3D]'
                          : 'bg-secondary-muted/20 text-white/70'
                      }`}
                    >
                      Sprint {number}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="grid flex-1 gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                {visibleFields.map((field) => (
                  <button
                    key={field.key}
                    type="button"
                    onClick={() => setActiveField(field.key)}
                    className={`flex min-h-[64px] w-full items-center justify-between rounded-lg px-4 text-left transition-all ${
                      activeDefinition.key === field.key
                        ? 'bg-primary ring-2 ring-accent'
                        : 'bg-primary/60 hover:bg-primary'
                    }`}
                  >
                    <span className="text-sm text-white/50">
                      {field.label}
                      {field.unit && <span className="ml-1 text-white/30">({field.unit})</span>}
                    </span>
                    <span className="font-mono text-2xl tabular-nums text-white">
                      {values[field.key] || '—'}
                    </span>
                  </button>
                ))}

                {fields.some((f) => f.optional) && (
                  <button
                    type="button"
                    onClick={() => setShowOptional((v) => !v)}
                    className="text-sm text-accent/80 hover:text-accent"
                  >
                    {showOptional ? '− Hide optional fields' : '+ Optional fields'}
                  </button>
                )}

                {rsi != null && (
                  <p className="rounded-lg bg-accent/10 px-4 py-2 text-center font-mono text-xl tabular-nums text-accent">
                    RSI {rsi.toFixed(2)}
                  </p>
                )}
                {asymmetry != null && (
                  <p
                    className={`rounded-lg px-4 py-2 text-center font-mono text-xl tabular-nums ${
                      asymmetry < 10
                        ? 'bg-green-500/10 text-green-400'
                        : asymmetry <= 15
                          ? 'bg-yellow-500/10 text-yellow-400'
                          : 'bg-red-500/10 text-red-400'
                    }`}
                  >
                    {asymmetry.toFixed(1)}% asymmetry
                  </p>
                )}
                {definition.hint && (
                  <p className="text-xs leading-relaxed text-white/30">{definition.hint}</p>
                )}
              </div>

              <div className="space-y-3">
                <NumericKeypad
                  value={values[activeDefinition.key] ?? ''}
                  onChange={(value) => {
                    setValues((current) => ({ ...current, [activeDefinition.key]: value }));
                    markPayloadChanged();
                  }}
                  maxDecimals={activeDefinition.maxDecimals}
                  maxIntegerDigits={activeDefinition.maxIntegerDigits}
                  disabled={saving}
                />
                <button
                  type="button"
                  onClick={save}
                  disabled={!canSave}
                  className={`min-h-[64px] w-full rounded-xl text-lg font-bold uppercase tracking-wide transition-all active:scale-[0.98] disabled:opacity-30 ${
                    outlier && !confirmOutlier
                      ? 'bg-amber-400 text-[#090A3D]'
                      : 'bg-accent text-[#090A3D]'
                  }`}
                >
                  {saving
                    ? 'Saving…'
                    : outlier && !confirmOutlier
                      ? 'That looks high — tap again to confirm'
                      : `Save attempt ${attempts.length + 1}`}
                </button>
                {saveHint && (
                  <p className="text-center text-sm text-amber-300">{saveHint}</p>
                )}
              </div>
            </div>
          </>
        )}

        {rosterError && (
          <p className="rounded-lg bg-amber-500/10 px-4 py-2 text-sm text-amber-200">
            {rosterError}
          </p>
        )}
        {error && (
          <p className="rounded-lg bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</p>
        )}
      </section>

      {toast && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-xl bg-accent px-6 py-3 text-lg font-semibold text-[#090A3D] shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
