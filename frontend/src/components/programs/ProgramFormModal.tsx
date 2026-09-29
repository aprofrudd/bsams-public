'use client';

import { useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { programsApi } from '@/lib/api';
import type { ProgramPackage } from '@/lib/types';

interface ProgramFormModalProps {
  program: ProgramPackage | null; // null = create mode
  onClose: () => void;
  onSaved: () => void;
}

const CATEGORY_OPTIONS = ['General', 'Strength', 'Conditioning', 'Fight Camp'];

export function ProgramFormModal({ program, onClose, onSaved }: ProgramFormModalProps) {
  const [programName, setProgramName] = useState(program?.program_name || '');
  const [description, setDescription] = useState(program?.description || '');
  const [category, setCategory] = useState(program?.category || 'General');
  const [isPublished, setIsPublished] = useState(program?.is_published || false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!programName.trim()) {
      setError('Program name is required');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (program) {
        await programsApi.update(program.id, {
          program_name: programName.trim(),
          description: description.trim() || undefined,
          category,
          is_published: isPublished,
        });
      } else {
        await programsApi.create({
          program_name: programName.trim(),
          description: description.trim() || undefined,
          category,
          is_published: isPublished,
        });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save program');
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title={program ? 'Edit Program' : 'New Program'} zIndex={60}>
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-white/60 mb-1">Program Name</label>
          <input
            type="text"
            value={programName}
            onChange={e => setProgramName(e.target.value)}
            className="w-full px-3 py-2 min-h-[44px] rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent"
            placeholder="e.g. Train Like a Champion 1"
          />
        </div>

        <div>
          <label className="block text-sm text-white/60 mb-1">Description</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent resize-none"
            placeholder="What does this program include?"
          />
        </div>

        <div>
          <label className="block text-sm text-white/60 mb-1">Category</label>
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            className="w-full px-3 py-2 min-h-[44px] rounded bg-white/5 border border-secondary-muted text-white text-sm focus:outline-none focus:border-accent"
          >
            {CATEGORY_OPTIONS.map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isPublished}
            onChange={e => setIsPublished(e.target.checked)}
            className="w-4 h-4 rounded border-secondary-muted"
          />
          <span className="text-sm text-white/60">Published (visible to all users)</span>
        </label>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        <button
          onClick={handleSave}
          disabled={saving || !programName.trim()}
          className="w-full py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors disabled:opacity-50"
        >
          {saving ? 'Saving...' : (program ? 'Update Program' : 'Create Program')}
        </button>
      </div>
    </ResponsiveModal>
  );
}
