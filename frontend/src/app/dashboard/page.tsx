'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useAthleteContext } from '@/lib/contexts/AthleteContext';
import { ReadinessIndicator } from '@/components/training/ReadinessIndicator';
import { QuickActions } from '@/components/dashboard/QuickActions';
import { TodaysSessions } from '@/components/dashboard/TodaysSessions';
import { WellnessMini } from '@/components/dashboard/WellnessMini';
import { TestResultsSummary } from '@/components/dashboard/TestResultsSummary';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { selectedAthlete, athleteError } = useAthleteContext();
  const [dataVersion, setDataVersion] = useState(0);
  const [exportError, setExportError] = useState<string | null>(null);
  const [showWelcome, setShowWelcome] = useState(false);

  useEffect(() => {
    try {
      if (!localStorage.getItem('bsams-welcome-dismissed')) {
        setShowWelcome(true);
      }
    } catch { /* ignore */ }
  }, []);

  const dismissWelcome = useCallback(() => {
    setShowWelcome(false);
    try { localStorage.setItem('bsams-welcome-dismissed', '1'); } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    } else if (!loading && user && user.role !== 'athlete') {
      router.replace('/training');
    }
  }, [loading, user, router]);

  if (loading || !user || user.role !== 'athlete') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!selectedAthlete) {
    if (athleteError) {
      return (
        <div className="flex items-center justify-center min-h-[60vh]">
          <div className="card max-w-md text-center">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-8 h-8 text-amber-400 mx-auto mb-3">
              <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
            </svg>
            <p className="text-white/80 text-sm">{athleteError}</p>
          </div>
        </div>
      );
    }
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const bumpVersion = () => setDataVersion((v) => v + 1);

  async function handleExport() {
    if (!selectedAthlete) return;
    setExportError(null);
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
      setExportError('Failed to export data. Please try again.');
    }
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <h2 className="section-title text-base sm:text-lg">My Dashboard</h2>

      {/* Welcome Banner */}
      {showWelcome && (
        <div className="card border border-accent/30 bg-accent/5 relative">
          <button
            onClick={dismissWelcome}
            className="absolute top-3 right-3 text-white/40 hover:text-white transition-colors"
            aria-label="Dismiss welcome"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-5 h-5">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
          <h3 className="font-heading text-sm uppercase tracking-wider text-accent mb-2">Welcome!</h3>
          <p className="text-white/70 text-sm mb-3">Here are some things to get you started:</p>
          <ul className="text-sm text-white/60 space-y-1.5">
            <li className="flex items-center gap-2">
              <span className="text-accent">1.</span>
              <span>Log today&apos;s <strong className="text-white/80">wellness</strong> using the quick action below</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-accent">2.</span>
              <span>Complete any <strong className="text-white/80">assigned sessions</strong> from your coach</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-accent">3.</span>
              <span>Log your own <strong className="text-white/80">training sessions</strong> with RPE and duration</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="text-accent">4.</span>
              <span>View your <strong className="text-white/80">test results</strong> in the Testing section</span>
            </li>
          </ul>
        </div>
      )}

      {/* Readiness */}
      <ReadinessIndicator athleteId={selectedAthlete.id} dataVersion={dataVersion} />

      {/* Today's Sessions */}
      <TodaysSessions
        athleteId={selectedAthlete.id}
        dataVersion={dataVersion}
      />

      {/* Quick Actions */}
      <QuickActions athleteId={selectedAthlete.id} onDataChanged={bumpVersion} />

      {/* Bento: Wellness + Test Results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WellnessMini athleteId={selectedAthlete.id} dataVersion={dataVersion} />
        <TestResultsSummary athleteId={selectedAthlete.id} />
      </div>

      {/* Data Export */}
      <div className="card">
        <h3 className="font-heading text-sm uppercase tracking-wider text-white/60 mb-3">My Data</h3>
        <button
          onClick={handleExport}
          className="btn-primary px-6 bg-transparent border border-accent text-accent hover:bg-accent/10 text-sm"
        >
          Export My Data
        </button>
        {exportError && (
          <p className="text-red-400 text-sm mt-2">{exportError}</p>
        )}
      </div>
    </div>
  );
}
