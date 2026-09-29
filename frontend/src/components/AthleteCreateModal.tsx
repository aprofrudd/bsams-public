'use client';

import { useState } from 'react';
import { athletesApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { Athlete } from '@/lib/types';

interface AthleteCreateModalProps {
  onClose: () => void;
  onCreated: (athlete: Athlete) => void;
}

export function AthleteCreateModal({ onClose, onCreated }: AthleteCreateModalProps) {
  const [name, setName] = useState('');
  const [gender, setGender] = useState<'male' | 'female'>('male');
  const [dob, setDob] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || trimmed.length > 100) {
      setError('Name must be 1-100 characters');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const created = await athletesApi.create({
        name: trimmed,
        gender,
        date_of_birth: dob || undefined,
      });
      onCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create athlete');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="sm" title="Add Athlete">
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm text-white/60 mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input w-full"
              required
              maxLength={100}
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Gender</label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value as 'male' | 'female')}
              className="select w-full"
            >
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Date of Birth</label>
            <input
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              className="input w-full"
            />
          </div>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" disabled={saving} className="btn-primary flex-1 disabled:opacity-50">
              {saving ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
