'use client';

import { useState } from 'react';
import { combineApi, ApiError } from '@/lib/api';
import { normaliseWeightCategory } from '@/lib/combineParticipantForm';
import type { CombineRosterResult, CombineRosterRow } from '@/lib/types';

/**
 * Paste-a-roster import.
 *
 * The preview is not optional: importing forty boxers is exactly the moment to
 * create forty duplicate athlete records by accident, so the real import stays
 * disabled until the coach has seen which rows would be created and which would be
 * linked to an athlete already on the account.
 */

const TEMPLATE = 'First name, Surname, M/F, Club, Weight category, Age group, Body mass kg';

export function parseRosterText(text: string): { rows: CombineRosterRow[]; errors: string[] } {
  const rows: CombineRosterRow[] = [];
  const errors: string[] = [];

  text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line, index) => {
      // Skip a pasted header row
      if (index === 0 && /first\s*name/i.test(line)) return;

      const cells = line.split(/\t|,/).map((cell) => cell.trim());
      const [first, surname, genderRaw, club, weight, age, mass] = cells;

      if (!first) {
        errors.push(`Line ${index + 1}: no first name`);
        return;
      }
      const gender = (genderRaw || '').toLowerCase();
      const resolved =
        gender.startsWith('m') ? 'male' : gender.startsWith('f') ? 'female' : null;
      if (!resolved) {
        errors.push(`Line ${index + 1}: gender must be M or F`);
        return;
      }

      // Strict, like the backend: "57" and "91kg+" are fixed up, but an invented
      // division is rejected here rather than importing a category the board's
      // filter chips would match for one boxer and nobody else.
      const category = weight ? normaliseWeightCategory(weight) : null;
      if (weight && category === null) {
        errors.push(`Line ${index + 1}: unknown weight category '${weight}'`);
        return;
      }

      const bodyMass = mass ? Number(mass) : undefined;
      rows.push({
        first_name: first,
        surname: surname || undefined,
        gender: resolved,
        club: club || undefined,
        weight_category: category ?? undefined,
        age_group: age || undefined,
        body_mass_kg: Number.isFinite(bodyMass) ? bodyMass : undefined,
      });
    });

  return { rows, errors };
}

export function RosterImport({
  eventId,
  onImported,
}: {
  eventId: string;
  onImported: () => void;
}) {
  const [text, setText] = useState('');
  const [preview, setPreview] = useState<CombineRosterResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { rows, errors } = parseRosterText(text);

  async function runPreview() {
    setBusy(true);
    setError(null);
    try {
      setPreview(await combineApi.importRoster(eventId, rows, { dryRun: true }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not preview the import');
    } finally {
      setBusy(false);
    }
  }

  async function runImport() {
    setBusy(true);
    setError(null);
    try {
      const result = await combineApi.importRoster(eventId, rows, { dryRun: false });
      setPreview(result);
      setText('');
      onImported();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not import the roster');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="text-xs uppercase tracking-widest text-white/40">
          Paste the roster — one boxer per line
        </label>
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPreview(null);
          }}
          rows={8}
          spellCheck={false}
          placeholder={`${TEMPLATE}\nJack, Reid, M, Repton, 57kg, Junior, 57.2`}
          className="input mt-1 w-full font-mono text-sm"
        />
        <p className="mt-1 text-xs text-white/30">
          Comma or tab separated. Gender is required — it is never guessed.
        </p>
      </div>

      {errors.length > 0 && (
        <ul className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-200">
          {errors.slice(0, 5).map((message) => (
            <li key={message}>{message}</li>
          ))}
          {errors.length > 5 && <li>…and {errors.length - 5} more</li>}
        </ul>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={runPreview}
          disabled={busy || rows.length === 0}
          className="btn-secondary disabled:opacity-40"
        >
          Preview {rows.length > 0 ? `${rows.length} boxers` : ''}
        </button>
        <button
          type="button"
          onClick={runImport}
          disabled={busy || !preview || !preview.dry_run}
          title={preview ? undefined : 'Preview the import first'}
          className="btn-primary disabled:opacity-40"
        >
          Import
        </button>
      </div>

      {preview && (
        <div className="rounded-lg border border-secondary-muted/50 p-3">
          <p className="text-sm text-white/70">
            {preview.dry_run ? 'Preview: ' : 'Imported: '}
            <span className="text-accent">{preview.created_athletes} new</span>,{' '}
            <span className="text-accent">{preview.linked_athletes} linked</span> to existing
            athletes, {preview.participants_added} added to the roster
          </p>
          <ul className="mt-2 max-h-48 space-y-0.5 overflow-y-auto text-xs">
            {preview.results.map((row) => (
              <li
                key={row.index}
                className={
                  row.action === 'error'
                    ? 'text-red-300'
                    : row.action === 'linked'
                      ? 'text-accent/80'
                      : row.action === 'skipped'
                        ? 'text-white/30'
                        : 'text-white/60'
                }
              >
                #{row.bib ?? '—'} {row.action}
                {row.matched_name ? ` → ${row.matched_name}` : ''}
                {row.reason ? ` (${row.reason})` : ''}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && <p className="text-sm text-red-300">{error}</p>}
    </div>
  );
}
