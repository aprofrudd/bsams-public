'use client';

import { useState, useEffect } from 'react';
import { assessmentApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { MovementAssessment } from '@/lib/types';

interface AssessmentFormProps {
  athleteId: string;
  existingAssessment?: MovementAssessment | null;
  onClose: () => void;
  onSaved: () => void;
}

// --- NASM Checklist Definitions ---

interface CompensationDef {
  key: string;
  label: string;
  hasSide: boolean;
}

interface CheckpointDef {
  key: string;
  label: string;
  compensations: CompensationDef[];
}

const OVERHEAD_SQUAT_CHECKPOINTS: CheckpointDef[] = [
  {
    key: 'feet_ankles',
    label: 'Feet & Ankles',
    compensations: [
      { key: 'turn_out', label: 'Turn Out', hasSide: true },
      { key: 'flatten', label: 'Flatten (Pronate)', hasSide: true },
      { key: 'heels_rise', label: 'Heels Rise', hasSide: false },
    ],
  },
  {
    key: 'knees',
    label: 'Knees',
    compensations: [
      { key: 'valgus', label: 'Knee Valgus', hasSide: true },
      { key: 'excessive_forward', label: 'Excessive Forward', hasSide: false },
    ],
  },
  {
    key: 'lphc',
    label: 'LPHC (Lumbo-Pelvic-Hip)',
    compensations: [
      { key: 'forward_lean', label: 'Forward Lean', hasSide: false },
      { key: 'low_back_arch', label: 'Low Back Arch', hasSide: false },
      { key: 'hip_shift', label: 'Hip Shift', hasSide: true },
    ],
  },
  {
    key: 'shoulders',
    label: 'Shoulders',
    compensations: [
      { key: 'arms_fall_forward', label: 'Arms Fall Forward', hasSide: false },
    ],
  },
  {
    key: 'head',
    label: 'Head',
    compensations: [
      { key: 'forward_protrusion', label: 'Forward Protrusion', hasSide: false },
    ],
  },
];

const SINGLE_LEG_SQUAT_CHECKPOINTS: CheckpointDef[] = [
  {
    key: 'knees',
    label: 'Knees',
    compensations: [
      { key: 'valgus', label: 'Knee Valgus', hasSide: false },
    ],
  },
  {
    key: 'lphc',
    label: 'LPHC (Lumbo-Pelvic-Hip)',
    compensations: [
      { key: 'hip_hike', label: 'Hip Hike', hasSide: false },
      { key: 'hip_drop', label: 'Hip Drop', hasSide: false },
      { key: 'trunk_rotation', label: 'Trunk Rotation', hasSide: false },
    ],
  },
  {
    key: 'feet_ankles',
    label: 'Feet & Ankles',
    compensations: [
      { key: 'flatten', label: 'Flatten (Pronate)', hasSide: false },
    ],
  },
  {
    key: 'head',
    label: 'Balance',
    compensations: [
      { key: 'loss_of_balance', label: 'Loss of Balance', hasSide: false },
    ],
  },
];

const ASSESSMENT_TYPES = [
  { value: 'overhead_squat', label: 'Overhead Squat' },
  { value: 'single_leg_squat_left', label: 'Single Leg Squat (Left)' },
  { value: 'single_leg_squat_right', label: 'Single Leg Squat (Right)' },
];

const SEVERITY_OPTIONS = ['mild', 'moderate', 'significant'] as const;
const SIDE_OPTIONS = ['left', 'right', 'bilateral'] as const;
const VIEW_TYPE_OPTIONS = ['anterior', 'lateral', 'posterior'] as const;

// --- Compensation state ---

interface CompensationState {
  observed: boolean;
  severity: string;
  side: string;
}

type FindingsState = Record<string, Record<string, CompensationState>>;

function getCheckpointsForType(type: string): CheckpointDef[] {
  if (type.startsWith('single_leg_squat')) return SINGLE_LEG_SQUAT_CHECKPOINTS;
  return OVERHEAD_SQUAT_CHECKPOINTS;
}

function buildInitialFindings(type: string, existing?: Record<string, any>): FindingsState {
  const checkpoints = getCheckpointsForType(type);
  const state: FindingsState = {};
  for (const cp of checkpoints) {
    state[cp.key] = {};
    for (const comp of cp.compensations) {
      const existingComp = existing?.[cp.key]?.[comp.key];
      state[cp.key][comp.key] = {
        observed: existingComp?.observed ?? false,
        severity: existingComp?.severity ?? 'mild',
        side: existingComp?.side ?? (comp.hasSide ? 'bilateral' : ''),
      };
    }
  }
  return state;
}

function findingsToPayload(findings: FindingsState): Record<string, any> {
  const payload: Record<string, any> = {};
  for (const [regionKey, compensations] of Object.entries(findings)) {
    const regionPayload: Record<string, any> = {};
    for (const [compKey, state] of Object.entries(compensations)) {
      const entry: Record<string, any> = { observed: state.observed };
      if (state.observed) {
        entry.severity = state.severity;
        if (state.side) entry.side = state.side;
      }
      regionPayload[compKey] = entry;
    }
    payload[regionKey] = regionPayload;
  }
  return payload;
}

// --- Summary generation ---

const COMPENSATION_LABELS: Record<string, string> = {
  turn_out: 'foot turn out',
  flatten: 'foot pronation',
  heels_rise: 'heels rise',
  valgus: 'knee valgus',
  excessive_forward: 'excessive forward knee',
  forward_lean: 'forward lean',
  low_back_arch: 'low back arch',
  hip_shift: 'hip shift',
  arms_fall_forward: 'arms fall forward',
  forward_protrusion: 'forward head protrusion',
  hip_hike: 'hip hike',
  hip_drop: 'hip drop',
  trunk_rotation: 'trunk rotation',
  loss_of_balance: 'loss of balance',
};

const TYPE_LABELS: Record<string, string> = {
  overhead_squat: 'Overhead Squat',
  single_leg_squat_left: 'Single Leg Squat (Left)',
  single_leg_squat_right: 'Single Leg Squat (Right)',
};

function generateSummary(findings: FindingsState, assessmentType: string): string {
  const observed: string[] = [];
  for (const compensations of Object.values(findings)) {
    for (const [compKey, state] of Object.entries(compensations)) {
      if (state.observed) {
        let desc = COMPENSATION_LABELS[compKey] ?? compKey;
        if (state.side) desc = `${state.side} ${desc}`;
        desc += ` (${state.severity})`;
        observed.push(desc);
      }
    }
  }

  const typeLabel = TYPE_LABELS[assessmentType] ?? assessmentType;
  if (observed.length === 0) {
    return `${typeLabel}: No compensations observed.`;
  }
  return `${typeLabel}: ${observed.join(', ')}.`;
}

// --- Photo state ---
interface PhotoFile {
  file: File;
  viewType: string;
  preview: string;
}

export function AssessmentForm({
  athleteId,
  existingAssessment,
  onClose,
  onSaved,
}: AssessmentFormProps) {
  const isEdit = !!existingAssessment;

  const [assessmentDate, setAssessmentDate] = useState(
    existingAssessment ? existingAssessment.assessment_date.slice(0, 10) : ''
  );
  const [assessmentType, setAssessmentType] = useState(
    existingAssessment?.assessment_type ?? 'overhead_squat'
  );
  const [findings, setFindings] = useState<FindingsState>(() =>
    buildInitialFindings(
      existingAssessment?.assessment_type ?? 'overhead_squat',
      existingAssessment?.findings
    )
  );
  const [notes, setNotes] = useState(existingAssessment?.notes ?? '');
  const [photos, setPhotos] = useState<PhotoFile[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Rebuild findings when assessment type changes
  useEffect(() => {
    if (!isEdit) {
      setFindings(buildInitialFindings(assessmentType));
    }
  }, [assessmentType, isEdit]);

  // Cleanup photo previews on unmount
  useEffect(() => {
    return () => {
      photos.forEach((p) => URL.revokeObjectURL(p.preview));
    };
  }, [photos]);

  function updateCompensation(
    regionKey: string,
    compKey: string,
    field: keyof CompensationState,
    value: string | boolean
  ) {
    setFindings((prev) => ({
      ...prev,
      [regionKey]: {
        ...prev[regionKey],
        [compKey]: {
          ...prev[regionKey][compKey],
          [field]: value,
        },
      },
    }));
  }

  function handlePhotoAdd(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files) return;
    const newPhotos: PhotoFile[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!file.type.startsWith('image/')) continue;
      if (file.size > 10 * 1024 * 1024) continue; // 10MB limit
      newPhotos.push({
        file,
        viewType: 'anterior',
        preview: URL.createObjectURL(file),
      });
    }
    setPhotos((prev) => [...prev, ...newPhotos]);
    // Reset input
    e.target.value = '';
  }

  function removePhoto(index: number) {
    setPhotos((prev) => {
      URL.revokeObjectURL(prev[index].preview);
      return prev.filter((_, i) => i !== index);
    });
  }

  function updatePhotoViewType(index: number, viewType: string) {
    setPhotos((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], viewType };
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!isEdit && !assessmentDate) {
      setError('Assessment date is required');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const findingsPayload = findingsToPayload(findings);
      const summary = generateSummary(findings, assessmentType);

      let assessmentId: string;

      if (isEdit && existingAssessment) {
        const updated = await assessmentApi.updateAssessment(existingAssessment.id, {
          ...(assessmentDate ? { assessment_date: assessmentDate } : {}),
          assessment_type: assessmentType,
          findings: findingsPayload,
          notes: notes || undefined,
          summary,
        });
        assessmentId = updated.id;
      } else {
        const created = await assessmentApi.createAssessment({
          athlete_id: athleteId,
          assessment_date: assessmentDate,
          assessment_type: assessmentType,
          findings: findingsPayload,
          notes: notes || undefined,
          summary,
        });
        assessmentId = created.id;
      }

      // Upload photos sequentially
      for (const photo of photos) {
        try {
          await assessmentApi.uploadPhoto(assessmentId, photo.file, photo.viewType);
        } catch {
          // Best effort photo upload
        }
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save assessment');
    } finally {
      setSaving(false);
    }
  }

  const checkpoints = getCheckpointsForType(assessmentType);

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="lg" title={isEdit ? 'Edit Assessment' : 'New Movement Assessment'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Date + Type */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-white/60 mb-1">Date</label>
              <input
                type="date"
                value={assessmentDate}
                onChange={(e) => setAssessmentDate(e.target.value)}
                className="input w-full"
                required={!isEdit}
              />
            </div>
            <div>
              <label className="block text-sm text-white/60 mb-1">Assessment Type</label>
              <select
                value={assessmentType}
                onChange={(e) => setAssessmentType(e.target.value)}
                className="input w-full"
              >
                {ASSESSMENT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* NASM Checklist */}
          <div>
            <label className="block text-sm text-white/60 mb-2">Movement Checklist</label>
            <div className="space-y-3">
              {checkpoints.map((cp) => (
                <div key={cp.key} className="border border-secondary-muted/40 rounded-lg p-3">
                  <div className="text-xs font-heading uppercase tracking-wider text-accent mb-2">
                    {cp.label}
                  </div>
                  <div className="space-y-2">
                    {cp.compensations.map((comp) => {
                      const state = findings[cp.key]?.[comp.key];
                      if (!state) return null;
                      return (
                        <div key={comp.key} className="space-y-1">
                          <div className="flex items-center gap-3 min-h-[44px]">
                            <label className="flex items-center gap-2 cursor-pointer min-h-[44px]">
                              <input
                                type="checkbox"
                                checked={state.observed}
                                onChange={(e) =>
                                  updateCompensation(cp.key, comp.key, 'observed', e.target.checked)
                                }
                                className="w-5 h-5 rounded border-secondary-muted accent-accent"
                              />
                              <span className="text-sm text-white/80">{comp.label}</span>
                            </label>
                          </div>
                          {state.observed && (
                            <div className="flex items-center gap-2 ml-6 flex-wrap">
                              <select
                                value={state.severity}
                                onChange={(e) =>
                                  updateCompensation(cp.key, comp.key, 'severity', e.target.value)
                                }
                                className="input text-xs py-1 px-2 w-auto"
                              >
                                {SEVERITY_OPTIONS.map((s) => (
                                  <option key={s} value={s}>
                                    {s.charAt(0).toUpperCase() + s.slice(1)}
                                  </option>
                                ))}
                              </select>
                              {comp.hasSide && (
                                <select
                                  value={state.side}
                                  onChange={(e) =>
                                    updateCompensation(cp.key, comp.key, 'side', e.target.value)
                                  }
                                  className="input text-xs py-1 px-2 w-auto"
                                >
                                  {SIDE_OPTIONS.map((s) => (
                                    <option key={s} value={s}>
                                      {s.charAt(0).toUpperCase() + s.slice(1)}
                                    </option>
                                  ))}
                                </select>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Photo Upload */}
          <div>
            <label className="block text-sm text-white/60 mb-2">Photos (optional)</label>
            <input
              type="file"
              accept="image/*"
              multiple
              onChange={handlePhotoAdd}
              className="block w-full min-h-[44px] text-sm text-white/60 file:mr-3 file:py-2.5 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-accent file:text-[#090A3D] file:cursor-pointer hover:file:bg-accent/80 active:file:bg-accent/70"
            />
            {photos.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-2">
                {photos.map((p, i) => (
                  <div key={i} className="relative group">
                    <img
                      src={p.preview}
                      alt={`Photo ${i + 1}`}
                      className="w-full h-24 object-cover rounded-lg border border-secondary-muted/30"
                    />
                    <select
                      value={p.viewType}
                      onChange={(e) => updatePhotoViewType(i, e.target.value)}
                      className="absolute bottom-1 left-1 bg-black/70 text-white text-xs border-none rounded px-1 py-0.5"
                    >
                      {VIEW_TYPE_OPTIONS.map((v) => (
                        <option key={v} value={v}>
                          {v}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      onClick={() => removePhoto(i)}
                      className="absolute top-0 right-0 bg-black/60 text-red-400 rounded-full min-w-[28px] min-h-[28px] p-2 flex items-center justify-center text-sm hover:bg-black/80 active:bg-black/90"
                    >
                      x
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm text-white/60 mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full"
              rows={2}
              placeholder="Additional observations..."
              maxLength={2000}
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
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Save Assessment'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
