'use client';

import { useState } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { athletesApi } from '@/lib/api';
import type { Athlete } from '@/lib/types';

interface OnboardingWizardProps {
  currentStep: number;
  athleteCreated: boolean;
  onNext: () => void;
  onPrev: () => void;
  onDismiss: () => void;
  onAthleteCreated: (athlete: Athlete) => void;
  onComplete: () => void;
}

/* ---------- Step indicator ---------- */

function StepIndicator({ currentStep }: { currentStep: number }) {
  const steps = ['Welcome', 'Add Athlete', 'Tour'];
  return (
    <div className="flex items-center justify-center gap-0 mb-6">
      {steps.map((label, i) => {
        const isCompleted = i < currentStep;
        const isActive = i === currentStep;
        return (
          <div key={label} className="flex items-center">
            {i > 0 && (
              <div className={`w-8 sm:w-12 h-0.5 ${i <= currentStep ? 'bg-accent' : 'bg-secondary-muted'}`} />
            )}
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                  isCompleted
                    ? 'bg-accent text-primary'
                    : isActive
                      ? 'bg-accent text-primary'
                      : 'border border-secondary-muted text-white/40'
                }`}
              >
                {isCompleted ? (
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <span className={`text-[10px] uppercase tracking-wider font-heading ${isActive || isCompleted ? 'text-accent' : 'text-white/30'}`}>
                {label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ---------- Step 0: Welcome ---------- */

const FEATURE_CARDS = [
  {
    title: 'Testing',
    description: 'Record and analyse jump, mobility, isometric, and air bike assessments.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
        <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H4.598a.75.75 0 00-.75.75v3.634a.75.75 0 001.5 0v-2.033l.312.311a7 7 0 0011.712-3.138.75.75 0 00-1.449-.389zm1.079-7.058a.75.75 0 00-1.5 0v2.033l-.312-.312A7 7 0 002.867 9.225a.75.75 0 001.449.388A5.5 5.5 0 0113.52 7.147l.312.311h-2.433a.75.75 0 000 1.5h3.634a.75.75 0 00.75-.75V4.574z" clipRule="evenodd" />
      </svg>
    ),
  },
  {
    title: 'Training',
    description: 'Log sessions, track wellness, and monitor training load with ACWR analysis.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
        <path d="M15.98 1.804a1 1 0 00-1.96 0l-.24 1.192a1 1 0 01-.784.785l-1.192.238a1 1 0 000 1.962l1.192.238a1 1 0 01.785.785l.238 1.192a1 1 0 001.962 0l.238-1.192a1 1 0 01.785-.785l1.192-.238a1 1 0 000-1.962l-1.192-.238a1 1 0 01-.785-.785l-.238-1.192zM6.949 5.684a1 1 0 00-1.898 0l-.683 2.051a1 1 0 01-.633.633l-2.051.683a1 1 0 000 1.898l2.051.684a1 1 0 01.633.632l.683 2.051a1 1 0 001.898 0l.683-2.051a1 1 0 01.633-.633l2.051-.683a1 1 0 000-1.898l-2.051-.683a1 1 0 01-.633-.633L6.95 5.684zM13.949 13.684a1 1 0 00-1.898 0l-.184.551a1 1 0 01-.632.633l-.551.183a1 1 0 000 1.898l.551.183a1 1 0 01.633.633l.183.551a1 1 0 001.898 0l.184-.551a1 1 0 01.632-.633l.551-.183a1 1 0 000-1.898l-.551-.184a1 1 0 01-.633-.632l-.183-.551z" />
      </svg>
    ),
  },
  {
    title: 'Library',
    description: 'Build your exercise database and create reusable session templates.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
        <path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06V4.435a.75.75 0 00-.545-.72A8.964 8.964 0 0015 3.5a8.964 8.964 0 00-4.25 1.065v12.255zM9.25 4.565A8.964 8.964 0 005 3.5a8.964 8.964 0 00-2.455.215.75.75 0 00-.545.72v10.625a.75.75 0 00.955.72A7.462 7.462 0 015 15.5c1.579 0 3.058.49 4.25 1.32V4.565z" />
      </svg>
    ),
  },
  {
    title: 'Upload',
    description: 'Import athlete data in bulk via CSV files.',
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
        <path d="M9.25 13.25a.75.75 0 001.5 0V4.636l2.955 3.129a.75.75 0 001.09-1.03l-4.25-4.5a.75.75 0 00-1.09 0l-4.25 4.5a.75.75 0 101.09 1.03L9.25 4.636v8.614z" />
        <path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
      </svg>
    ),
  },
];

function WelcomeStep() {
  return (
    <div>
      <h2 className="section-title text-base text-center">Welcome to BSAMS</h2>
      <p className="text-white/60 text-sm text-center mt-2 mb-6">
        Your all-in-one platform for high-performance athlete management.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {FEATURE_CARDS.map((card) => (
          <div key={card.title} className="bg-secondary-muted/20 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-accent">{card.icon}</span>
              <h3 className="font-heading font-semibold uppercase tracking-wider text-accent text-sm">{card.title}</h3>
            </div>
            <p className="text-white/60 text-xs leading-relaxed">{card.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Step 1: Create Athlete ---------- */

function CreateAthleteStep({
  athleteCreated,
  onAthleteCreated,
  onSkip,
}: {
  athleteCreated: boolean;
  onAthleteCreated: (athlete: Athlete) => void;
  onSkip: () => void;
}) {
  const [name, setName] = useState('');
  const [gender, setGender] = useState<'male' | 'female'>('male');
  const [dob, setDob] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState(false);

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
      setJustCreated(true);
      onAthleteCreated(created);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create athlete');
    } finally {
      setSaving(false);
    }
  }

  if (athleteCreated || justCreated) {
    return (
      <div className="text-center py-8">
        <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center mx-auto mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-6 h-6 text-accent">
            <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
          </svg>
        </div>
        <h3 className="font-heading font-semibold uppercase tracking-wider text-accent text-sm mb-1">Athlete Created</h3>
        <p className="text-white/60 text-sm">You can add more athletes later from the header dropdown.</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="section-title text-base text-center">Create Your First Athlete</h2>
      <p className="text-white/60 text-sm text-center mt-2 mb-6">
        Add an athlete to start recording performance data.
      </p>
      <form onSubmit={handleSubmit} className="space-y-3 max-w-sm mx-auto">
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
        <button type="submit" disabled={saving} className="btn-primary w-full disabled:opacity-50">
          {saving ? 'Creating...' : 'Create Athlete'}
        </button>
      </form>
      <p className="text-center mt-4">
        <button onClick={onSkip} className="text-white/40 hover:text-white/60 text-sm underline underline-offset-2 transition-colors">
          I&apos;ll do this later
        </button>
      </p>
    </div>
  );
}

/* ---------- Step 2: Feature Tour ---------- */

const TOUR_ITEMS = [
  { title: 'Testing', description: 'Record and analyse jump, mobility, isometric, and air bike assessments. View Z-scores and radar plots.' },
  { title: 'Training', description: 'Log sessions, track wellness, monitor training load with ACWR analysis, and assign sessions to athletes.' },
  { title: 'Reports', description: 'Generate comprehensive athlete test reports and export as PDF.' },
  { title: 'Library', description: 'Build your exercise database and create reusable session templates.' },
  { title: 'Upload', description: 'Import athlete data in bulk via CSV files.' },
];

function FeatureTourStep() {
  return (
    <div>
      <h2 className="section-title text-base text-center">You&apos;re All Set</h2>
      <p className="text-white/60 text-sm text-center mt-2 mb-6">
        Here&apos;s a quick overview of what you can do:
      </p>
      <div className="space-y-3">
        {TOUR_ITEMS.map((item) => (
          <div key={item.title} className="bg-secondary-muted/20 rounded-lg p-4">
            <h3 className="font-heading font-semibold uppercase tracking-wider text-accent text-sm mb-1">{item.title}</h3>
            <p className="text-white/60 text-xs leading-relaxed">{item.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- Main Wizard ---------- */

export function OnboardingWizard({
  currentStep,
  athleteCreated,
  onNext,
  onPrev,
  onDismiss,
  onAthleteCreated,
  onComplete,
}: OnboardingWizardProps) {
  return (
    <ResponsiveModal isOpen={true} onClose={onDismiss} maxWidth="lg" zIndex={60}>
      <StepIndicator currentStep={currentStep} />

      {currentStep === 0 && <WelcomeStep />}
      {currentStep === 1 && (
        <CreateAthleteStep
          athleteCreated={athleteCreated}
          onAthleteCreated={onAthleteCreated}
          onSkip={onNext}
        />
      )}
      {currentStep === 2 && <FeatureTourStep />}

      {/* Navigation buttons */}
      <div className="flex justify-between mt-6 pt-4 border-t border-secondary-muted/30">
        {currentStep === 0 ? (
          <>
            <button onClick={onDismiss} className="btn-secondary text-sm min-h-[44px] px-4">Skip</button>
            <button onClick={onNext} className="btn-primary text-sm min-h-[44px] px-6">Get Started</button>
          </>
        ) : currentStep === 1 ? (
          <>
            <button onClick={onPrev} className="btn-secondary text-sm min-h-[44px] px-4">Back</button>
            <button onClick={onNext} className="btn-primary text-sm min-h-[44px] px-6">Next</button>
          </>
        ) : (
          <>
            <button onClick={onPrev} className="btn-secondary text-sm min-h-[44px] px-4">Back</button>
            <button onClick={onComplete} className="btn-primary text-sm min-h-[44px] px-6">Finish Setup</button>
          </>
        )}
      </div>
    </ResponsiveModal>
  );
}
