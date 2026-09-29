'use client';

import { useState } from 'react';
import { wellnessApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { NumberStepper } from '@/components/ui/NumberStepper';
import type { WellnessEntry } from '@/lib/types';

interface WellnessFormProps {
  athleteId: string;
  existingEntry?: WellnessEntry | null;
  existingDates?: string[];
  onClose: () => void;
  onSaved: () => void;
}

const HOOPER_FIELDS: { key: string; label: string; lowLabel: string; highLabel: string }[] = [
  { key: 'sleep', label: 'Sleep Quality', lowLabel: 'Very Good', highLabel: 'Very Bad' },
  { key: 'fatigue', label: 'Fatigue', lowLabel: 'Very Low', highLabel: 'Very High' },
  { key: 'stress', label: 'Stress', lowLabel: 'Very Low', highLabel: 'Very High' },
  { key: 'doms', label: 'DOMS', lowLabel: 'Very Low', highLabel: 'Very High' },
];

function toInputDate(isoDate: string): string {
  return isoDate.slice(0, 10);
}

export function WellnessForm({
  athleteId,
  existingEntry,
  existingDates,
  onClose,
  onSaved,
}: WellnessFormProps) {
  const isEdit = !!existingEntry;

  const [entryDate, setEntryDate] = useState(
    existingEntry ? toInputDate(existingEntry.entry_date) : new Date().toISOString().slice(0, 10)
  );
  const [scores, setScores] = useState<Record<string, number>>(() => {
    if (existingEntry) {
      return {
        sleep: existingEntry.sleep,
        fatigue: existingEntry.fatigue,
        stress: existingEntry.stress,
        doms: existingEntry.doms,
      };
    }
    return {
      sleep: 1,
      fatigue: 1,
      stress: 1,
      doms: 1,
    };
  });
  const [notes, setNotes] = useState(existingEntry?.notes || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hooperIndex = scores.sleep + scores.fatigue + scores.stress + scores.doms;

  function setScore(key: string, value: number) {
    setScores((prev) => ({ ...prev, [key]: value }));
  }

  function getHooperColor(index: number): string {
    if (index <= 10) return 'text-green-400';
    if (index <= 16) return 'text-yellow-400';
    return 'text-red-400';
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!isEdit && existingDates?.includes(entryDate)) {
      const confirmed = window.confirm(
        'A wellness entry already exists for this date. Saving will update the existing entry. Continue?'
      );
      if (!confirmed) return;
    }

    setSaving(true);
    setError(null);

    try {
      if (isEdit && existingEntry) {
        await wellnessApi.updateEntry(existingEntry.id, {
          ...(entryDate ? { entry_date: entryDate } : {}),
          sleep: scores.sleep,
          fatigue: scores.fatigue,
          stress: scores.stress,
          doms: scores.doms,
          notes: notes || undefined,
        });
      } else {
        await wellnessApi.createEntry({
          athlete_id: athleteId,
          entry_date: entryDate,
          sleep: scores.sleep,
          fatigue: scores.fatigue,
          stress: scores.stress,
          doms: scores.doms,
          notes: notes || undefined,
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save wellness entry');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title={isEdit ? 'Edit Hooper Index' : 'Log Hooper Index'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-white/60 mb-1">Date</label>
            <input
              type="date"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              className="input w-full"
              required
            />
          </div>

          {HOOPER_FIELDS.map((field) => (
            <div key={field.key}>
              <div className="flex justify-between items-center mb-1">
                <label className="text-sm text-white/60">{field.label}</label>
                <span className="text-accent text-sm font-medium">{scores[field.key]}/7</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-white/40 w-16">{field.lowLabel}</span>
                <NumberStepper
                  value={scores[field.key]}
                  onChange={(v) => setScore(field.key, v)}
                  min={1}
                  max={7}
                  variant="segments"
                />
                <span className="text-xs text-white/40 w-16 text-right">{field.highLabel}</span>
              </div>
            </div>
          ))}

          {/* Hooper Index display */}
          <div className="bg-secondary-muted/30 rounded-lg p-3 text-center">
            <div className="text-xs text-white/60 mb-1">Hooper Index</div>
            <div className={`text-2xl font-bold ${getHooperColor(hooperIndex)}`}>
              {hooperIndex}
            </div>
            <div className="text-xs text-white/40 mt-1">Range: 4 (best) - 28 (worst)</div>
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full resize-none"
              rows={2}
              maxLength={1000}
              placeholder="How are you feeling?"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="btn-primary flex-1 disabled:opacity-50"
            >
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Log Wellness'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
