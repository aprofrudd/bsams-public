'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { useAthleteContext } from '@/lib/contexts/AthleteContext';
import { DataSharingConsent } from '@/components/DataSharingConsent';
import { SessionTable } from '@/components/training/SessionTable';
import { SessionCalendar } from '@/components/training/SessionCalendar';
import { SessionLogForm } from '@/components/training/SessionLogForm';
import { WellnessChart } from '@/components/training/WellnessChart';
import { LoadChart } from '@/components/training/LoadChart';
import { ReadinessIndicator } from '@/components/training/ReadinessIndicator';
import { BatchAssignModal } from '@/components/training/BatchAssignModal';
import { TemplateSessionModal } from '@/components/training/TemplateSessionModal';
import NoAthleteSelected from '@/components/NoAthleteSelected';
import { trainingApi } from '@/lib/api';
import type { TrainingSession } from '@/lib/types';

function useLocalStorage(key: string, defaultValue: boolean): [boolean, (v: boolean) => void] {
  const [value, setValue] = useState(defaultValue);
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored !== null) setValue(JSON.parse(stored));
    } catch { /* ignore */ }
  }, [key]);
  function set(v: boolean) {
    setValue(v);
    try { localStorage.setItem(key, JSON.stringify(v)); } catch { /* ignore */ }
  }
  return [value, set];
}

