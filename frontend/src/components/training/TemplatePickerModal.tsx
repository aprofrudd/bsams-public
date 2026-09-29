'use client';

import { useState, useEffect } from 'react';
import { sessionTemplatesApi, programsApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { SessionTemplate, InstalledProgramTemplate } from '@/lib/types';

interface TemplatePickerModalProps {
  sessionId: string;
  existingExerciseCount?: number;
  onClose: () => void;
  onApplied: () => void;
}

export function TemplatePickerModal({ sessionId, existingExerciseCount = 0, onClose, onApplied }: TemplatePickerModalProps) {
  const [templates, setTemplates] = useState<SessionTemplate[]>([]);
  const [programTemplates, setProgramTemplates] = useState<InstalledProgramTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState<string | null>(null);

  // Track program template IDs for routing apply calls
  const programTemplateIds = new Set(programTemplates.map(pt => pt.id));

  useEffect(() => {
    async function load() {
      try {
        const [templateData, programData] = await Promise.all([
          sessionTemplatesApi.list(),
          programsApi.installedTemplates().catch(() => [] as InstalledProgramTemplate[]),
        ]);
        setTemplates(templateData);
        setProgramTemplates(programData);
      } catch {
        setError('Failed to load templates');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleApply(templateId: string, isProgram: boolean) {
    if (existingExerciseCount > 0) {
      const confirmed = window.confirm(
        `This session already has ${existingExerciseCount} exercise(s). Template exercises will be added to the existing list. Continue?`
      );
      if (!confirmed) return;
    }

    setApplying(templateId);
    setError(null);
    try {
      if (isProgram) {
        await programsApi.applyTemplate(templateId, sessionId);
      } else {
        await sessionTemplatesApi.apply(templateId, sessionId);
      }
      onApplied();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply template');
      setApplying(null);
    }
  }

  // Group program templates by program name
  const programGroups = programTemplates.reduce<Record<string, InstalledProgramTemplate[]>>((acc, t) => {
    if (!acc[t.program_name]) acc[t.program_name] = [];
    acc[t.program_name].push(t);
    return acc;
  }, {});

  const hasAnyTemplates = templates.length > 0 || programTemplates.length > 0;

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title="Import from Template" zIndex={60}>
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
            {/* My Templates */}
            {templates.length > 0 && (
              <div>
                <p className="text-xs text-white/40 uppercase tracking-wider mb-2">My Templates</p>
                <div className="space-y-2">
                  {templates.map((t) => (
                    <div
                      key={t.id}
                      className="border border-secondary-muted rounded-lg p-3 hover:border-accent/30 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{t.template_name}</p>
                          <p className="text-xs text-white/40">
                            {t.training_type} &middot; {t.exercises.length} exercise{t.exercises.length !== 1 ? 's' : ''}
                          </p>
                        </div>
                        <button
                          onClick={() => handleApply(t.id, false)}
                          disabled={applying !== null}
                          className="px-3 py-1.5 rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
                        >
                          {applying === t.id ? 'Applying...' : 'Apply'}
                        </button>
                      </div>
                    </div>
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
                    <div
                      key={pt.id}
                      className="border border-secondary-muted rounded-lg p-3 hover:border-accent/30 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{pt.template_name}</p>
                          <p className="text-xs text-white/40">
                            {pt.training_type} &middot; {pt.exercises.length} exercise{pt.exercises.length !== 1 ? 's' : ''}
                          </p>
                        </div>
                        <button
                          onClick={() => handleApply(pt.id, true)}
                          disabled={applying !== null}
                          className="px-3 py-1.5 rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
                        >
                          {applying === pt.id ? 'Applying...' : 'Apply'}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
    </ResponsiveModal>
  );
}
