'use client';

import { useState } from 'react';
import { lactateApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { LactateTest, LactateStageCreate } from '@/lib/types';

interface LactateTestFormProps {
  athleteId: string;
  existingTest?: LactateTest | null;
  onClose: () => void;
  onSaved: () => void;
}

interface StageRow {
  intensity: string;
  lactate: string;
  hr: string;
  rpe: string;
}

function emptyStage(): StageRow {
  return { intensity: '', lactate: '', hr: '', rpe: '' };
}

export function LactateTestForm({
  athleteId,
  existingTest,
  onClose,
  onSaved,
}: LactateTestFormProps) {
  const isEdit = !!existingTest;

  const [testType, setTestType] = useState<'running' | 'cycling'>(
    existingTest?.test_type ?? 'running'
  );
  const [testDate, setTestDate] = useState(
    existingTest ? existingTest.test_date.slice(0, 10) : ''
  );
  const [stages, setStages] = useState<StageRow[]>(() => {
    if (existingTest?.stages?.length) {
      return existingTest.stages.map((s) => ({
        intensity: String(s.intensity_value),
        lactate: String(s.blood_lactate_mmol),
        hr: s.heart_rate_bpm != null ? String(s.heart_rate_bpm) : '',
        rpe: s.rpe != null ? String(s.rpe) : '',
      }));
    }
    return [emptyStage(), emptyStage(), emptyStage()];
  });
  const [notes, setNotes] = useState(existingTest?.notes ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const intensityLabel = testType === 'running' ? 'Speed (km/h)' : 'Power (W)';
  const unitLabel = testType === 'running' ? 'km/h' : 'W';

  function updateStage(index: number, field: keyof StageRow, value: string) {
    setStages((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  function removeStage(index: number) {
    if (stages.length <= 1) return;
    setStages((prev) => prev.filter((_, i) => i !== index));
  }

  function addStage() {
    setStages((prev) => [...prev, emptyStage()]);
  }

  function validate(): string | null {
    if (!isEdit && !testDate) return 'Test date is required';

    const filled = stages.filter((s) => s.intensity || s.lactate);
    if (filled.length < 1) return 'At least 1 stage with intensity and lactate is required';

    for (let i = 0; i < stages.length; i++) {
      const s = stages[i];
      if (!s.intensity && !s.lactate && !s.hr && !s.rpe) continue;
      if (!s.intensity) return `Stage ${i + 1}: Intensity is required`;
      if (!s.lactate) return `Stage ${i + 1}: Lactate is required`;
      const intensity = Number(s.intensity);
      if (isNaN(intensity) || intensity <= 0 || intensity > 2000) {
        return `Stage ${i + 1}: Intensity must be 0–2000`;
      }
      const lactate = Number(s.lactate);
      if (isNaN(lactate) || lactate < 0 || lactate > 50) {
        return `Stage ${i + 1}: Lactate must be 0–50 mmol/L`;
      }
      if (s.hr) {
        const hr = Number(s.hr);
        if (isNaN(hr) || hr < 20 || hr > 250) {
          return `Stage ${i + 1}: HR must be 20–250 bpm`;
        }
      }
      if (s.rpe) {
        const rpe = Number(s.rpe);
        if (isNaN(rpe) || rpe < 1 || rpe > 10) {
          return `Stage ${i + 1}: RPE must be 1–10`;
        }
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
      const stagesPayload: LactateStageCreate[] = stages
        .filter((s) => s.intensity && s.lactate)
        .map((s) => ({
          intensity_value: Number(s.intensity),
          blood_lactate_mmol: Number(s.lactate),
          ...(s.hr ? { heart_rate_bpm: Number(s.hr) } : {}),
          ...(s.rpe ? { rpe: Number(s.rpe) } : {}),
        }));

      if (isEdit && existingTest) {
        await lactateApi.updateTest(existingTest.id, {
          test_type: testType,
          ...(testDate ? { test_date: testDate } : {}),
          notes: notes || undefined,
          stages: stagesPayload,
        });
      } else {
        await lactateApi.createTest(athleteId, {
          test_type: testType,
          test_date: testDate,
          notes: notes || undefined,
          stages: stagesPayload,
        });
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save test');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="lg" title={isEdit ? 'Edit Lactate Test' : 'New Lactate Test'}>
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Test Type Toggle */}
          <div>
            <label className="block text-sm text-white/60 mb-1">Test Type</label>
            <div className="flex bg-secondary-muted/30 rounded-lg p-0.5 w-fit">
              <button
                type="button"
                onClick={() => setTestType('running')}
                className={`px-4 py-1.5 min-h-[44px] rounded-md text-sm font-medium transition-colors ${
                  testType === 'running'
                    ? 'bg-green-500/20 text-green-400 active:bg-green-500/30'
                    : 'text-white/60 hover:text-white active:text-white/80'
                }`}
              >
                Running
              </button>
              <button
                type="button"
                onClick={() => setTestType('cycling')}
                className={`px-4 py-1.5 min-h-[44px] rounded-md text-sm font-medium transition-colors ${
                  testType === 'cycling'
                    ? 'bg-blue-500/20 text-blue-400 active:bg-blue-500/30'
                    : 'text-white/60 hover:text-white active:text-white/80'
                }`}
              >
                Cycling
              </button>
            </div>
          </div>

          {/* Test Date */}
          <div>
            <label className="block text-sm text-white/60 mb-1">Date</label>
            <input
              type="date"
              value={testDate}
              onChange={(e) => setTestDate(e.target.value)}
              className="input w-full"
              required={!isEdit}
            />
          </div>

          {/* Stages */}
          <div>
            <label className="block text-sm text-white/60 mb-2">Stages</label>

            {/* Desktop Header */}
            <div className="hidden sm:grid grid-cols-[auto_1fr_1fr_auto_auto_auto] gap-2 text-xs text-white/40 mb-1 px-1">
              <span>#</span>
              <span>{intensityLabel}</span>
              <span>Lactate (mmol/L)</span>
              <span>HR</span>
              <span>RPE</span>
              <span></span>
            </div>

            <div className="space-y-2">
              {stages.map((s, i) => (
                <div key={i}>
                  {/* Desktop row */}
                  <div className="hidden sm:grid grid-cols-[auto_1fr_1fr_auto_auto_auto] gap-2 items-center">
                    <span className="text-xs text-white/40 w-5 text-center">{i + 1}</span>
                    <input
                      type="number"
                      step="any"
                      min="0"
                      max="2000"
                      value={s.intensity}
                      onChange={(e) => updateStage(i, 'intensity', e.target.value)}
                      className="input w-full"
                      placeholder={unitLabel}
                    />
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      max="50"
                      value={s.lactate}
                      onChange={(e) => updateStage(i, 'lactate', e.target.value)}
                      className="input w-full"
                      placeholder="mmol/L"
                    />
                    <input
                      type="number"
                      min="20"
                      max="250"
                      value={s.hr}
                      onChange={(e) => updateStage(i, 'hr', e.target.value)}
                      className="input w-16"
                      placeholder="bpm"
                    />
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={s.rpe}
                      onChange={(e) => updateStage(i, 'rpe', e.target.value)}
                      className="input w-14"
                      placeholder="1-10"
                    />
                    <button
                      type="button"
                      onClick={() => removeStage(i)}
                      disabled={stages.length <= 1}
                      className="text-white/30 hover:text-red-400 active:text-red-300 disabled:opacity-20 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center"
                      title="Remove stage"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
                        <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>

                  {/* Mobile row */}
                  <div className="sm:hidden space-y-1.5 border border-secondary-muted/50 rounded-lg p-2">
                    <div className="text-xs text-white/40">Stage {i + 1}</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs text-white/40">{intensityLabel}</label>
                        <input
                          type="number"
                          step="any"
                          min="0"
                          max="2000"
                          value={s.intensity}
                          onChange={(e) => updateStage(i, 'intensity', e.target.value)}
                          className="input w-full"
                          placeholder={unitLabel}
                        />
                      </div>
                      <div>
                        <label className="text-xs text-white/40">Lactate</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="50"
                          value={s.lactate}
                          onChange={(e) => updateStage(i, 'lactate', e.target.value)}
                          className="input w-full"
                          placeholder="mmol/L"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-xs text-white/40">HR (bpm)</label>
                        <input
                          type="number"
                          min="20"
                          max="250"
                          value={s.hr}
                          onChange={(e) => updateStage(i, 'hr', e.target.value)}
                          className="input w-full"
                          placeholder="bpm"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-white/40">RPE</label>
                        <input
                          type="number"
                          min="1"
                          max="10"
                          value={s.rpe}
                          onChange={(e) => updateStage(i, 'rpe', e.target.value)}
                          className="input w-full"
                          placeholder="1-10"
                        />
                      </div>
                    </div>
                    {stages.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeStage(i)}
                        className="text-xs text-red-400/60 hover:text-red-400 active:text-red-300 min-h-[44px] flex items-center"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={addStage}
              className="mt-2 text-sm text-accent hover:text-accent/80 active:text-accent/60 min-h-[44px] flex items-center transition-colors"
            >
              + Add Stage
            </button>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm text-white/60 mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full"
              rows={2}
              placeholder="Optional notes..."
              maxLength={1000}
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
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Create Test'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
