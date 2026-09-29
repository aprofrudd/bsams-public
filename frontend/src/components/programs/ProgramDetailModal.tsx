'use client';

import { useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { ProgramTemplateFormModal } from './ProgramTemplateFormModal';
import { programsApi } from '@/lib/api';
import type { ProgramPackageDetail, ProgramTemplate } from '@/lib/types';

interface ProgramDetailModalProps {
  program: ProgramPackageDetail;
  isAdmin: boolean;
  onClose: () => void;
  onInstall: () => void;
  onUninstall: () => void;
  onProgramUpdated: () => void;
}

export function ProgramDetailModal({ program, isAdmin, onClose, onInstall, onUninstall, onProgramUpdated }: ProgramDetailModalProps) {
  const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null);
  const [showTemplateForm, setShowTemplateForm] = useState(false);
  const [editTemplate, setEditTemplate] = useState<ProgramTemplate | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  async function handleDeleteTemplate(templateId: string) {
    if (!window.confirm('Delete this template?')) return;
    setDeleting(templateId);
    try {
      await programsApi.deleteTemplate(program.id, templateId);
      onProgramUpdated();
      onClose();
    } catch {
      // handled by parent error state
    } finally {
      setDeleting(null);
    }
  }

  return (
    <>
      <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="lg" title={program.program_name} zIndex={50}>
        <div className="space-y-4">
          {/* Meta */}
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-medium uppercase px-2 py-0.5 rounded-full bg-white/5 text-white/40">
              {program.category}
            </span>
            <span className="text-xs text-white/40">
              {program.templates.length} template{program.templates.length !== 1 ? 's' : ''}
            </span>
          </div>

          {program.description && (
            <p className="text-sm text-white/60">{program.description}</p>
          )}

          {/* Install/Uninstall */}
          <div>
            {program.is_installed ? (
              <button
                onClick={onUninstall}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
              >
                Installed — Click to Uninstall
              </button>
            ) : (
              <button
                onClick={onInstall}
                className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
              >
                Install Program
              </button>
            )}
          </div>

          {/* Templates */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-white/80">Templates</h3>
              {isAdmin && (
                <button
                  onClick={() => { setEditTemplate(null); setShowTemplateForm(true); }}
                  className="px-3 py-1.5 rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
                >
                  + Add Template
                </button>
              )}
            </div>

            {program.templates.length === 0 ? (
              <p className="text-white/40 text-sm text-center py-6">No templates yet.</p>
            ) : (
              <div className="space-y-2">
                {program.templates.map(t => (
                  <div key={t.id} className="border border-secondary-muted/50 rounded-lg">
                    <button
                      onClick={() => setExpandedTemplate(expandedTemplate === t.id ? null : t.id)}
                      className="w-full text-left p-3 flex items-center justify-between"
                    >
                      <div>
                        <p className="font-medium text-sm">{t.template_name}</p>
                        <p className="text-xs text-white/40">
                          {t.training_type} &middot; {t.exercises.length} exercise{t.exercises.length !== 1 ? 's' : ''}
                        </p>
                      </div>
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        className={`w-4 h-4 text-white/30 transition-transform ${expandedTemplate === t.id ? 'rotate-180' : ''}`}
                      >
                        <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 011.06 0L10 11.94l3.72-3.72a.75.75 0 111.06 1.06l-4.25 4.25a.75.75 0 01-1.06 0L5.22 9.28a.75.75 0 010-1.06z" clipRule="evenodd" />
                      </svg>
                    </button>

                    {expandedTemplate === t.id && (
                      <div className="px-3 pb-3 border-t border-secondary-muted/30">
                        {t.notes && <p className="text-xs text-white/50 mt-2 mb-2">{t.notes}</p>}
                        {t.exercises.length > 0 ? (
                          <div className="space-y-1 mt-2">
                            {t.exercises.map((ex, i) => (
                              <div key={i} className="text-xs text-white/60 flex items-center gap-2">
                                <span className="text-white/20 w-4 text-right">{i + 1}.</span>
                                <span>{ex.exercise_name}</span>
                                <span className="text-white/30">
                                  {ex.sets}x{ex.reps || '-'}
                                  {ex.weight_kg ? ` @ ${ex.weight_kg}kg` : ''}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-white/30 mt-2">No exercises defined.</p>
                        )}
                        {isAdmin && (
                          <div className="flex items-center gap-2 mt-3">
                            <button
                              onClick={() => { setEditTemplate(t); setShowTemplateForm(true); }}
                              className="px-3 py-1.5 rounded text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteTemplate(t.id)}
                              disabled={deleting === t.id}
                              className="px-3 py-1.5 rounded text-xs font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors disabled:opacity-50"
                            >
                              {deleting === t.id ? 'Deleting...' : 'Delete'}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </ResponsiveModal>

      {/* Template Form Modal */}
      {showTemplateForm && (
        <ProgramTemplateFormModal
          programId={program.id}
          template={editTemplate}
          onClose={() => { setShowTemplateForm(false); setEditTemplate(null); }}
          onSaved={() => { setShowTemplateForm(false); setEditTemplate(null); onProgramUpdated(); onClose(); }}
        />
      )}
    </>
  );
}
