'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useAthleteContext } from '@/lib/contexts/AthleteContext';
import { useIsReadOnly } from '@/lib/hooks/useIsReadOnly';
import { athletesApi, eventsApi } from '@/lib/api';
import InviteSection from '@/components/InviteSection';
import NoAthleteSelected from '@/components/NoAthleteSelected';
import { ReadinessIndicator } from '@/components/training/ReadinessIndicator';
import { AthleteMaxesPanel } from '@/components/blocks/AthleteMaxesPanel';

export default function AthleteInfoPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { selectedAthlete, setSelectedAthlete } = useAthleteContext();
  const readOnly = useIsReadOnly();

  const [firstName, setFirstName] = useState('');
  const [surname, setSurname] = useState('');
  const [gender, setGender] = useState<'male' | 'female'>('male');
  const [dob, setDob] = useState('');
  const [bodyMass, setBodyMass] = useState('');
  const [stature, setStature] = useState('');
  const [status, setStatus] = useState('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [eventCount, setEventCount] = useState<number | null>(null);
  const [lastTestDate, setLastTestDate] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (selectedAthlete) {
      // Auto-populate first_name/surname from name if null
      let fn = selectedAthlete.first_name || '';
      let sn = selectedAthlete.surname || '';
      if (!fn && selectedAthlete.name) {
        const lastSpace = selectedAthlete.name.lastIndexOf(' ');
        if (lastSpace > 0) {
          fn = selectedAthlete.name.substring(0, lastSpace);
          sn = selectedAthlete.name.substring(lastSpace + 1);
        } else {
          fn = selectedAthlete.name;
        }
      }
      setFirstName(fn);
      setSurname(sn);
      setGender(selectedAthlete.gender);
      setDob(selectedAthlete.date_of_birth?.slice(0, 10) ?? '');
      setBodyMass(selectedAthlete.body_mass_kg?.toString() ?? '');
      setStature(selectedAthlete.stature_cm?.toString() ?? '');
      setStatus(selectedAthlete.status ?? '');
      setNotes(selectedAthlete.notes ?? '');
      setError(null);
      setSuccess(false);
    }
  }, [selectedAthlete]);

  // Fetch quick stats (event count + last test date)
  useEffect(() => {
    if (!selectedAthlete) {
      setEventCount(null);
      setLastTestDate(null);
      return;
    }
    eventsApi.listForAthlete(selectedAthlete.id).then(events => {
      setEventCount(events.length);
      if (events.length > 0) {
        const sorted = [...events].sort((a, b) => b.event_date.localeCompare(a.event_date));
        setLastTestDate(sorted[0].event_date);
      } else {
        setLastTestDate(null);
      }
    }).catch(() => {
      setEventCount(null);
      setLastTestDate(null);
    });
  }, [selectedAthlete]);

  async function handleExport() {
    if (!selectedAthlete) return;
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/export/athlete/${selectedAthlete.id}`,
        { credentials: 'include' }
      );
      if (!response.ok) throw new Error('Export failed');
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `athlete_${selectedAthlete.id}_export.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('Failed to export data');
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedAthlete) return;

    const trimmedFirst = firstName.trim();
    if (!trimmedFirst) {
      setError('First name is required');
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      // Build full form state, then send only changed fields
      const formValues: Record<string, any> = {
        first_name: trimmedFirst,
        surname: surname.trim() || null,
        gender,
        date_of_birth: dob || null,
        body_mass_kg: bodyMass ? parseFloat(bodyMass) : null,
        stature_cm: stature ? parseFloat(stature) : null,
        status: status || null,
        notes: notes.trim() || null,
      };

      // Compare with existing athlete to only send changed fields
      const existing: Record<string, any> = {
        first_name: selectedAthlete.first_name ?? null,
        surname: selectedAthlete.surname ?? null,
        gender: selectedAthlete.gender,
        date_of_birth: selectedAthlete.date_of_birth?.slice(0, 10) ?? null,
        body_mass_kg: selectedAthlete.body_mass_kg ?? null,
        stature_cm: selectedAthlete.stature_cm ?? null,
        status: selectedAthlete.status ?? null,
        notes: selectedAthlete.notes ?? null,
      };

      const updateData: Record<string, any> = {};
      for (const key of Object.keys(formValues)) {
        const formVal = formValues[key];
        const existVal = existing[key];
        // Compare as strings to handle type mismatches (number vs string)
        const formStr = formVal === null ? null : String(formVal);
        const existStr = existVal === null ? null : String(existVal);
        if (formStr !== existStr) {
          updateData[key] = formVal;
        }
      }

      // Always include first_name so the name sync trigger fires
      if (!updateData.first_name) {
        updateData.first_name = trimmedFirst;
      }

      const updated = await athletesApi.update(selectedAthlete.id, updateData);
      setSelectedAthlete(updated);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  }

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!selectedAthlete) {
    return (
      <div className="space-y-4 md:space-y-6">
        <h2 className="section-title text-base sm:text-lg">{readOnly ? 'My Profile' : 'Athlete Information'}</h2>
        <NoAthleteSelected message={readOnly ? 'Loading your profile...' : 'Select an athlete to view their profile'} />
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <h2 className="section-title text-base sm:text-lg">{readOnly ? 'My Profile' : 'Athlete Information'}</h2>

      {/* Quick Stats */}
      <div className="flex items-center gap-4 flex-wrap">
        <ReadinessIndicator athleteId={selectedAthlete.id} />
        <div className="flex items-center gap-3 text-xs text-white/60">
          {lastTestDate && (
            <>
              <span>
                Last test: {new Date(lastTestDate + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
              </span>
              <div className="w-px h-3 bg-secondary-muted/50" />
            </>
          )}
          {eventCount !== null && (
            <span>Tests: {eventCount}</span>
          )}
        </div>
      </div>

      <form onSubmit={handleSave} className="card max-w-2xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-white/60 mb-1">First Name *</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="input w-full"
              required
              maxLength={50}
              disabled={readOnly}
            />
          </div>
          <div>
            <label className="block text-sm text-white/60 mb-1">Surname</label>
            <input
              type="text"
              value={surname}
              onChange={(e) => setSurname(e.target.value)}
              className="input w-full"
              maxLength={50}
              disabled={readOnly}
            />
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Gender</label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value as 'male' | 'female')}
              className="select w-full"
              disabled={readOnly}
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
              disabled={readOnly}
            />
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Body Mass (kg)</label>
            <input
              type="number"
              value={bodyMass}
              onChange={(e) => setBodyMass(e.target.value)}
              className="input w-full"
              min="0.1"
              max="500"
              step="0.1"
              disabled={readOnly}
            />
          </div>
          <div>
            <label className="block text-sm text-white/60 mb-1">Stature (cm)</label>
            <input
              type="number"
              value={stature}
              onChange={(e) => setStature(e.target.value)}
              className="input w-full"
              min="0.1"
              max="300"
              step="0.1"
              disabled={readOnly}
            />
          </div>

          <div>
            <label className="block text-sm text-white/60 mb-1">Status</label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="select w-full"
              disabled={readOnly}
            >
              <option value="">Not set</option>
              <option value="amateur">Amateur</option>
              <option value="professional">Professional</option>
            </select>
          </div>
        </div>

        <div className="mt-4">
          <label className="block text-sm text-white/60 mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="input w-full h-24 min-h-[88px] resize-none"
            placeholder="Additional notes about this athlete..."
            disabled={readOnly}
          />
        </div>

        {readOnly && (
          <p className="text-white/40 text-sm mt-3 italic">
            Your profile is managed by your coach. Contact them to request changes.
          </p>
        )}

        {error && <p className="text-red-400 text-sm mt-3">{error}</p>}
        {success && <p className="text-green-400 text-sm mt-3">Profile saved successfully</p>}

        {!readOnly && (
          <div className="mt-4 flex gap-3">
            <button
              type="submit"
              disabled={saving}
              className="btn-primary px-6 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Profile'}
            </button>
            <button
              type="button"
              onClick={handleExport}
              className="btn-primary px-6 bg-transparent border border-accent text-accent hover:bg-accent/10"
            >
              Export Data
            </button>
          </div>
        )}
      </form>

      {/* Export Data — available to all users for this athlete */}
      {readOnly && selectedAthlete && (
        <div className="flex gap-3">
          <button
            type="button"
            onClick={handleExport}
            className="btn-primary px-6 bg-transparent border border-accent text-accent hover:bg-accent/10"
          >
            Export My Data
          </button>
        </div>
      )}

      {/* 1RM Maxes — coaches/admins only */}
      {!readOnly && selectedAthlete && (
        <AthleteMaxesPanel
          athleteId={selectedAthlete.id}
          athleteName={`${selectedAthlete.first_name} ${selectedAthlete.surname ?? ''}`.trim()}
        />
      )}

      {/* Invite Section — coaches/admins only */}
      {!readOnly && selectedAthlete && (
        <InviteSection athlete={selectedAthlete} />
      )}
    </div>
  );
}
