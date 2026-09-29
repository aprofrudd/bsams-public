'use client';

import { useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { programmeFormsApi } from '@/lib/api';
import { useAthleteSelection, getAthleteName } from '@/lib/hooks/useAthleteSelection';
import type { ProgrammeForm } from '@/lib/types';

type Step = 'athletes' | 'date';

interface ProgrammeApplyModalProps {
  form: ProgrammeForm;
  onClose: () => void;
  onApplied: () => void;
}

export function ProgrammeApplyModal({ form, onClose, onApplied }: ProgrammeApplyModalProps) {
  const [step, setStep] = useState<Step>('athletes');
  const {
    loading, selectedIds, searchQuery, setSearchQuery,
    filteredAthletes, toggleAthlete, toggleAll, error: athleteError,
  } = useAthleteSelection();
  const [startDate, setStartDate] = useState('');

  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function isMonday(dateStr: string): boolean {
    if (!dateStr) return false;
    const d = new Date(dateStr + 'T00:00:00');
    return d.getDay() === 1;
  }

  async function handleApply() {
    setApplying(true);
    setError(null);
    try {
      const resp = await programmeFormsApi.apply(form.id, {
        athlete_ids: Array.from(selectedIds),
        start_date: startDate,
      });
      setSuccess(
        `Created ${resp.created_count} sessions (${resp.sessions_per_athlete} per athlete).`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply form');
    } finally {
      setApplying(false);
    }
  }

  if (success) {
    return (
      <ResponsiveModal isOpen onClose={onApplied} maxWidth="md" title="Form Applied">
        <div className="text-center py-6">
          <div className="text-4xl mb-4">&#10003;</div>
          <p className="text-sm text-green-400 mb-4">{success}</p>
          <button
            onClick={onApplied}
            className="px-6 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
          >
            Done
          </button>
        </div>
      </ResponsiveModal>
    );
  }

  return (
    <ResponsiveModal isOpen onClose={onClose} maxWidth="lg" title={`Apply: ${form.form_name}`}>
      <div className="space-y-4">
        {(error || athleteError) && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
            {error || athleteError}
            {error && <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">&times;</button>}
          </div>
        )}

        {/* Step 1: Athletes */}
        {step === 'athletes' && (
          <>
            <div className="flex items-center justify-between">
              <p className="text-sm text-white/60">Select athletes ({selectedIds.size} selected)</p>
              <button
                onClick={toggleAll}
                className="text-xs text-accent hover:text-accent/80"
              >
                {selectedIds.size === filteredAthletes.length ? 'Deselect All' : 'Select All'}
              </button>
            </div>

            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-field w-full"
              placeholder="Search athletes..."
            />

            <div className="max-h-60 overflow-y-auto space-y-1">
              {loading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                </div>
              ) : filteredAthletes.length === 0 ? (
                <p className="text-white/40 text-sm text-center py-4">No athletes found</p>
              ) : (
                filteredAthletes.map(a => (
                  <label
                    key={a.id}
                    className="flex items-center gap-3 p-2 rounded hover:bg-white/5 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedIds.has(a.id)}
                      onChange={() => toggleAthlete(a.id)}
                      className="rounded"
                    />
                    <span className="text-sm">{getAthleteName(a)}</span>
                  </label>
                ))
              )}
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setStep('date')}
                disabled={selectedIds.size === 0}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </>
        )}

        {/* Step 2: Date + Confirm */}
        {step === 'date' && (
          <>
            <p className="text-sm text-white/60">Pick the Monday that starts Week 1</p>

            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="input-field w-full"
            />

            {startDate && !isMonday(startDate) && (
              <p className="text-xs text-yellow-400">Start date must be a Monday.</p>
            )}

            <div className="text-xs text-white/40 space-y-1">
              <p>{form.num_weeks} weeks &times; {form.sessions_per_week} sessions &times; {selectedIds.size} athletes</p>
              <p>= {form.num_weeks * form.sessions_per_week * selectedIds.size} sessions total</p>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep('athletes')}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleApply}
                disabled={!startDate || !isMonday(startDate) || applying}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
              >
                {applying ? 'Applying...' : `Apply to ${selectedIds.size} Athletes`}
              </button>
            </div>
          </>
        )}
      </div>
    </ResponsiveModal>
  );
}
