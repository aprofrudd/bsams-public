'use client';

import { useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { trainingBlocksApi } from '@/lib/api';
import { useAthleteSelection, getAthleteName } from '@/lib/hooks/useAthleteSelection';
import type { TrainingBlockDetail, WeightResolution } from '@/lib/types';

type Step = 'athletes' | 'date' | 'preview';

interface BlockApplyModalProps {
  block: TrainingBlockDetail;
  onClose: () => void;
  onApplied: () => void;
}

export function BlockApplyModal({ block, onClose, onApplied }: BlockApplyModalProps) {
  const [step, setStep] = useState<Step>('athletes');
  const {
    loading, selectedIds, searchQuery, setSearchQuery,
    filteredAthletes, toggleAthlete, toggleAll, error: athleteError,
  } = useAthleteSelection();
  const [startDate, setStartDate] = useState('');

  const [previewLoading, setPreviewLoading] = useState(false);
  const [resolutions, setResolutions] = useState<WeightResolution[]>([]);
  const [totalSessions, setTotalSessions] = useState(0);

  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function isMonday(dateStr: string): boolean {
    if (!dateStr) return false;
    const d = new Date(dateStr + 'T00:00:00');
    return d.getDay() === 1;
  }

  async function handlePreview() {
    setPreviewLoading(true);
    setError(null);
    try {
      const resp = await trainingBlocksApi.preview(block.id, Array.from(selectedIds));
      setResolutions(resp.resolutions);
      setTotalSessions(resp.total_sessions);
      setStep('preview');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load preview');
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleApply() {
    setApplying(true);
    setError(null);
    try {
      const resp = await trainingBlocksApi.apply(block.id, {
        athlete_ids: Array.from(selectedIds),
        start_date: startDate,
      });
      const unresolvedCount = resp.unresolved_exercises.length;
      setSuccess(
        `Created ${resp.created_count} sessions (${resp.sessions_per_athlete} per athlete).` +
        (unresolvedCount > 0 ? ` ${unresolvedCount} exercise(s) need manual weight entry.` : '')
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply block');
    } finally {
      setApplying(false);
    }
  }

  if (success) {
    return (
      <ResponsiveModal isOpen onClose={onApplied} maxWidth="md" title="Block Applied">
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
    <ResponsiveModal isOpen onClose={onClose} maxWidth="lg" title={`Apply: ${block.block_name}`}>
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

        {/* Step 2: Date */}
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
              <p>{block.num_weeks} weeks &times; {block.sessions.length} session types &times; {selectedIds.size} athletes</p>
              <p>= {block.sessions.length * selectedIds.size} sessions total (across {block.num_weeks} weeks)</p>
            </div>

            <div className="flex justify-between">
              <button
                onClick={() => setStep('athletes')}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handlePreview}
                disabled={!startDate || !isMonday(startDate) || previewLoading}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
              >
                {previewLoading ? 'Loading...' : 'Preview'}
              </button>
            </div>
          </>
        )}

        {/* Step 3: Preview & Apply */}
        {step === 'preview' && (
          <>
            <div className="text-sm text-white/60 mb-2">
              <p>{totalSessions} sessions will be created for {selectedIds.size} athlete{selectedIds.size !== 1 ? 's' : ''}.</p>
            </div>

            {resolutions.length > 0 && (
              <div>
                <h4 className="text-xs text-white/50 mb-2">Weight Resolution</h4>
                <div className="max-h-48 overflow-y-auto border border-secondary-muted rounded-lg">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-secondary-muted text-white/50">
                        <th className="text-left p-2">Athlete</th>
                        <th className="text-left p-2">Exercise</th>
                        <th className="text-right p-2">1RM</th>
                        <th className="text-right p-2">%</th>
                        <th className="text-right p-2">Load</th>
                        <th className="text-left p-2">Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resolutions.map((r, i) => (
                        <tr
                          key={i}
                          className={`border-b border-secondary-muted/50 ${r.source === 'missing' ? 'bg-yellow-500/5' : ''}`}
                        >
                          <td className="p-2">{r.athlete_name}</td>
                          <td className="p-2">{r.exercise_name}</td>
                          <td className="p-2 text-right">
                            {r.max_1rm_kg != null ? `${r.max_1rm_kg} kg` : '—'}
                          </td>
                          <td className="p-2 text-right">{r.percent_1rm}%</td>
                          <td className="p-2 text-right">
                            {r.resolved_weight_kg != null ? (
                              <span className="text-green-400">{r.resolved_weight_kg} kg</span>
                            ) : (
                              <span className="text-yellow-400">Missing</span>
                            )}
                          </td>
                          <td className="p-2">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                              r.source === 'vbt' ? 'bg-cyan-500/10 text-cyan-400' :
                              r.source === 'manual' ? 'bg-blue-500/10 text-blue-400' :
                              'bg-yellow-500/10 text-yellow-400'
                            }`}>
                              {r.source}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {resolutions.some(r => r.source === 'missing') && (
                  <p className="text-xs text-yellow-400 mt-2">
                    Exercises with missing 1RM data will be created without weight. Set weights manually afterwards.
                  </p>
                )}
              </div>
            )}

            <div className="flex justify-between">
              <button
                onClick={() => setStep('date')}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
              >
                Back
              </button>
              <button
                onClick={handleApply}
                disabled={applying}
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
