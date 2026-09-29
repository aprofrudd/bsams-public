'use client';

import { useState } from 'react';
import { trainingApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { RpeSelector } from '@/components/ui/RpeSelector';
import { NumberStepper } from '@/components/ui/NumberStepper';
import { TrainingTypeSelector } from './TrainingTypeSelector';
import type { TrainingSession } from '@/lib/types';

export type SessionFormMode = 'log' | 'edit' | 'complete' | 'assign';

interface SessionLogFormProps {
  athleteId: string;
  existingSession?: TrainingSession | null;
  mode?: SessionFormMode;
  isAthlete?: boolean;
  onClose: () => void;
  onSaved: () => void;
}

function toInputDate(isoDate: string): string {
  return isoDate.slice(0, 10);
}

const MODE_TITLES: Record<SessionFormMode, string> = {
  log: 'Add Session',
  edit: 'Edit Session',
  complete: 'Complete Session',
  assign: 'Assign Session',
};

export function SessionLogForm({
  athleteId,
  existingSession,
  mode = existingSession ? 'edit' : 'log',
  isAthlete,
  onClose,
  onSaved,
}: SessionLogFormProps) {
  const isComplete = mode === 'complete';
  const isAssign = mode === 'assign';
  const isEdit = mode === 'edit';

  const [sessionDate, setSessionDate] = useState(
    existingSession ? toInputDate(existingSession.session_date) : ''
  );
  const [trainingType, setTrainingType] = useState(
    existingSession?.training_type || 'Strength'
  );
  const [durationMinutes, setDurationMinutes] = useState(
    existingSession?.duration_minutes ? String(existingSession.duration_minutes) : ''
  );
  const [rpe, setRpe] = useState(
    existingSession?.rpe ? String(existingSession.rpe) : ''
  );
  const [notes, setNotes] = useState(existingSession?.notes || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const showRpeDuration = !isAssign;
  const computedSrpe = showRpeDuration && rpe && durationMinutes
    ? Number(rpe) * Number(durationMinutes)
    : null;

  function validate(): string | null {
    if (!isEdit && !isComplete && !sessionDate) return 'Session date is required';
    if (showRpeDuration) {
      // In complete mode, RPE/duration are mandatory. In log mode, optional (but validate if partially filled)
      const requireRpe = isComplete || isEdit;
      const hasDuration = durationMinutes && Number(durationMinutes) > 0;
      const hasRpe = rpe && Number(rpe) > 0;
      if (requireRpe || hasDuration || hasRpe) {
        if (hasDuration && (Number(durationMinutes) < 1 || Number(durationMinutes) > 600))
          return 'Duration must be 1-600 minutes';
        if (hasRpe && (Number(rpe) < 1 || Number(rpe) > 10))
          return 'RPE must be 1-10';
        // If one is filled, require both (for sRPE calculation)
        if (hasDuration && !hasRpe) return 'RPE is required when duration is provided';
        if (hasRpe && !hasDuration) return 'Duration is required when RPE is provided';
      }
    }
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      if (isComplete && existingSession) {
        // Complete a session — PATCH with rpe, duration, notes, status
        await trainingApi.updateSession(existingSession.id, {
          duration_minutes: Number(durationMinutes),
          rpe: Number(rpe),
          notes: notes || undefined,
          status: 'completed',
        });
      } else if (isEdit && existingSession) {
        await trainingApi.updateSession(existingSession.id, {
          ...(sessionDate ? { session_date: sessionDate } : {}),
          training_type: trainingType,
          duration_minutes: Number(durationMinutes),
          rpe: Number(rpe),
          notes: notes || undefined,
        });
      } else if (isAssign) {
        await trainingApi.createSession({
          athlete_id: athleteId,
          session_date: sessionDate,
          training_type: trainingType,
          notes: notes || undefined,
          status: 'assigned',
        });
      } else {
        // Regular log — RPE/duration optional
        await trainingApi.createSession({
          athlete_id: athleteId,
          session_date: sessionDate,
          training_type: trainingType,
          ...(durationMinutes ? { duration_minutes: Number(durationMinutes) } : {}),
          ...(rpe ? { rpe: Number(rpe) } : {}),
          notes: notes || undefined,
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save session');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title={MODE_TITLES[mode]}>
        <form onSubmit={handleSubmit} className="space-y-3">
          {isComplete ? (
            <>
              <div className="text-sm text-white/60">
                <span className="text-white font-medium">{existingSession?.training_type}</span>
                {' on '}
                <span className="text-white font-medium">
                  {existingSession?.session_date ? new Date(existingSession.session_date + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : ''}
                </span>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-sm text-white/60 mb-1">Session Date</label>
                <input
                  type="date"
                  value={sessionDate}
                  onChange={(e) => setSessionDate(e.target.value)}
                  className="input w-full"
                  required={!isEdit}
                />
              </div>

              <div>
                <label className="block text-sm text-white/60 mb-1">Training Type</label>
                <TrainingTypeSelector value={trainingType} onChange={setTrainingType} />
              </div>
            </>
          )}

          {showRpeDuration && (
            <>
              <div>
                <label className="block text-sm text-white/60 mb-1">Duration (minutes)</label>
                <NumberStepper
                  value={Number(durationMinutes) || 0}
                  onChange={(v) => setDurationMinutes(String(v))}
                  min={1}
                  max={600}
                  variant="plusminus"
                />
              </div>

              <div>
                <label className="block text-sm text-white/60 mb-1">RPE (1-10)</label>
                <RpeSelector
                  value={Number(rpe) || 0}
                  onChange={(v) => setRpe(String(v))}
                />
              </div>

              {computedSrpe !== null && (
                <div className="text-sm text-white/60">
                  sRPE: <span className="text-accent font-medium">{computedSrpe}</span>
                  <span className="text-white/40 ml-1">(RPE x Duration)</span>
                </div>
              )}
            </>
          )}

          <div>
            <label className="block text-sm text-white/60 mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full resize-none"
              rows={3}
              maxLength={1000}
              placeholder="Session notes..."
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
              {saving ? 'Saving...' : MODE_TITLES[mode]}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
