'use client';

import { useState, useEffect, useCallback } from 'react';
import { trainingApi, exercisesApi } from '@/lib/api';
import { SessionLogForm } from './SessionLogForm';
import type { SessionFormMode } from './SessionLogForm';
import { ExerciseTable } from './ExerciseTable';
import { IntervalTimer } from './IntervalTimer';
import { SessionActionMenu } from './SessionActionMenu';
import type { TimerExercise } from './useIntervalTimer';
import type { TrainingSession } from '@/lib/types';
import { useIsMobile } from '@/lib/hooks/useMediaQuery';

interface SessionTableProps {
  athleteId: string;
  onDataChanged?: () => void;
  showForm: boolean;
  onShowForm: (show: boolean) => void;
  isAthlete?: boolean;
  formMode?: 'log' | 'assign';
  onFormMode?: (mode: 'log' | 'assign') => void;
  userId?: string;
}

export function SessionTable({ athleteId, onDataChanged, showForm, onShowForm, isAthlete, formMode = 'log', onFormMode, userId }: SessionTableProps) {
  const isMobile = useIsMobile();
  const [sessions, setSessions] = useState<TrainingSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingSession, setEditingSession] = useState<TrainingSession | null>(null);
  const [editMode, setEditMode] = useState<SessionFormMode>('log');
  const [expandedSessionId, setExpandedSessionId] = useState<string | null>(null);
  const [autoAddExerciseSessionId, setAutoAddExerciseSessionId] = useState<string | null>(null);
  const [autoTemplateSessionId, setAutoTemplateSessionId] = useState<string | null>(null);
  const [autoEditSessionId, setAutoEditSessionId] = useState<string | null>(null);
  const [timerSessionId, setTimerSessionId] = useState<string | null>(null);
  const [timerExercises, setTimerExercises] = useState<TimerExercise[]>([]);

  const loadSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await trainingApi.listSessions(athleteId);
      setSessions(data);
    } catch (err) {
      setError('Failed to load sessions');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  async function handleDelete(sessionId: string) {
    if (!window.confirm('Delete this training session?')) return;
    try {
      await trainingApi.deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (expandedSessionId === sessionId) setExpandedSessionId(null);
      onDataChanged?.();
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  }

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr + 'T00:00:00');
    return d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
    });
  }

  const today = new Date().toISOString().slice(0, 10);

  function isOverdue(session: TrainingSession): boolean {
    return session.status === 'assigned' && session.session_date < today;
  }

  function getSrpeColor(srpe: number): string {
    if (srpe >= 500) return 'text-red-400';
    if (srpe >= 300) return 'text-yellow-400';
    return 'text-green-400';
  }

  function toggleExpand(sessionId: string) {
    setExpandedSessionId((prev) => (prev === sessionId ? null : sessionId));
  }

  /** Can the current user edit/delete this session? */
  function canEditSession(session: TrainingSession): boolean {
    if (!isAthlete) return true; // Coach/admin can edit all
    // Athletes can edit their own self-logged sessions only
    return session.status === null && session.created_by === userId;
  }

  function canDeleteSession(session: TrainingSession): boolean {
    if (!isAthlete) return true;
    return session.status === null && session.created_by === userId;
  }

  function canCompleteSession(session: TrainingSession): boolean {
    if (!isAthlete) return false;
    if (session.status === 'assigned') return true;
    // Self-logged sessions without RPE can be completed
    if (session.status === null && session.created_by === userId && session.rpe == null) return true;
    return false;
  }

  /** Can the current user manage exercises on this session (add/delete/full edit)? */
  function canManageExercises(session: TrainingSession): boolean {
    if (!isAthlete) return true; // Coach/admin can manage all
    // Athletes can manage exercises on their own self-logged sessions
    return session.status === null && session.created_by === userId;
  }

  async function handleLaunchTimer(sessionId: string) {
    try {
      const exercises = await exercisesApi.list(sessionId);

      // Check if this is a circuit session (any exercise has category=Circuit)
      const hasCircuit = exercises.some(ex => ex.exercise_category?.toLowerCase() === 'circuit');

      let timerExs: TimerExercise[];

      if (hasCircuit) {
        // Circuit: one TimerExercise per prescription row (preserving set_number order)
        // This gives the timer the correct sequential playback: Ex1R1 -> Ex2R1 -> Ex3R1 -> Ex1R2 -> ...
        timerExs = exercises
          .filter(ex => ex.duration_seconds && ex.duration_seconds > 0)
          .sort((a, b) => a.set_number - b.set_number)
          .map(ex => ({
            exercise_name: ex.exercise_name,
            sets: [{
              reps: 1,
              duration_seconds: ex.duration_seconds!,
              rest_between_reps_seconds: 0,
              rest_after_set_seconds: ex.rest_seconds || 10,
            }],
            intensity_type: ex.intensity_type,
            intensity_value: ex.intensity_value,
            intensity_min: ex.intensity_min,
            intensity_max: ex.intensity_max,
          }));
      } else {
        // Conditioning/other: group by exercise_name, build TimerSetConfig[] per exercise
        const grouped = new Map<string, TimerExercise>();
        for (const ex of exercises) {
          if (!ex.duration_seconds || ex.duration_seconds <= 0) continue;
          if (!grouped.has(ex.exercise_name)) {
            grouped.set(ex.exercise_name, {
              exercise_name: ex.exercise_name,
              sets: [],
              intensity_type: ex.intensity_type,
              intensity_value: ex.intensity_value,
              intensity_min: ex.intensity_min,
              intensity_max: ex.intensity_max,
            });
          }
          grouped.get(ex.exercise_name)!.sets.push({
            reps: ex.reps || 1,
            duration_seconds: ex.duration_seconds,
            rest_between_reps_seconds: ex.rest_between_reps_seconds || 0,
            rest_after_set_seconds: ex.rest_seconds || 60,
            rep_durations: ex.rep_durations || undefined,
            rest_between_reps: ex.rest_between_reps || undefined,
            rep_intensity_values: ex.rep_intensity_values || undefined,
          });
        }
        timerExs = Array.from(grouped.values());
      }

      if (timerExs.length > 0) {
        setTimerSessionId(sessionId);
        setTimerExercises(timerExs);
      }
    } catch (err) {
      console.error('Failed to load exercises for timer:', err);
    }
  }

  return (
    <div>
      {loading ? (
        <div className="text-center py-8">
          <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <p className="text-red-400 text-sm py-4 text-center">{error}</p>
      ) : sessions.length === 0 ? (
        <p className="text-white/60 text-sm py-8 text-center">
          No training sessions logged yet
        </p>
      ) : (
        <div className="space-y-2">
          {sessions.map((session) => {
            const isExpanded = expandedSessionId === session.id;
            return (
              <div
                key={session.id}
                className="rounded-lg border border-secondary-muted/30 bg-secondary-muted/5 overflow-hidden"
              >
                {/* Session row with inline actions */}
                <div className="flex items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2.5 min-h-[44px] hover:bg-secondary-muted/10 transition-colors">
                  {/* Clickable session info area */}
                  <button
                    type="button"
                    onClick={() => toggleExpand(session.id)}
                    className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0 text-left"
                  >
                    <span className="text-sm text-white/60 font-medium shrink-0 w-14">
                      {formatDate(session.session_date)}
                    </span>
                    <span className="text-sm font-medium text-white truncate">
                      {session.training_type}
                    </span>
                    {['conditioning', 'circuit'].includes(session.training_type.toLowerCase()) && (
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5 text-white/40 shrink-0" aria-label="Conditioning — has timer">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z" clipRule="evenodd" />
                      </svg>
                    )}
                    {session.duration_minutes != null && (
                      <span className="text-xs text-white/50 shrink-0 hidden sm:inline">
                        {session.duration_minutes}min
                      </span>
                    )}
                    {session.rpe != null && (
                      <span className="text-xs text-white/50 shrink-0 hidden sm:inline">
                        RPE {session.rpe}
                      </span>
                    )}
                    {session.srpe != null && (
                      <span className={`text-xs font-semibold shrink-0 ${getSrpeColor(session.srpe)}`}>
                        sRPE {session.srpe}
                      </span>
                    )}
                    {session.status === 'assigned' && (
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${
                        isOverdue(session)
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {isOverdue(session) ? 'Overdue' : 'Assigned'}
                      </span>
                    )}
                    {session.status === 'completed' && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-green-500/20 text-green-400 shrink-0">
                        Completed
                      </span>
                    )}
                    {session.status === null && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-white/10 text-white/50 shrink-0">
                        Logged
                      </span>
                    )}
                  </button>

                  {/* Action buttons: kebab menu on mobile, inline on desktop */}
                  {isMobile ? (
                    <SessionActionMenu
                      canComplete={canCompleteSession(session)}
                      canDelete={canDeleteSession(session)}
                      isCoachOrAdmin={!isAthlete}
                      canManageExercises={canManageExercises(session)}
                      completeLabel={session.status === 'assigned' ? 'Complete' : 'Add RPE'}
                      showTimer={canManageExercises(session) && ['conditioning', 'circuit'].includes(session.training_type.toLowerCase())}
                      onComplete={() => {
                        setEditingSession(session);
                        setEditMode('complete');
                        onShowForm(true);
                      }}
                      onAddExercise={() => {
                        setExpandedSessionId(session.id);
                        setAutoAddExerciseSessionId(session.id);
                      }}
                      onTemplate={() => {
                        setExpandedSessionId(session.id);
                        setAutoTemplateSessionId(session.id);
                      }}
                      onEditExercises={canManageExercises(session) ? () => {
                        setExpandedSessionId(session.id);
                        setAutoEditSessionId(session.id);
                      } : undefined}
                      onTimer={() => handleLaunchTimer(session.id)}
                      onDelete={() => handleDelete(session.id)}
                    />
                  ) : (
                    <div className="flex items-center gap-1 shrink-0">
                      {canCompleteSession(session) && (
                        <button
                          onClick={() => {
                            setEditingSession(session);
                            setEditMode('complete');
                            onShowForm(true);
                          }}
                          className="px-2 py-1.5 min-h-[36px] rounded text-xs font-medium bg-accent text-[#090A3D] hover:bg-accent/80 active:scale-[0.97] transition-colors"
                        >
                          {session.status === 'assigned' ? 'Complete' : 'Add RPE'}
                        </button>
                      )}
                      {canManageExercises(session) && (
                        <>
                          <button
                            onClick={() => {
                              setExpandedSessionId(session.id);
                              setAutoAddExerciseSessionId(session.id);
                            }}
                            className="px-2 py-1.5 min-h-[36px] rounded text-xs font-medium text-accent hover:bg-accent/10 active:scale-[0.97] transition-colors"
                            title="Add exercise"
                          >
                            + Exercise
                          </button>
                          <button
                            onClick={() => {
                              setExpandedSessionId(session.id);
                              setAutoTemplateSessionId(session.id);
                            }}
                            className="px-2 py-1.5 min-h-[36px] rounded text-xs font-medium text-accent hover:bg-accent/10 active:scale-[0.97] transition-colors"
                            title="Import from template"
                          >
                            Template
                          </button>
                          <button
                            onClick={() => {
                              setExpandedSessionId(session.id);
                              setAutoEditSessionId(session.id);
                            }}
                            className="px-2 py-1.5 min-h-[36px] rounded text-xs font-medium text-accent hover:bg-accent/10 active:scale-[0.97] transition-colors"
                            title="Edit exercises"
                          >
                            Edit
                          </button>
                        </>
                      )}
                      {canManageExercises(session) && ['conditioning', 'circuit'].includes(session.training_type.toLowerCase()) && (
                        <button
                          onClick={() => handleLaunchTimer(session.id)}
                          className="px-2 py-1.5 min-h-[36px] rounded text-xs font-medium text-accent hover:bg-accent/10 active:scale-[0.97] transition-colors"
                          title="Launch interval timer"
                        >
                          Timer
                        </button>
                      )}
                      {canDeleteSession(session) && (
                        <button
                          onClick={() => handleDelete(session.id)}
                          className="px-2 py-1.5 min-h-[36px] rounded text-xs font-medium text-red-400/60 hover:bg-red-400/10 hover:text-red-400 active:scale-[0.97] transition-colors"
                          title="Delete session"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                            <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
                          </svg>
                        </button>
                      )}
                    </div>
                  )}

                  {/* Expand chevron */}
                  <button
                    type="button"
                    onClick={() => toggleExpand(session.id)}
                    className="shrink-0 p-1"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      className={`w-4 h-4 text-white/40 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    >
                      <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-secondary-muted/20">
                    {/* Description banner */}
                    {session.description && (
                      <div className="mt-3 mb-2 px-3 py-2 rounded bg-accent/5 border border-accent/20">
                        <p className="text-xs text-white/60">{session.description}</p>
                      </div>
                    )}
                    {/* Inline exercises */}
                    <ExerciseTable
                      sessionId={session.id}
                      trainingType={session.training_type}
                      readOnly={!canManageExercises(session)}
                      autoShowAddForm={autoAddExerciseSessionId === session.id}
                      onAddFormShown={() => setAutoAddExerciseSessionId(null)}
                      autoShowTemplatePicker={autoTemplateSessionId === session.id}
                      onTemplatePickerShown={() => setAutoTemplateSessionId(null)}
                      autoEdit={autoEditSessionId === session.id}
                      onAutoEditDone={() => setAutoEditSessionId(null)}
                    />

                    {/* Notes */}
                    {session.notes && (
                      <div className="mt-3 pt-3 border-t border-secondary-muted/20">
                        <span className="text-xs text-white/40">Notes:</span>
                        <p className="text-sm text-white/70 mt-0.5">{session.notes}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showForm && (
        <SessionLogForm
          athleteId={athleteId}
          existingSession={editingSession}
          mode={editingSession ? editMode : formMode}
          isAthlete={isAthlete}
          onClose={() => { onShowForm(false); setEditingSession(null); }}
          onSaved={() => {
            onShowForm(false);
            setEditingSession(null);
            loadSessions();
            onDataChanged?.();
          }}
        />
      )}

      {timerSessionId && timerExercises.length > 0 && (
        <IntervalTimer
          sessionId={timerSessionId}
          exercises={timerExercises}
          onClose={() => {
            setTimerSessionId(null);
            setTimerExercises([]);
          }}
          onSaved={() => {
            loadSessions();
            onDataChanged?.();
          }}
        />
      )}
    </div>
  );
}
