'use client';

import { useState } from 'react';
import { airBikeApi } from '@/lib/api';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { AirBikeTest, AirBikeSprintCreate, AirBikeSplitScheme } from '@/lib/types';
import { sprintMidPower, midSplitSeconds } from '@/lib/airBikeSplits';

interface AirBikeTestFormProps {
  athleteId: string;
  existingTest?: AirBikeTest | null;
  onClose: () => void;
  onSaved: () => void;
}

export function AirBikeTestForm({
  athleteId,
  existingTest,
  onClose,
  onSaved,
}: AirBikeTestFormProps) {
  const isEdit = !!existingTest;

  const sprint1Existing = existingTest?.sprints.find((s) => s.sprint_number === 1);
  const sprint2Existing = existingTest?.sprints.find((s) => s.sprint_number === 2);

  const [testDate, setTestDate] = useState(
    existingTest ? existingTest.test_date.slice(0, 10) : ''
  );
  const [bodyMass, setBodyMass] = useState(
    existingTest ? String(existingTest.body_mass_kg) : ''
  );
  const [notes, setNotes] = useState(existingTest?.notes ?? '');
  // Which mid split this test uses. Defaults to the original 7/14/27 protocol.
  const [splitScheme, setSplitScheme] = useState<AirBikeSplitScheme>(
    existingTest?.split_scheme ?? '7_14_27'
  );
  const midSeconds = midSplitSeconds(splitScheme);

  // Sprint 1 (required)
  const [s1_7s, setS1_7s] = useState(sprint1Existing ? String(sprint1Existing.power_7s) : '');
  const [s1_mid, setS1_mid] = useState(
    sprint1Existing ? String(sprintMidPower(sprint1Existing) ?? '') : ''
  );
  const [s1_27s, setS1_27s] = useState(sprint1Existing ? String(sprint1Existing.power_27s) : '');
  const [s1_lactate, setS1_lactate] = useState(
    sprint1Existing?.blood_lactate_mmol != null ? String(sprint1Existing.blood_lactate_mmol) : ''
  );

  // Sprint 2 (optional, all-or-nothing for power fields)
  const [s2_7s, setS2_7s] = useState(sprint2Existing ? String(sprint2Existing.power_7s) : '');
  const [s2_mid, setS2_mid] = useState(
    sprint2Existing ? String(sprintMidPower(sprint2Existing) ?? '') : ''
  );
  const [s2_27s, setS2_27s] = useState(sprint2Existing ? String(sprint2Existing.power_27s) : '');
  const [s2_lactate, setS2_lactate] = useState(
    sprint2Existing?.blood_lactate_mmol != null ? String(sprint2Existing.blood_lactate_mmol) : ''
  );

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function validate(): string | null {
    if (!isEdit && !testDate) return 'Test date is required';
    if (!bodyMass) return 'Body mass is required';
    const mass = Number(bodyMass);
    if (isNaN(mass) || mass <= 0 || mass > 300) return 'Body mass must be 0–300 kg';

    // Sprint 1 is required
    if (!s1_7s || !s1_mid || !s1_27s) return 'Sprint 1: all 3 power values are required';
    for (const [label, val] of [['7s', s1_7s], [`${midSeconds}s`, s1_mid], ['27s', s1_27s]] as const) {
      const n = Number(val);
      if (isNaN(n) || n <= 0 || n > 5000) return `Sprint 1 ${label} Power must be 0–5000 W`;
    }
    if (s1_lactate) {
      const n = Number(s1_lactate);
      if (isNaN(n) || n < 0 || n > 30) return 'Sprint 1 Blood Lactate must be 0–30 mmol/L';
    }

    // Sprint 2 is all-or-nothing for the 3 power fields
    const s2HasAny = s2_7s || s2_mid || s2_27s;
    const s2HasAll = s2_7s && s2_mid && s2_27s;
    if (s2HasAny && !s2HasAll) return 'Sprint 2: provide all 3 power values or leave all empty';
    if (s2HasAll) {
      for (const [label, val] of [['7s', s2_7s], [`${midSeconds}s`, s2_mid], ['27s', s2_27s]] as const) {
        const n = Number(val);
        if (isNaN(n) || n <= 0 || n > 5000) return `Sprint 2 ${label} Power must be 0–5000 W`;
      }
    }
    if (s2_lactate) {
      const n = Number(s2_lactate);
      if (isNaN(n) || n < 0 || n > 30) return 'Sprint 2 Blood Lactate must be 0–30 mmol/L';
    }

    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Send exactly one mid split — it is what tells the API which protocol was run.
      const midSplit = (value: string): Pick<AirBikeSprintCreate, 'power_14s' | 'power_17s'> =>
        splitScheme === '7_17_27' ? { power_17s: Number(value) } : { power_14s: Number(value) };

      const sprints: AirBikeSprintCreate[] = [
        {
          sprint_number: 1,
          power_7s: Number(s1_7s),
          ...midSplit(s1_mid),
          power_27s: Number(s1_27s),
          ...(s1_lactate ? { blood_lactate_mmol: Number(s1_lactate) } : {}),
        },
      ];

      if (s2_7s && s2_mid && s2_27s) {
        sprints.push({
          sprint_number: 2,
          power_7s: Number(s2_7s),
          ...midSplit(s2_mid),
          power_27s: Number(s2_27s),
          ...(s2_lactate ? { blood_lactate_mmol: Number(s2_lactate) } : {}),
        });
      }

      if (isEdit && existingTest) {
        await airBikeApi.updateTest(existingTest.id, {
          ...(testDate ? { test_date: testDate } : {}),
          body_mass_kg: Number(bodyMass),
          notes: notes || undefined,
          sprints,
        });
      } else {
        await airBikeApi.createTest(athleteId, {
          test_date: testDate,
          body_mass_kg: Number(bodyMass),
          notes: notes || undefined,
          sprints,
        });
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save test');
    } finally {
      setSaving(false);
    }
  }

  return (
    <ResponsiveModal isOpen={true} onClose={onClose} maxWidth="md" title={isEdit ? 'Edit Air Bike Test' : 'New Air Bike Test'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Date + Body Mass row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-white/60 mb-1">Date</label>
              <input
                type="date"
                value={testDate}
                onChange={(e) => setTestDate(e.target.value)}
                className="input w-full"
                required={!isEdit}
              />
            </div>
            <div>
              <label className="block text-sm text-white/60 mb-1">Body Mass (kg)</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="300"
                value={bodyMass}
                onChange={(e) => setBodyMass(e.target.value)}
                className="input w-full"
                placeholder="kg"
                required
              />
            </div>
          </div>

          {/* Split protocol */}
          <div>
            <label className="text-xs text-white/40">Split Protocol</label>
            <div className="flex gap-2 mt-1">
              {(['7_14_27', '7_17_27'] as const).map((scheme) => (
                <button
                  key={scheme}
                  type="button"
                  onClick={() => setSplitScheme(scheme)}
                  className={`flex-1 min-h-[44px] px-3 rounded-lg text-sm font-medium transition-all active:scale-[0.97] ${
                    splitScheme === scheme
                      ? 'bg-accent text-[#090A3D]'
                      : 'bg-secondary-muted/20 text-white/60 hover:bg-secondary-muted/40'
                  }`}
                >
                  {scheme === '7_14_27' ? '7 / 14 / 27 s' : '7 / 17 / 27 s'}
                </button>
              ))}
            </div>
          </div>

          {/* Sprint 1 */}
          <div className="border border-secondary-muted/50 rounded-lg p-3 space-y-2">
            <div className="text-sm font-heading uppercase tracking-wider text-accent">Sprint 1</div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-white/40">7s Power (W)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="5000"
                  value={s1_7s}
                  onChange={(e) => setS1_7s(e.target.value)}
                  className="input w-full"
                  placeholder="W"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-white/40">{midSeconds}s Power (W)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="5000"
                  value={s1_mid}
                  onChange={(e) => setS1_mid(e.target.value)}
                  className="input w-full"
                  placeholder="W"
                  required
                />
              </div>
              <div>
                <label className="text-xs text-white/40">27s Power (W)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="5000"
                  value={s1_27s}
                  onChange={(e) => setS1_27s(e.target.value)}
                  className="input w-full"
                  placeholder="W"
                  required
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-white/40">Blood Lactate (mmol/L)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="30"
                value={s1_lactate}
                onChange={(e) => setS1_lactate(e.target.value)}
                className="input w-full max-w-[200px]"
                placeholder="Optional"
              />
            </div>
          </div>

          {/* Sprint 2 */}
          <div className="border border-secondary-muted/50 rounded-lg p-3 space-y-2">
            <div className="text-sm font-heading uppercase tracking-wider text-white/40">
              Sprint 2 <span className="text-xs normal-case tracking-normal">(optional)</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-xs text-white/40">7s Power (W)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="5000"
                  value={s2_7s}
                  onChange={(e) => setS2_7s(e.target.value)}
                  className="input w-full"
                  placeholder="W"
                />
              </div>
              <div>
                <label className="text-xs text-white/40">{midSeconds}s Power (W)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="5000"
                  value={s2_mid}
                  onChange={(e) => setS2_mid(e.target.value)}
                  className="input w-full"
                  placeholder="W"
                />
              </div>
              <div>
                <label className="text-xs text-white/40">27s Power (W)</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  max="5000"
                  value={s2_27s}
                  onChange={(e) => setS2_27s(e.target.value)}
                  className="input w-full"
                  placeholder="W"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-white/40">Blood Lactate (mmol/L)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="30"
                value={s2_lactate}
                onChange={(e) => setS2_lactate(e.target.value)}
                className="input w-full max-w-[200px]"
                placeholder="Optional"
              />
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm text-white/60 mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="input w-full"
              rows={2}
              placeholder="Optional notes..."
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
              {saving ? 'Saving...' : isEdit ? 'Update' : 'Create Test'}
            </button>
          </div>
        </form>
    </ResponsiveModal>
  );
}