export default function TrainingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const { selectedAthlete } = useAthleteContext();
  const isAthlete = user?.role === 'athlete';
  const isCoachOrAdmin = user?.role === 'coach' || user?.role === 'admin';
  const [dataVersion, setDataVersion] = useState(0);
  const [showSessionForm, setShowSessionForm] = useState(false);
  const [sessionFormMode, setSessionFormMode] = useState<'log' | 'assign'>('log');
  const [showTrainingLoad, setShowTrainingLoad] = useLocalStorage('bsams-training-load-visible', false);
  const [showWellness, setShowWellness] = useLocalStorage('bsams-training-wellness-visible', isAthlete);
  const [showBatchAssign, setShowBatchAssign] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);

  // View toggle: 'list' or 'calendar'
  const [viewMode, setViewMode] = useState<'list' | 'calendar'>('calendar');
  useEffect(() => {
    try {
      const stored = localStorage.getItem('bsams-training-view');
      if (stored === 'list' || stored === 'calendar') setViewMode(stored);
    } catch { /* ignore */ }
  }, []);
  function toggleView(mode: 'list' | 'calendar') {
    setViewMode(mode);
    try { localStorage.setItem('bsams-training-view', mode); } catch { /* ignore */ }
  }

  // Calendar needs sessions loaded at page level
  const [calendarSessions, setCalendarSessions] = useState<TrainingSession[]>([]);
  const [calendarExpandedId, setCalendarExpandedId] = useState<string | null>(null);
  const [calendarCompleteSession, setCalendarCompleteSession] = useState<TrainingSession | null>(null);

  const loadCalendarSessions = useCallback(async () => {
    if (!selectedAthlete) return;
    try {
      const data = await trainingApi.listSessions(selectedAthlete.id);
      setCalendarSessions(data);
    } catch { /* ignore */ }
  }, [selectedAthlete]);

  useEffect(() => {
    if (viewMode === 'calendar' && selectedAthlete) {
      loadCalendarSessions();
    }
  }, [viewMode, selectedAthlete, dataVersion, loadCalendarSessions]);

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-2 md:space-y-3">
      {/* Page Header */}
      <div>
        {/* Row 1: Title + DataSharingConsent + desktop action buttons */}
        <div className="flex items-center justify-between mb-2 sm:mb-0">
          <div className="flex items-center gap-2">
            <h2 className="section-title text-base sm:text-lg">{isAthlete ? 'My Training' : 'Training'}</h2>
            {selectedAthlete && (
              <>
                <button
                  onClick={() => toggleView('calendar')}
                  className={`px-2 py-1 min-h-[32px] rounded text-xs font-medium transition-colors ${
                    viewMode === 'calendar' ? 'bg-accent text-[#090A3D]' : 'bg-secondary-muted/30 text-white/60 hover:text-white'
                  }`}
                  title="Calendar view"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M5.75 2a.75.75 0 01.75.75V4h7V2.75a.75.75 0 011.5 0V4h.25A2.75 2.75 0 0118 6.75v8.5A2.75 2.75 0 0115.25 18H4.75A2.75 2.75 0 012 15.25v-8.5A2.75 2.75 0 014.75 4H5V2.75A.75.75 0 015.75 2zm-1 5.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h10.5c.69 0 1.25-.56 1.25-1.25v-6.5c0-.69-.56-1.25-1.25-1.25H4.75z" clipRule="evenodd" />
                  </svg>
                </button>
                <button
                  onClick={() => toggleView('list')}
                  className={`px-2 py-1 min-h-[32px] rounded text-xs font-medium transition-colors ${
                    viewMode === 'list' ? 'bg-accent text-[#090A3D]' : 'bg-secondary-muted/30 text-white/60 hover:text-white'
                  }`}
                  title="List view"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zm0 10.5a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10z" clipRule="evenodd" />
                  </svg>
                </button>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            {user?.role === 'coach' && <DataSharingConsent />}
            {selectedAthlete && (
              <div className="hidden sm:flex items-center gap-3">
                <button
                  onClick={() => {
                    setSessionFormMode('log');
                    setShowSessionForm(true);
                  }}
                  className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
                >
                  + Add Session
                </button>
                <button
                  onClick={() => setShowTemplateModal(true)}
                  className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
                >
                  From Template
                </button>
                {isCoachOrAdmin && (
                  <>
                    <button
                      onClick={() => setShowBatchAssign(true)}
                      className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
                    >
                      Batch Assign
                    </button>
                    <button
                      onClick={() => {
                        setSessionFormMode('assign');
                        setShowSessionForm(true);
                      }}
                      className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
                    >
                      Assign Session
                    </button>
                    <button
                      onClick={() => router.push('/programs?tab=forms')}
                      className="px-4 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
                    >
                      + To Form
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Row 2: Mobile-only action buttons — full width, equal split */}
        {selectedAthlete && (
          <div className="flex sm:hidden items-center gap-2">
            <button
              onClick={() => {
                setSessionFormMode('log');
                setShowSessionForm(true);
              }}
              className="flex-1 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
            >
              + Add
            </button>
            <button
              onClick={() => setShowTemplateModal(true)}
              className="flex-1 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
            >
              Template
            </button>
            {isCoachOrAdmin && (
              <>
                <button
                  onClick={() => setShowBatchAssign(true)}
                  className="flex-1 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
                >
                  Batch
                </button>
                <button
                  onClick={() => {
                    setSessionFormMode('assign');
                    setShowSessionForm(true);
                  }}
                  className="flex-1 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
                >
                  Assign
                </button>
                <button
                  onClick={() => router.push('/programs?tab=forms')}
                  className="flex-1 py-2.5 min-h-[44px] rounded text-sm font-medium bg-accent/10 text-accent hover:bg-accent/20 active:scale-[0.97] transition-colors"
                >
                  Form
                </button>
              </>
            )}
          </div>
        )}
      </div>

      {/* Main Content */}
      {selectedAthlete ? (
        <>
          {/* Compact Readiness Bar */}
          <ReadinessIndicator athleteId={selectedAthlete.id} dataVersion={dataVersion} />

          {/* Sessions — primary content */}
          {viewMode === 'list' ? (
            <SessionTable
              athleteId={selectedAthlete.id}
              onDataChanged={() => setDataVersion((v) => v + 1)}
              showForm={showSessionForm}
              onShowForm={setShowSessionForm}
              isAthlete={isAthlete}
              formMode={sessionFormMode}
              onFormMode={setSessionFormMode}
              userId={user?.user_id}
            />
          ) : (
            <div className="card">
              <SessionCalendar
                sessions={calendarSessions}
                onSelectSession={(session) =>
                  setCalendarExpandedId((prev) => (prev === session.id ? null : session.id))
                }
                expandedSessionId={calendarExpandedId}
              />
              {/* Expanded session detail below calendar */}
              {calendarExpandedId && (() => {
                const session = calendarSessions.find((s) => s.id === calendarExpandedId);
                if (!session) return null;
                return (
                  <div className="mt-4 pt-4 border-t border-secondary-muted/30">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-white">{session.training_type}</span>
                        <span className="text-xs text-white/50">{session.session_date}</span>
                        {session.duration_minutes != null && (
                          <span className="text-xs text-white/50">{session.duration_minutes}min</span>
                        )}
                        {session.rpe != null && (
                          <span className="text-xs text-white/50">RPE {session.rpe}</span>
                        )}
                        {session.srpe != null && (
                          <span className={`text-xs font-semibold ${session.srpe >= 500 ? 'text-red-400' : session.srpe >= 300 ? 'text-yellow-400' : 'text-green-400'}`}>
                            sRPE {session.srpe}
                          </span>
                        )}
                        {session.status && (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${session.status === 'assigned' ? 'bg-amber-500/20 text-amber-400' : 'bg-green-500/20 text-green-400'}`}>
                            {session.status === 'assigned' ? 'Assigned' : 'Completed'}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => setCalendarExpandedId(null)}
                        className="text-white/40 hover:text-white text-xs px-2 py-1 min-h-[36px] transition-colors"
                      >
                        Close
                      </button>
                    </div>
                    {session.notes && (
                      <p className="text-sm text-white/60 mb-2">{session.notes}</p>
                    )}
                    <div className="flex items-center gap-3">
                      {/* Complete button for assigned sessions */}
                      {isAthlete && session.status === 'assigned' && (
                        <button
                          onClick={() => setCalendarCompleteSession(session)}
                          className="px-3 py-1.5 min-h-[36px] rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
                        >
                          Complete
                        </button>
                      )}
                      {/* Add RPE for self-logged sessions without RPE */}
                      {isAthlete && session.status === null && session.rpe == null && session.created_by === user?.user_id && (
                        <button
                          onClick={() => setCalendarCompleteSession(session)}
                          className="px-3 py-1.5 min-h-[36px] rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
                        >
                          Add RPE
                        </button>
                      )}
                      {/* Switch to list view for full session editing */}
                      <button
                        onClick={() => { toggleView('list'); }}
                        className="text-xs text-accent hover:text-accent/80 transition-colors"
                      >
                        Switch to list view for editing
                      </button>
                    </div>
                  </div>
                );
              })()}
            </div>
          )}

          {/* Complete session form for calendar view */}
          {calendarCompleteSession && (
            <SessionLogForm
              athleteId={selectedAthlete.id}
              existingSession={calendarCompleteSession}
              mode="complete"
              isAthlete={isAthlete}
              onClose={() => setCalendarCompleteSession(null)}
              onSaved={() => {
                setCalendarCompleteSession(null);
                setCalendarExpandedId(null);
                setDataVersion((v) => v + 1);
                loadCalendarSessions();
              }}
            />
          )}

          {/* Session form overlay for calendar view */}
          {viewMode === 'calendar' && showSessionForm && (
            <SessionLogForm
              athleteId={selectedAthlete.id}
              mode={sessionFormMode}
              isAthlete={isAthlete}
              onClose={() => setShowSessionForm(false)}
              onSaved={() => {
                setShowSessionForm(false);
                setDataVersion((v) => v + 1);
                loadCalendarSessions();
              }}
            />
          )}

          {/* Analytics Toggles */}
          <div className="flex items-center gap-4 px-1">
            <label className="flex items-center gap-2 cursor-pointer min-h-[44px]">
              <input
                type="checkbox"
                checked={showTrainingLoad}
                onChange={(e) => setShowTrainingLoad(e.target.checked)}
                className="w-4 h-4 rounded accent-[#33CBF4]"
              />
              <span className="text-sm text-white/60">Training Load</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer min-h-[44px]">
              <input
                type="checkbox"
                checked={showWellness}
                onChange={(e) => setShowWellness(e.target.checked)}
                className="w-4 h-4 rounded accent-[#33CBF4]"
              />
              <span className="text-sm text-white/60">Hooper Index</span>
            </label>
          </div>

          {(showTrainingLoad || showWellness) && (
            <div className={`grid gap-4 md:gap-6 ${showTrainingLoad && showWellness ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
              {showTrainingLoad && (
                <div className="card">
                  <LoadChart athleteId={selectedAthlete.id} dataVersion={dataVersion} />
                </div>
              )}
              {showWellness && (
                <div className="card">
                  <WellnessChart athleteId={selectedAthlete.id} onDataChanged={() => setDataVersion((v) => v + 1)} />
                </div>
              )}
            </div>
          )}
        </>
      ) : (
        <NoAthleteSelected message="Select an athlete to view training data" />
      )}

      {showBatchAssign && (
        <BatchAssignModal
          onClose={() => setShowBatchAssign(false)}
          onAssigned={() => {
            setShowBatchAssign(false);
            setDataVersion((v) => v + 1);
          }}
        />
      )}

      {showTemplateModal && selectedAthlete && (
        <TemplateSessionModal
          athleteId={selectedAthlete.id}
          onClose={() => setShowTemplateModal(false)}
          onCreated={() => {
            setShowTemplateModal(false);
            setDataVersion((v) => v + 1);
          }}
        />
      )}
    </div>
  );
}
