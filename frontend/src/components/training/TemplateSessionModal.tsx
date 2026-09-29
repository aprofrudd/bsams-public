'use client';

import { useState, useEffect } from 'react';
import { sessionTemplatesApi, trainingApi, programsApi } from '@/lib/api';
import type { TargetPreviewExercise } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { SessionTemplate, InstalledProgramTemplate } from '@/lib/types';

const TIER_LABELS: Record<string, string> = {
  foundation: 'Foundation',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
};

const TIER_COLORS: Record<string, string> = {
  foundation: 'bg-green-500/20 text-green-400 border-green-500/30',
  intermediate: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  advanced: 'bg-red-500/20 text-red-400 border-red-500/30',
};

function formatIntensityRange(ex: TargetPreviewExercise): string {
  if (ex.intensity_min == null || ex.intensity_max == null) return 'No data';
  if (ex.intensity_type === 'power_watts') return `${Math.round(ex.intensity_min)}-${Math.round(ex.intensity_max)}W`;
  if (ex.intensity_type === 'speed_kmh') return `${ex.intensity_min}-${ex.intensity_max} km/h`;
  if (ex.intensity_type === 'rpe') return `RPE ${ex.intensity_min}-${ex.intensity_max}`;
  return `${ex.intensity_min}-${ex.intensity_max}`;
}

interface TemplateSessionModalProps {
  athleteId: string;
  onClose: () => void;
  onCreated: () => void;
}

