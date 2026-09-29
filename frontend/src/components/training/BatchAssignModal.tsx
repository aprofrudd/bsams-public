'use client';

import { useState, useEffect, useMemo } from 'react';
import { sessionTemplatesApi, trainingApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { useAthleteSelection, getAthleteName } from '@/lib/hooks/useAthleteSelection';
import type { SessionTemplate } from '@/lib/types';

type Step = 'template' | 'athletes' | 'review';

interface BatchAssignModalProps {
  onClose: () => void;
  onAssigned: (count: number) => void;
}

export function BatchAssignModal({ onClose, onAssigned }: BatchAssignModalProps) {
  const [step, setStep] = useState<Step>('template');
  const [templates, setTemplates] = useState<SessionTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const {
    athletes, loading: loadingAthletes, selectedIds: selectedAthleteIds,
    searchQuery, setSearchQuery, filteredAthletes, toggleAthlete,
    toggleAll: toggleSelectAll, error: athleteError,
  } = useAthleteSelection();

  const loadingData = loadingTemplates || loadingAthletes;

  const [selectedTemplate, setSelectedTemplate] = useState<SessionTemplate | null>(null);
  const [sessionDate, setSessionDate] = useState('');
  const [notes, setNotes] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successCount, setSuccessCount] = useState<number | null>(null);

  // Load templates on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        const templateData = await sessionTemplatesApi.list();
        setTemplates(templateData);
      } catch {
        setLoadError('Failed to load data');
      } finally {
        setLoadingTemplates(false);
      }
    };
    loadData();
  }, []);

  // Check if all visible athletes are selected
  const allVisibleSelected =
    filteredAthletes.length > 0 &&
    filteredAthletes.every((a) => selectedAthleteIds.has(a.id));

  async function handleSubmit() {
    if (!selectedTemplate || selectedAthleteIds.size === 0 || !sessionDate) return;

    setSubmitting(true);
    setError(null);

    try {
      const result = await trainingApi.batchAssign({
        template_id: selectedTemplate.id,
        athlete_ids: Array.from(selectedAthleteIds),
        session_date: sessionDate,
        notes: notes || undefined,
      });
      setSuccessCount(result.created_count);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign sessions');
    } finally {
      setSubmitting(false);
    }
  }

  function handleDone() {
    onAssigned(successCount ?? 0);
  }

  // Step indicator labels
  const steps: { key: Step; label: string; number: number }[] = [
    { key: 'template', label: 'Template', number: 1 },
    { key: 'athletes', label: 'Athletes', number: 2 },
    { key: 'review', label: 'Review', number: 3 },
  ];

  const stepIndex = steps.findIndex((s) => s.key === step);

  // Selected athlete names for review step
  const selectedAthleteNames = useMemo(() => {
    return athletes
      .filter((a) => selectedAthleteIds.has(a.id))
      .map((a) => getAthleteName(a));
  }, [athletes, selectedAthleteIds]);

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="lg" title="Batch Assign Sessions">
      {/* Success State */}
      {successCount !== null ? (
        <div className="text-center py-8">
          <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-green-400">
              <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
            </svg>
          </div>
          <p className="text-white font-medium text-lg mb-1">
            Successfully assigned {successCount} session{successCount !== 1 ? 's' : ''}
          </p>
          <p className="text-white/40 text-sm mb-2">
            Sessions have been created for the selected athletes.
          </p>
          <p className="text-white/30 text-xs mb-6">
            Athletes will see assigned sessions when they next log in.
          </p>
          <button
            onClick={handleDone}
            className="px-6 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
          >
            Done
          </button>
        </div>
      ) : (
        <>
          {/* Step Indicators */}
          <div className="flex items-center justify-center gap-2 mb-6">
            {steps.map((s, i) => {
              const isActive = i === stepIndex;
              const isCompleted = i < stepIndex;
              return (
                <div key={s.key} className="flex items-center gap-2">
                  {i > 0 && (
                    <div
                      className={`w-8 h-px ${
                        isCompleted || isActive ? 'bg-accent' : 'bg-secondary-muted'
                      }`}
                    />
                  )}
                  <div className="flex items-center gap-1.5">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                        isActive
                          ? 'bg-accent text-[#090A3D]'
                          : isCompleted
                          ? 'bg-accent/30 text-accent'
                          : 'bg-secondary-muted/30 text-white/40'
                      }`}
                    >
                      {s.number}
                    </div>
                    <span
                      className={`text-xs ${
                        isActive ? 'text-white' : 'text-white/40'
                      }`}
                    >
                      {s.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Loading state */}
          {loadingData ? (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
              <p className="text-white/40 text-sm mt-2">Loading...</p>
            </div>
          ) : (loadError || athleteError) ? (
            <p className="text-red-400 text-sm py-4 text-center">{loadError || athleteError}</p>
          ) : (
            <>
              {/* Step 1: Select Template */}
              {step === 'template' && (
                <div>
                  {templates.length === 0 ? (
                    <p className="text-white/60 text-sm py-8 text-center">
                      No templates found. Create a template in the Library first.
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-[60vh] sm:max-h-[40vh] overflow-y-auto">
                      {templates.map((t) => {
                        const isSelected = selectedTemplate?.id === t.id;
                        return (
                          <button
                            key={t.id}
                            type="button"
                            onClick={() => setSelectedTemplate(t)}
                            className={`w-full text-left border rounded-lg p-3 min-h-[44px] transition-colors ${
                              isSelected
                                ? 'border-accent bg-accent/10'
                                : 'border-secondary-muted hover:border-accent/30'
                            }`}
                          >
                            <p className="font-medium text-sm">{t.template_name}</p>
                            <p className="text-xs text-white/40">
                              {t.training_type} &middot; {t.exercises.length} exercise
                              {t.exercises.length !== 1 ? 's' : ''}
                            </p>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  <div className="flex gap-3 pt-4">
                    <button
                      type="button"
                      onClick={onClose}
                      className="btn-secondary flex-1"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => setStep('athletes')}
                      disabled={!selectedTemplate}
                      className="btn-primary flex-1 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2: Select Athletes */}
              {step === 'athletes' && (
                <div>
                  {/* Selected template summary */}
                  {selectedTemplate && (
                    <div className="border border-secondary-muted/30 rounded-lg p-2.5 mb-3 bg-secondary-muted/5">
                      <p className="text-xs text-white/40">
                        Template: <span className="text-white font-medium">{selectedTemplate.template_name}</span>
                        {' '}&middot;{' '}
                        {selectedTemplate.training_type}
                        {' '}&middot;{' '}
                        {selectedTemplate.exercises.length} exercise{selectedTemplate.exercises.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  )}

                  {/* Search input */}
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search athletes..."
                    className="input w-full mb-3"
                  />

                  {athletes.length === 0 ? (
                    <p className="text-white/60 text-sm py-8 text-center">
                      No athletes found.
                    </p>
                  ) : (
                    <>
                      {/* Select All toggle + count */}
                      <div className="flex items-center justify-between mb-2">
                        <label className="flex items-center gap-2 min-h-[44px] cursor-pointer">
                          <input
                            type="checkbox"
                            checked={allVisibleSelected}
                            onChange={toggleSelectAll}
                            className="w-4 h-4 rounded border-secondary-muted bg-transparent text-accent focus:ring-accent accent-[#33CBF4]"
                          />
                          <span className="text-sm text-white/60">Select All</span>
                        </label>
                        {selectedAthleteIds.size > 0 && (
                          <span className="text-xs font-medium bg-accent/20 text-accent px-2 py-1 rounded-full">
                            {selectedAthleteIds.size} selected
                          </span>
                        )}
                      </div>

                      {/* Athlete list */}
                      <div className="space-y-1 max-h-[55vh] sm:max-h-[35vh] overflow-y-auto">
                        {filteredAthletes.map((a) => (
                          <label
                            key={a.id}
                            className="flex items-center gap-2 px-2 py-2 min-h-[44px] rounded hover:bg-secondary-muted/10 cursor-pointer transition-colors"
                          >
                            <input
                              type="checkbox"
                              checked={selectedAthleteIds.has(a.id)}
                              onChange={() => toggleAthlete(a.id)}
                              className="w-4 h-4 rounded border-secondary-muted bg-transparent text-accent focus:ring-accent accent-[#33CBF4]"
                            />
                            <span className="text-sm">{getAthleteName(a)}</span>
                          </label>
                        ))}
                      </div>
                    </>
                  )}

                  <div className="flex gap-3 pt-4">
                    <button
                      type="button"
                      onClick={() => setStep('template')}
                      className="btn-secondary flex-1"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={() => setStep('review')}
                      disabled={selectedAthleteIds.size === 0}
                      className="btn-primary flex-1 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}

              {/* Step 3: Review & Confirm */}
              {step === 'review' && (
                <div>
                  {/* Summary */}
                  <div className="space-y-3 mb-4">
                    <div className="border border-secondary-muted/30 rounded-lg p-3 bg-secondary-muted/5">
                      <p className="text-xs text-white/40 mb-1">Template</p>
                      <p className="text-sm font-medium">{selectedTemplate?.template_name}</p>
                      <p className="text-xs text-white/40 mt-0.5">
                        {selectedTemplate?.training_type} &middot; {selectedTemplate?.exercises.length} exercise{(selectedTemplate?.exercises.length ?? 0) !== 1 ? 's' : ''}
                      </p>
                    </div>

                    <div>
                      <label className="block text-sm text-white/60 mb-1">Session Date</label>
                      <input
                        type="date"
                        value={sessionDate}
                        onChange={(e) => setSessionDate(e.target.value)}
                        className="input w-full"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-white/60 mb-1">Notes (optional)</label>
                      <textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        className="input w-full resize-none"
                        rows={2}
                        maxLength={1000}
                        placeholder="Session notes..."
                      />
                    </div>

                    {/* Selected athletes list */}
                    <div>
                      <p className="text-sm text-white/60 mb-1">
                        Athletes ({selectedAthleteIds.size})
                      </p>
                      <div className="border border-secondary-muted/30 rounded-lg p-2 max-h-[30vh] sm:max-h-[20vh] overflow-y-auto">
                        {selectedAthleteNames.map((name, i) => (
                          <p key={i} className="text-sm py-0.5">
                            {name}
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Error display */}
                  {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setStep('athletes')}
                      disabled={submitting}
                      className="btn-secondary flex-1"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={submitting || !sessionDate}
                      className="btn-primary flex-1 disabled:opacity-50"
                    >
                      {submitting
                        ? 'Assigning...'
                        : `Assign to ${selectedAthleteIds.size} Athlete${selectedAthleteIds.size !== 1 ? 's' : ''}`}
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </>
      )}
    </ResponsiveModal>
  );
}
