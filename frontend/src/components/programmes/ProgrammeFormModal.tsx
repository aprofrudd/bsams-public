'use client';

import { useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { SimpleSectionEditor } from './SimpleSectionEditor';
import { SupersetSectionEditor } from './SupersetSectionEditor';
import { programmeFormsApi } from '@/lib/api';
import type {
  ProgrammeForm,
  ProgrammeFormData,
  ProgrammeFormSession,
  ProgrammeFormSection,
} from '@/lib/types';

const SECTION_DEFS = [
  { key: 'hand_prep', label: 'HAND PREP', type: 'simple' },
  { key: 'extended_warmup', label: 'EXTENDED WARM-UP', type: 'simple' },
  { key: 'superset_1', label: 'SUPERSET 1', type: 'superset' },
  { key: 'superset_2', label: 'SUPERSET 2', type: 'superset' },
  { key: 'superset_3', label: 'SUPERSET 3', type: 'superset' },
  { key: 'core_circuit', label: 'CORE CIRCUIT', type: 'simple' },
  { key: 'perform_separate', label: 'PERFORM SEPARATE', type: 'simple' },
] as const;

interface ProgrammeFormModalProps {
  existingForm: ProgrammeForm | null;
  onClose: () => void;
  onSaved: () => void;
}

function createEmptySessions(count: number): ProgrammeFormSession[] {
  return Array.from({ length: count }, (_, i) => ({
    session_number: i + 1,
    session_name: `Session ${i + 1}`,
    sections: [],
  }));
}

function adjustSessions(
  existing: ProgrammeFormSession[],
  targetCount: number
): ProgrammeFormSession[] {
  if (existing.length === targetCount) return existing;
  if (existing.length > targetCount) return existing.slice(0, targetCount);
  const extra = createEmptySessions(targetCount - existing.length);
  return [
    ...existing,
    ...extra.map((s, i) => ({
      ...s,
      session_number: existing.length + i + 1,
      session_name: `Session ${existing.length + i + 1}`,
    })),
  ];
}

export function ProgrammeFormModal({ existingForm, onClose, onSaved }: ProgrammeFormModalProps) {
  const isEditing = existingForm !== null;

  const [formName, setFormName] = useState(existingForm?.form_name ?? '');
  const [description, setDescription] = useState(existingForm?.description ?? '');
  const [numWeeks, setNumWeeks] = useState(existingForm?.num_weeks ?? 4);
  const [sessionsPerWeek, setSessionsPerWeek] = useState(existingForm?.sessions_per_week ?? 3);
  const [formData, setFormData] = useState<ProgrammeFormData>(
    existingForm?.form_data ?? { sessions: createEmptySessions(3) }
  );
  const [activeSession, setActiveSession] = useState(0);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleSessionsPerWeekChange(value: number) {
    const clamped = Math.min(7, Math.max(1, value));
    setSessionsPerWeek(clamped);
    setFormData((prev) => ({
      sessions: adjustSessions(prev.sessions, clamped),
    }));
    if (activeSession >= clamped) setActiveSession(clamped - 1);
  }

  function handleNumWeeksChange(value: number) {
    setNumWeeks(Math.min(16, Math.max(1, value)));
  }

  function toggleSection(key: string) {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function addSection(sessionIndex: number, sectionKey: string) {
    setFormData((prev) => ({
      sessions: prev.sessions.map((session, si) => {
        if (si !== sessionIndex) return session;
        const newSection: ProgrammeFormSection = {
          section_type: sectionKey,
          exercises: [],
        };
        // Insert in canonical order
        const order: string[] = SECTION_DEFS.map((d) => d.key);
        const updated = [...session.sections, newSection].sort(
          (a, b) => order.indexOf(a.section_type) - order.indexOf(b.section_type)
        );
        return { ...session, sections: updated };
      }),
    }));
    setExpandedSections((prev) => new Set(prev).add(`${sessionIndex}-${sectionKey}`));
  }

  function removeSection(sessionIndex: number, sectionKey: string) {
    setFormData((prev) => ({
      sessions: prev.sessions.map((session, si) =>
        si === sessionIndex
          ? { ...session, sections: session.sections.filter((s) => s.section_type !== sectionKey) }
          : session
      ),
    }));
    setExpandedSections((prev) => {
      const next = new Set(prev);
      next.delete(`${sessionIndex}-${sectionKey}`);
      return next;
    });
  }

  function updateSection(sessionIndex: number, sectionType: string, update: Partial<ProgrammeFormSection>) {
    setFormData((prev) => ({
      sessions: prev.sessions.map((session, si) =>
        si === sessionIndex
          ? {
              ...session,
              sections: session.sections.map((sec) =>
                sec.section_type === sectionType ? { ...sec, ...update } : sec
              ),
            }
          : session
      ),
    }));
  }

  function updateSessionName(sessionIndex: number, name: string) {
    setFormData((prev) => ({
      sessions: prev.sessions.map((session, si) =>
        si === sessionIndex ? { ...session, session_name: name } : session
      ),
    }));
  }

  async function handleSave() {
    if (!formName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      if (isEditing && existingForm) {
        await programmeFormsApi.update(existingForm.id, {
          form_name: formName.trim(),
          description: description.trim() || undefined,
          num_weeks: numWeeks,
          sessions_per_week: sessionsPerWeek,
          form_data: formData,
        });
      } else {
        await programmeFormsApi.create({
          form_name: formName.trim(),
          description: description.trim() || undefined,
          num_weeks: numWeeks,
          sessions_per_week: sessionsPerWeek,
          form_data: formData,
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save form');
    } finally {
      setSaving(false);
    }
  }

  const currentSession = formData.sessions[activeSession];

  return (
    <ResponsiveModal isOpen onClose={onClose} maxWidth="3xl" title={isEditing ? 'Edit Programme Form' : 'New Programme Form'}>
      <div className="space-y-4">
        {/* Header */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="sm:col-span-2">
            <label className="block text-xs text-white/50 mb-1">Form Name</label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              className="input-field w-full"
              placeholder="e.g. 4-Week Strength Programme"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">Weeks</label>
            <input
              type="number"
              value={numWeeks}
              onChange={(e) => handleNumWeeksChange(parseInt(e.target.value) || 1)}
              className="input-field w-full"
              min={1}
              max={16}
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">Sessions/Week</label>
            <input
              type="number"
              value={sessionsPerWeek}
              onChange={(e) => handleSessionsPerWeekChange(parseInt(e.target.value) || 1)}
              className="input-field w-full"
              min={1}
              max={7}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-white/50 mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="input-field w-full"
            rows={2}
            placeholder="Optional description..."
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">&times;</button>
          </div>
        )}

        {/* Session Tabs */}
        <div className="flex items-center gap-1 flex-wrap">
          {formData.sessions.map((session, i) => (
            <button
              key={i}
              onClick={() => setActiveSession(i)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeSession === i
                  ? 'bg-accent text-[#090A3D]'
                  : 'bg-white/5 text-white/60 hover:bg-white/10'
              }`}
            >
              {session.session_name || `Session ${i + 1}`}
            </button>
          ))}
        </div>

        {/* Session Name */}
        {currentSession && (
          <div>
            <label className="block text-xs text-white/50 mb-1">Session Name</label>
            <input
              type="text"
              value={currentSession.session_name}
              onChange={(e) => updateSessionName(activeSession, e.target.value)}
              className="input-field w-full"
              placeholder="e.g. Upper Body"
            />
          </div>
        )}

        {/* Section Panels */}
        {currentSession && (
          <div className="space-y-1">
            {SECTION_DEFS.map((def) => {
              const section = currentSession.sections.find(
                (s) => s.section_type === def.key
              );
              if (!section) return null;
              const isExpanded = expandedSections.has(`${activeSession}-${def.key}`);
              const exerciseCount = section.exercises.length;

              return (
                <div key={def.key} className="border border-secondary-muted rounded-lg overflow-visible">
                  <div className="flex items-center">
                    <button
                      onClick={() => toggleSection(`${activeSession}-${def.key}`)}
                      className="flex-1 flex items-center justify-between px-3 py-2 min-h-[44px] text-left hover:bg-white/5 transition-colors"
                    >
                      <span className="text-xs font-bold tracking-wider text-accent">{def.label}</span>
                      <span className="text-[10px] text-white/40">
                        {exerciseCount > 0 && `${exerciseCount} exercise${exerciseCount !== 1 ? 's' : ''}`}
                        {' '}{isExpanded ? '\u25B2' : '\u25BC'}
                      </span>
                    </button>
                    <button
                      onClick={() => removeSection(activeSession, def.key)}
                      className="px-2 py-2 min-h-[44px] text-white/30 hover:text-red-400 transition-colors"
                      title="Remove section"
                    >
                      &times;
                    </button>
                  </div>
                  {isExpanded && (
                    <div className="px-3 pb-3">
                      {def.type === 'superset' ? (
                        <SupersetSectionEditor
                          exercises={section.exercises}
                          onChange={(exercises) =>
                            updateSection(activeSession, def.key, { exercises })
                          }
                          numWeeks={numWeeks}
                        />
                      ) : (
                        <SimpleSectionEditor
                          exercises={section.exercises}
                          onChange={(exercises) =>
                            updateSection(activeSession, def.key, { exercises })
                          }
                          sectionType={def.key}
                          circuitSets={section.circuit_sets}
                          onCircuitSetsChange={
                            def.key === 'core_circuit'
                              ? (sets) => updateSection(activeSession, def.key, { circuit_sets: sets })
                              : undefined
                          }
                        />
                      )}
                    </div>
                  )}
                </div>
              );
            })}

            {/* Add Section dropdown */}
            {(() => {
              const presentKeys = new Set(currentSession.sections.map((s) => s.section_type));
              const available = SECTION_DEFS.filter((d) => !presentKeys.has(d.key));
              if (available.length === 0) return null;
              return (
                <select
                  value=""
                  onChange={(e) => {
                    if (e.target.value) addSection(activeSession, e.target.value);
                  }}
                  className="input-field w-full text-sm text-white/60"
                >
                  <option value="">+ Add Section...</option>
                  {available.map((d) => (
                    <option key={d.key} value={d.key}>{d.label}</option>
                  ))}
                </select>
              );
            })()}
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 pt-2 border-t border-secondary-muted">
          <button
            onClick={onClose}
            className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!formName.trim() || saving}
            className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : isEditing ? 'Save Changes' : 'Create Form'}
          </button>
        </div>
      </div>
    </ResponsiveModal>
  );
}
