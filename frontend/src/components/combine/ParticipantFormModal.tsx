'use client';

import { useEffect, useMemo, useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { athletesApi, combineApi, ApiError } from '@/lib/api';
import type { CombineParticipant } from '@/lib/types';
import {
  AGE_GROUP_SUGGESTIONS,
  EMPTY_PARTICIPANT,
  WEIGHT_CATEGORIES,
  fromParticipant,
  hasErrors,
  toAthleteUpdate,
  toParticipantUpdate,
  toRosterRow,
  validateParticipant,
  type FormErrors,
  type ParticipantFormValues,
} from '@/lib/combineParticipantForm';

/**
 * Add or edit one boxer on the roster.
 *
 * The paste-a-list import is right for a roster sent ahead of time; this is for the
 * ones who turn up on the day, and for filling in the weigh-in afterwards. Only a
 * name and a gender are required, so a boxer can be added at the door in seconds and
 * the rest completed when they reach a station.
 */
export function ParticipantFormModal({
  eventId,
  participant,
  existingParticipants,
  isOpen,
  onClose,
  onSaved,
}: {
  eventId: string;
  /** null = adding a new boxer */
  participant: CombineParticipant | null;
  existingParticipants: CombineParticipant[];
  isOpen: boolean;
  onClose: () => void;
  onSaved: (message: string) => void;
}) {
  const isEdit = participant != null;
  const [values, setValues] = useState<ParticipantFormValues>(EMPTY_PARTICIPANT);
  const [errors, setErrors] = useState<FormErrors>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addAnother, setAddAnother] = useState(true);

  useEffect(() => {
    if (!isOpen) return;
    setValues(participant ? fromParticipant(participant) : EMPTY_PARTICIPANT);
    setErrors({});
    setError(null);
  }, [isOpen, participant]);

  const takenBibs = useMemo(
    () => existingParticipants.map((p) => p.bib).filter((b): b is number => b != null),
    [existingParticipants]
  );

  // Offer what this event is already using, so categories stay consistent.
  const clubOptions = useMemo(
    () => Array.from(new Set(existingParticipants.map((p) => p.club).filter(Boolean))) as string[],
    [existingParticipants]
  );
  // Fixed vocabulary, not suggestions: the backend rejects anything else, and an
  // invented division would sit in the board's filter chips matching one boxer. A
  // legacy value already on the record is kept so editing does not silently change it.
  const weightOptions = useMemo(() => {
    const current = participant?.weight_category;
    return current && !WEIGHT_CATEGORIES.includes(current)
      ? [current, ...WEIGHT_CATEGORIES]
      : WEIGHT_CATEGORIES;
  }, [participant]);
  const ageOptions = useMemo(() => {
    const used = existingParticipants.map((p) => p.age_group).filter(Boolean) as string[];
    return Array.from(new Set([...used, ...AGE_GROUP_SUGGESTIONS]));
  }, [existingParticipants]);

  const nextBib = useMemo(
    () => (takenBibs.length ? Math.max(...takenBibs) + 1 : 1),
    [takenBibs]
  );

  function set<K extends keyof ParticipantFormValues>(key: K, value: ParticipantFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();

    const found = validateParticipant(values, {
      takenBibs,
      currentBib: participant?.bib ?? null,
    });
    setErrors(found);
    if (hasErrors(found)) return;

    setSaving(true);
    setError(null);
    try {
      if (isEdit && participant) {
        await combineApi.updateParticipant(participant.id, toParticipantUpdate(values));
        // Name, gender and body mass live on the athlete record, not the roster entry —
        // and only reach it when they actually changed, so a weigh-in cannot rewrite
        // a name the form only guessed at.
        const athleteUpdate = toAthleteUpdate(values, participant);
        if (athleteUpdate) {
          await athletesApi.update(participant.athlete_id, athleteUpdate);
        }
        onSaved(`${values.first_name} updated`);
        onClose();
      } else {
        // Reuses the roster import for one row, so the same duplicate-athlete
        // matching applies to a boxer added at the door.
        const result = await combineApi.importRoster(eventId, [toRosterRow(values)], {
          dryRun: false,
          onNameMatch: 'link',
        });
        const row = result.results[0];
        if (!row || row.action === 'error') {
          setError(row?.reason ?? 'Could not add this boxer');
          return;
        }
        const label =
          row.action === 'linked'
            ? `${values.first_name} added — linked to existing athlete ${row.matched_name}`
            : `${values.first_name} added as bib ${row.bib}`;
        onSaved(label);

        if (addAnother) {
          // Keep club, category and age group — a queue at the door is usually
          // one club at a time.
          setValues({
            ...EMPTY_PARTICIPANT,
            club: values.club,
            weight_category: '',
            age_group: values.age_group,
            gender: values.gender,
          });
          setErrors({});
        } else {
          onClose();
        }
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save this boxer');
    } finally {
      setSaving(false);
    }
  }

  const fieldError = (key: keyof ParticipantFormValues) =>
    errors[key] ? <p className="mt-1 text-xs text-red-300">{errors[key]}</p> : null;

  return (
    <ResponsiveModal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="lg"
      title={isEdit ? `Edit ${participant?.name}` : 'Add a boxer'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">First name *</label>
            <input
              value={values.first_name}
              onChange={(e) => set('first_name', e.target.value)}
              className="input mt-1 w-full"
              autoFocus
              autoComplete="off"
            />
            {fieldError('first_name')}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">Surname</label>
            <input
              value={values.surname}
              onChange={(e) => set('surname', e.target.value)}
              className="input mt-1 w-full"
              autoComplete="off"
            />
          </div>
        </div>

        <div>
          <label className="text-xs uppercase tracking-widest text-white/40">Gender *</label>
          <div className="mt-1 flex gap-2">
            {(['male', 'female'] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => set('gender', option)}
                className={`min-h-[44px] flex-1 rounded-lg text-sm font-semibold capitalize transition-all active:scale-[0.97] ${
                  values.gender === option
                    ? 'bg-accent text-[#090A3D]'
                    : 'bg-secondary-muted/20 text-white/60 hover:bg-secondary-muted/40'
                }`}
              >
                {option}
              </button>
            ))}
          </div>
          {fieldError('gender')}
          {!isEdit && (
            <p className="mt-1 text-xs text-white/30">
              Required — it is never guessed, because benchmarks are gender-matched.
            </p>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">Bib</label>
            <input
              value={values.bib}
              onChange={(e) => set('bib', e.target.value)}
              inputMode="numeric"
              placeholder={isEdit ? '' : `auto — next is ${nextBib}`}
              className="input mt-1 w-full"
            />
            {fieldError('bib')}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">
              Body mass (kg)
            </label>
            <input
              value={values.body_mass_kg}
              onChange={(e) => set('body_mass_kg', e.target.value)}
              inputMode="decimal"
              placeholder="weigh-in"
              className="input mt-1 w-full"
            />
            {fieldError('body_mass_kg')}
            <p className="mt-1 text-xs text-white/30">
              Needed for W/kg on the bike. Also updates their profile.
            </p>
          </div>
        </div>

        <div>
          <label className="text-xs uppercase tracking-widest text-white/40">Club</label>
          <input
            value={values.club}
            onChange={(e) => set('club', e.target.value)}
            list="combine-club-options"
            className="input mt-1 w-full"
            autoComplete="off"
          />
          <datalist id="combine-club-options">
            {clubOptions.map((club) => (
              <option key={club} value={club} />
            ))}
          </datalist>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">
              Weight category
            </label>
            <select
              value={values.weight_category}
              onChange={(e) => set('weight_category', e.target.value)}
              className="input mt-1 w-full"
            >
              <option value="">Not set</option>
              {weightOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
            {fieldError('weight_category')}
          </div>
          <div>
            <label className="text-xs uppercase tracking-widest text-white/40">Age group</label>
            <input
              value={values.age_group}
              onChange={(e) => set('age_group', e.target.value)}
              list="combine-age-options"
              className="input mt-1 w-full"
              autoComplete="off"
            />
            <datalist id="combine-age-options">
              {ageOptions.map((group) => (
                <option key={group} value={group} />
              ))}
            </datalist>
          </div>
        </div>

        {isEdit && (
          <label className="flex min-h-[44px] items-center gap-2 text-sm text-white/60">
            <input
              type="checkbox"
              checked={values.withdrawn}
              onChange={(e) => set('withdrawn', e.target.checked)}
            />
            Withdrawn — keep their results but take them off the boards
          </label>
        )}

        {error && (
          <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</p>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          {!isEdit ? (
            <label className="flex items-center gap-2 text-sm text-white/50">
              <input
                type="checkbox"
                checked={addAnother}
                onChange={(e) => setAddAnother(e.target.checked)}
              />
              Keep adding
            </label>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              {isEdit ? 'Cancel' : 'Done'}
            </button>
            <button type="submit" disabled={saving} className="btn-primary disabled:opacity-40">
              {saving ? 'Saving…' : isEdit ? 'Save changes' : 'Add boxer'}
            </button>
          </div>
        </div>
      </form>
    </ResponsiveModal>
  );
}