export function TemplateSessionModal({ athleteId, onClose, onCreated }: TemplateSessionModalProps) {
  const [step, setStep] = useState<1 | 2>(1);
  const [templates, setTemplates] = useState<SessionTemplate[]>([]);
  const [goldStandardTemplates, setGoldStandardTemplates] = useState<SessionTemplate[]>([]);
  const [programTemplates, setProgramTemplates] = useState<InstalledProgramTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<SessionTemplate | null>(null);
  const [selectedSource, setSelectedSource] = useState<'own' | 'program' | 'gold_standard'>('own');

  // Step 2 fields
  const [sessionDate, setSessionDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Target preview
  const [targetPreview, setTargetPreview] = useState<TargetPreviewExercise[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [templateData, programData, goldData] = await Promise.all([
          sessionTemplatesApi.list(),
          programsApi.installedTemplates().catch(() => [] as InstalledProgramTemplate[]),
          sessionTemplatesApi.listGoldStandard().catch(() => [] as SessionTemplate[]),
        ]);
        setTemplates(templateData);
        setProgramTemplates(programData);
        setGoldStandardTemplates(goldData);
      } catch {
        setError('Failed to load templates');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function handleSelectTemplate(template: SessionTemplate) {
    setSelectedTemplate(template);
    setSelectedSource('own');
    setNotes(template.notes || '');
    setTargetPreview(null);
    setStep(2);
  }

  function handleSelectGoldStandard(template: SessionTemplate) {
    setSelectedTemplate(template);
    setSelectedSource('gold_standard');
    setNotes(template.notes || '');
    setTargetPreview(null);
    setStep(2);

    // Auto-preview targets for gold standard conditioning templates
    if (template.tier && athleteId) {
      setPreviewLoading(true);
      sessionTemplatesApi.previewTargets(template.id, athleteId)
        .then((res) => setTargetPreview(res.exercises))
        .catch(() => setTargetPreview(null))
        .finally(() => setPreviewLoading(false));
    }
  }

  function handleSelectProgramTemplate(pt: InstalledProgramTemplate) {
    // Map to SessionTemplate-compatible shape
    const mapped: SessionTemplate = {
      id: pt.id,
      coach_id: '',
      template_name: pt.template_name,
      training_type: pt.training_type,
      description: null,
      notes: pt.notes,
      template_category: null,
      tier: null,
      exercises: pt.exercises.map((ex) => ({
        id: '',
        template_id: pt.id,
        exercise_library_id: null,
        exercise_name: ex.exercise_name,
        exercise_category: ex.exercise_category,
        order_index: ex.order_index,
        sets: ex.sets,
        reps: ex.reps,
        weight_kg: ex.weight_kg,
        tempo: ex.tempo,
        rest_seconds: ex.rest_seconds,
        duration_seconds: ex.duration_seconds,
        distance_meters: ex.distance_meters,
        intensity_type: ex.intensity_type,
        intensity_value: ex.intensity_value,
        rest_between_reps_seconds: ex.rest_between_reps_seconds,
        rest_between_reps: null,
        rep_intensity_values: ex.rep_intensity_values,
        notes: ex.notes,
        created_at: '',
        updated_at: '',
      })),
      created_at: '',
      updated_at: '',
    };
    setSelectedTemplate(mapped);
    setSelectedSource('program');
    setNotes(pt.notes || '');
    setTargetPreview(null);
    setStep(2);
  }

  async function handleSubmit() {
    if (!selectedTemplate) return;
    setSubmitting(true);
    setError(null);
    try {
      const session = await trainingApi.createSession({
        athlete_id: athleteId,
        session_date: sessionDate,
        training_type: selectedTemplate.training_type,
        description: selectedTemplate.description || undefined,
        notes: notes || undefined,
        status: 'assigned',
      });
      if (selectedSource === 'program') {
        await programsApi.applyTemplate(selectedTemplate.id, session.id);
      } else {
        await sessionTemplatesApi.apply(selectedTemplate.id, session.id);
      }
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session');
      setSubmitting(false);
    }
  }

  // Group program templates by program name
  const programGroups = programTemplates.reduce<Record<string, InstalledProgramTemplate[]>>((acc, t) => {
    if (!acc[t.program_name]) acc[t.program_name] = [];
    acc[t.program_name].push(t);
    return acc;
  }, {});

  const hasAnyTemplates = templates.length > 0 || programTemplates.length > 0 || goldStandardTemplates.length > 0;

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title="Create from Template" zIndex={60}>
      {step === 1 && (
        <>
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <p className="text-red-400 text-sm py-4 text-center">{error}</p>
          ) : !hasAnyTemplates ? (
            <p className="text-white/60 text-sm py-8 text-center">
              No templates yet. Create templates in the Library page or install a program.
            </p>
          ) : (
            <div className="space-y-4">
              {/* Gold Standard Conditioning */}
              {goldStandardTemplates.length > 0 && (
                <div>
                  <p className="text-xs text-white/40 uppercase tracking-wider mb-2">Gold Standard Conditioning</p>
                  <div className="space-y-2">
                    {goldStandardTemplates.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => handleSelectGoldStandard(t)}
                        className="w-full text-left border border-secondary-muted rounded-lg p-3 hover:border-accent/30 transition-colors"
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium text-sm">{t.template_name}</p>
                          {t.tier && (
                            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${TIER_COLORS[t.tier] || ''}`}>
                              {TIER_LABELS[t.tier] || t.tier}
                            </span>
                          )}
                        </div>
                        {t.description && (
                          <p className="text-xs text-white/50 mb-1 line-clamp-2">{t.description}</p>
                        )}
                        <p className="text-xs text-white/40">
                          {t.training_type} &middot; {t.exercises.length} exercise{t.exercises.length !== 1 ? 's' : ''}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* My Templates */}
              {templates.length > 0 && (
                <div>
                  <p className="text-xs text-white/40 uppercase tracking-wider mb-2">My Templates</p>
                  <div className="space-y-2">
                    {templates.map((t) => (
                      <button
                        key={t.id}
                        onClick={() => handleSelectTemplate(t)}
                        className="w-full text-left border border-secondary-muted rounded-lg p-3 hover:border-accent/30 transition-colors"
                      >
                        <p className="font-medium text-sm">{t.template_name}</p>
                        <p className="text-xs text-white/40">
                          {t.training_type} &middot; {t.exercises.length} exercise{t.exercises.length !== 1 ? 's' : ''}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Program Templates */}
              {Object.entries(programGroups).map(([programName, pts]) => (
                <div key={programName}>
                  <p className="text-xs text-white/40 uppercase tracking-wider mb-2">{programName}</p>
                  <div className="space-y-2">
                    {pts.map((pt) => (
                      <button
                        key={pt.id}
                        onClick={() => handleSelectProgramTemplate(pt)}
                        className="w-full text-left border border-secondary-muted rounded-lg p-3 hover:border-accent/30 transition-colors"
                      >
                        <p className="font-medium text-sm">{pt.template_name}</p>
                        <p className="text-xs text-white/40">
                          {pt.training_type} &middot; {pt.exercises.length} exercise{pt.exercises.length !== 1 ? 's' : ''}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {step === 2 && selectedTemplate && (
        <div className="space-y-4">
          <button
            onClick={() => { setStep(1); setError(null); setTargetPreview(null); }}
            className="text-xs text-accent hover:text-accent/80 transition-colors"
          >
            &larr; Back to templates
          </button>

          <div className="border border-secondary-muted/30 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <p className="font-medium text-sm">{selectedTemplate.template_name}</p>
              {selectedTemplate.tier && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${TIER_COLORS[selectedTemplate.tier] || ''}`}>
                  {TIER_LABELS[selectedTemplate.tier] || selectedTemplate.tier}
                </span>
              )}
            </div>
            {selectedTemplate.description && (
              <p className="text-xs text-white/50 mb-1">{selectedTemplate.description}</p>
            )}
            <p className="text-xs text-white/40">
              {selectedTemplate.training_type} &middot; {selectedTemplate.exercises.length} exercise{selectedTemplate.exercises.length !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Target preview for gold standard templates */}
          {selectedSource === 'gold_standard' && (
            <div className="border border-secondary-muted/30 rounded-lg p-3">
              <p className="text-xs text-white/40 uppercase tracking-wider mb-2">Athlete Targets</p>
              {previewLoading ? (
                <div className="flex items-center gap-2 text-xs text-white/40">
                  <div className="w-3 h-3 border border-accent border-t-transparent rounded-full animate-spin" />
                  Resolving targets...
                </div>
              ) : targetPreview ? (
                <div className="space-y-1">
                  {targetPreview.map((ex, i) => (
                    <div key={i} className="flex justify-between text-xs">
                      <span className="text-white/60">{ex.exercise_name}</span>
                      <span className={ex.source === 'missing' ? 'text-amber-400' : 'text-accent'}>
                        {formatIntensityRange(ex)}
                        {ex.source !== 'missing' && ex.source !== 'default' && ex.source !== 'no_tier' && (
                          <span className="text-white/30 ml-1">({ex.source.replace('_', ' ')})</span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-white/40">No target data available</p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm text-white/60 mb-1">Session Date</label>
            <input
              type="date"
              value={sessionDate}
              onChange={(e) => setSessionDate(e.target.value)}
              className="w-full px-3 py-2 min-h-[44px] rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Notes (optional)</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent resize-none"
              placeholder="Session notes..."
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={submitting || !sessionDate}
            className="w-full py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors disabled:opacity-50"
          >
            {submitting ? 'Creating...' : 'Create Session'}
          </button>
        </div>
      )}
    </ResponsiveModal>
  );
}
