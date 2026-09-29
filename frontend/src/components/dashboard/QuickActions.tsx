'use client';

import { useState } from 'react';
import { SessionLogForm } from '@/components/training/SessionLogForm';
import { WellnessForm } from '@/components/training/WellnessForm';

interface QuickActionsProps {
  athleteId: string;
  onDataChanged: () => void;
}

export function QuickActions({ athleteId, onDataChanged }: QuickActionsProps) {
  const [showSessionForm, setShowSessionForm] = useState(false);
  const [showWellnessForm, setShowWellnessForm] = useState(false);

  return (
    <>
      <div className="flex gap-3">
        <button
          onClick={() => setShowSessionForm(true)}
          className="flex-1 px-4 py-3 min-h-[44px] rounded-lg text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
        >
          + Add Session
        </button>
        <button
          onClick={() => setShowWellnessForm(true)}
          className="flex-1 px-4 py-3 min-h-[44px] rounded-lg text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
        >
          + Log Wellness
        </button>
      </div>

      {showSessionForm && (
        <SessionLogForm
          athleteId={athleteId}
          mode="log"
          isAthlete
          onClose={() => setShowSessionForm(false)}
          onSaved={() => {
            setShowSessionForm(false);
            onDataChanged();
          }}
        />
      )}

      {showWellnessForm && (
        <WellnessForm
          athleteId={athleteId}
          onClose={() => setShowWellnessForm(false)}
          onSaved={() => {
            setShowWellnessForm(false);
            onDataChanged();
          }}
        />
      )}
    </>
  );
}
