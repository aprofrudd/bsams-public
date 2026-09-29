'use client';

import { useState, useCallback } from 'react';
import { MetabolicProfiler } from './MetabolicProfiler';
import { MetabolicProfilesList } from './MetabolicProfilesList';

interface MetabolicProfilesTabProps {
  athleteId: string;
  athleteWeight: number | null;
  readOnly?: boolean;
}

export function MetabolicProfilesTab({ athleteId, athleteWeight, readOnly }: MetabolicProfilesTabProps) {
  const [showProfiler, setShowProfiler] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSaved = useCallback(() => {
    setRefreshKey(k => k + 1);
  }, []);

  return (
    <div className="space-y-4">
      {/* Header with New Profile button */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">
          Ferretti/di Prampero 3-sprint metabolic protocol
        </p>
        {!readOnly && (
          <button
            onClick={() => setShowProfiler(true)}
            className="btn-primary text-sm px-4 py-1.5"
          >
            + New Profile
          </button>
        )}
      </div>

      {/* Saved profiles list */}
      <MetabolicProfilesList
        athleteId={athleteId}
        refreshKey={refreshKey}
        readOnly={readOnly}
      />

      {/* Full-screen profiler overlay */}
      {showProfiler && (
        <MetabolicProfiler
          athleteId={athleteId}
          athleteWeight={athleteWeight}
          onClose={() => setShowProfiler(false)}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
