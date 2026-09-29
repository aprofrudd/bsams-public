'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { programmeFormsApi } from '@/lib/api';
import { ProgrammeFormModal } from './ProgrammeFormModal';
import { ProgrammeApplyModal } from './ProgrammeApplyModal';
import { ProgrammeFormPrintView } from './ProgrammeFormPrintView';
import type { ProgrammeForm } from '@/lib/types';

export function ProgrammeFormListView() {
  const [forms, setForms] = useState<ProgrammeForm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editingForm, setEditingForm] = useState<ProgrammeForm | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [applyingForm, setApplyingForm] = useState<ProgrammeForm | null>(null);
  const [printingForm, setPrintingForm] = useState<ProgrammeForm | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);

  const loadForms = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await programmeFormsApi.list();
      setForms(data);
    } catch {
      setError('Failed to load programme forms');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadForms();
  }, [loadForms]);

  async function handleDelete(formId: string) {
    if (!window.confirm('Delete this programme form? This cannot be undone.')) return;
    try {
      await programmeFormsApi.delete(formId);
      setForms((prev) => prev.filter((f) => f.id !== formId));
    } catch {
      setError('Failed to delete form');
    }
  }

  async function handleExportPdf() {
    if (!printRef.current || !printingForm) return;
    setIsExporting(true);
    try {
      const jsPDF = (await import('jspdf')).default;
      const html2canvas = (await import('html2canvas')).default;

      const container = printRef.current;
      const reportSections = container.querySelectorAll('.report-section');

      const pdf = new jsPDF('p', 'mm', 'a4');
      const contentWidth = 190;

      for (let i = 0; i < reportSections.length; i++) {
        const canvas = await html2canvas(reportSections[i] as HTMLElement, {
          scale: 2,
          useCORS: true,
          backgroundColor: '#ffffff',
        });
        const imgData = canvas.toDataURL('image/jpeg', 0.95);
        const imgHeight = (canvas.height * contentWidth) / canvas.width;

        if (i > 0) pdf.addPage();
        pdf.addImage(imgData, 'JPEG', 10, 10, contentWidth, imgHeight);
      }

      const date = new Date().toISOString().split('T')[0];
      const safeName = printingForm.form_name.replace(/[^a-zA-Z0-9]/g, '_');
      pdf.save(`${safeName}_Programme_${date}.pdf`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to export PDF';
      setError(msg);
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-white/60">Your programme forms</p>
        <button
          onClick={() => { setEditingForm(null); setShowCreateModal(true); }}
          className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors"
        >
          + New Form
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400 mb-4">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">&times;</button>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : forms.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-white/60 text-sm mb-2">No programme forms yet.</p>
          <p className="text-white/40 text-xs">
            Create a form to define structured training programmes with sections and apply them to your athletes.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {forms.map((form) => (
            <div
              key={form.id}
              className="border border-secondary-muted rounded-lg p-4 hover:border-accent/30 transition-colors"
            >
              <div className="mb-2">
                <p className="font-medium text-sm">{form.form_name}</p>
                {form.description && (
                  <p className="text-xs text-white/40 mt-0.5 line-clamp-2">{form.description}</p>
                )}
              </div>
              <div className="text-xs text-white/50 mb-3">
                {form.num_weeks} weeks &middot; {form.sessions_per_week} sessions/wk
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={() => setEditingForm(form)}
                  className="px-3 py-1.5 min-h-[36px] rounded text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
                >
                  Edit
                </button>
                <button
                  onClick={() => setApplyingForm(form)}
                  className="px-3 py-1.5 min-h-[36px] rounded text-xs font-medium bg-accent/10 text-accent hover:bg-accent/20 transition-colors"
                >
                  Apply
                </button>
                <button
                  onClick={() => setPrintingForm(form)}
                  className="px-3 py-1.5 min-h-[36px] rounded text-xs font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
                >
                  Print
                </button>
                <button
                  onClick={() => handleDelete(form.id)}
                  className="px-3 py-1.5 min-h-[36px] rounded text-xs font-medium bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {(showCreateModal || editingForm) && (
        <ProgrammeFormModal
          existingForm={editingForm}
          onClose={() => { setShowCreateModal(false); setEditingForm(null); }}
          onSaved={() => { setShowCreateModal(false); setEditingForm(null); loadForms(); }}
        />
      )}

      {applyingForm && (
        <ProgrammeApplyModal
          form={applyingForm}
          onClose={() => setApplyingForm(null)}
          onApplied={() => { setApplyingForm(null); }}
        />
      )}

      {printingForm && createPortal(
        <div className="fixed inset-0 z-[100] bg-white overflow-y-auto">
          {/* Toolbar */}
          <div className="sticky top-0 z-10 bg-[#090A3D] flex items-center justify-between px-4 py-3 shadow-lg">
            <button
              onClick={() => setPrintingForm(null)}
              className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-white/10 text-white hover:bg-white/20 transition-colors"
            >
              Close
            </button>
            <button
              onClick={handleExportPdf}
              disabled={isExporting}
              className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
            >
              {isExporting ? 'Exporting...' : 'Export PDF'}
            </button>
          </div>
          {/* Print content */}
          <div className="flex justify-center py-8">
            <ProgrammeFormPrintView ref={printRef} form={printingForm} />
          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
