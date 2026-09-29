'use client';

import { useState, useCallback } from 'react';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import { BlockSessionEditor } from './BlockSessionEditor';
import { trainingBlocksApi } from '@/lib/api';
import type { TrainingBlockDetail, BlockSession, BlockExercise } from '@/lib/types';

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const BLOCK_CATEGORIES = ['Strength', 'Conditioning', 'Fight Camp', 'Plyometric', 'General'];

interface BlockBuilderModalProps {
  existingBlock: TrainingBlockDetail | null;
  onClose: () => void;
  onSaved: () => void;
}

interface EditingSession {
  blockSessionId?: string; // existing session ID (for updates)
  weekNumber: number;
  dayOfWeek: number;
  sessionName: string;
  trainingType: string;
  notes: string;
  exercises: BlockExercise[];
}

export function BlockBuilderModal({ existingBlock, onClose, onSaved }: BlockBuilderModalProps) {
  const isEditing = existingBlock !== null;

  const [blockName, setBlockName] = useState(existingBlock?.block_name ?? '');
  const [description, setDescription] = useState(existingBlock?.description ?? '');
  const [numWeeks, setNumWeeks] = useState(existingBlock?.num_weeks ?? 4);
  const [category, setCategory] = useState(existingBlock?.category ?? 'Strength');
  const [blockId, setBlockId] = useState<string | null>(existingBlock?.id ?? null);

  // Sessions indexed by "week-day" key
  const [sessions, setSessions] = useState<BlockSession[]>(existingBlock?.sessions ?? []);
  const [activeWeek, setActiveWeek] = useState(1);
  const [editingSession, setEditingSession] = useState<EditingSession | null>(null);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copyFromWeek, setCopyFromWeek] = useState<number | null>(null);

  // Save or create the block first (header only)
  const ensureBlock = useCallback(async (): Promise<string> => {
    if (blockId) {
      // Update metadata
      await trainingBlocksApi.update(blockId, {
        block_name: blockName.trim(),
        description: description.trim() || undefined,
        num_weeks: numWeeks,
        category,
      });
      return blockId;
    } else {
      const created = await trainingBlocksApi.create({
        block_name: blockName.trim(),
        description: description.trim() || undefined,
        num_weeks: numWeeks,
        category,
      });
      setBlockId(created.id);
      return created.id;
    }
  }, [blockId, blockName, description, numWeeks, category]);

  // Save a session (create or update)
  async function handleSaveSession() {
    if (!editingSession || !editingSession.sessionName.trim()) return;
    setSaving(true);
    setError(null);

    try {
      const bid = await ensureBlock();

      const exerciseData = editingSession.exercises.map(ex => {
        const cleaned: Record<string, unknown> = {};
        for (const [k, v] of Object.entries(ex)) {
          if (v != null) cleaned[k] = v;
        }
        return cleaned as unknown as BlockExercise;
      });

      if (editingSession.blockSessionId) {
        // Update existing session
        const updated = await trainingBlocksApi.updateSession(
          bid,
          editingSession.blockSessionId,
          {
            week_number: editingSession.weekNumber,
            day_of_week: editingSession.dayOfWeek,
            session_name: editingSession.sessionName.trim(),
            training_type: editingSession.trainingType,
            notes: editingSession.notes.trim() || undefined,
            exercises: exerciseData,
          }
        );
        setSessions(prev => prev.map(s => s.id === updated.id ? updated : s));
      } else {
        // Create new session
        const created = await trainingBlocksApi.createSession(bid, {
          week_number: editingSession.weekNumber,
          day_of_week: editingSession.dayOfWeek,
          session_name: editingSession.sessionName.trim(),
          training_type: editingSession.trainingType,
          notes: editingSession.notes.trim() || undefined,
          exercises: exerciseData,
        });
        setSessions(prev => [...prev, created]);
      }
      setEditingSession(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save session');
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteSession(sessionId: string) {
    if (!blockId) return;
    try {
      await trainingBlocksApi.deleteSession(blockId, sessionId);
      setSessions(prev => prev.filter(s => s.id !== sessionId));
    } catch {
      setError('Failed to delete session');
    }
  }

  async function handleCopyWeek(sourceWeek: number, targetWeek: number) {
    if (!blockId) return;
    setSaving(true);
    setError(null);
    try {
      const weekSessions = sessions.filter(s => s.week_number === sourceWeek);
      for (const session of weekSessions) {
        await trainingBlocksApi.duplicateSession(blockId, session.id, targetWeek);
      }
      // Reload block
      const detail = await trainingBlocksApi.get(blockId);
      setSessions(detail.sessions);
      setCopyFromWeek(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to copy week');
    } finally {
      setSaving(false);
    }
  }

  function handleDone() {
    if (blockId) {
      onSaved();
    } else {
      onClose();
    }
  }

  function sessionsForWeekDay(week: number, day: number) {
    return sessions.filter(s => s.week_number === week && s.day_of_week === day);
  }

  function openNewSession(week: number, day: number) {
    setEditingSession({
      weekNumber: week,
      dayOfWeek: day,
      sessionName: '',
      trainingType: category === 'Strength' ? 'Strength' : 'Conditioning',
      notes: '',
      exercises: [],
    });
  }

  function openEditSession(session: BlockSession) {
    setEditingSession({
      blockSessionId: session.id,
      weekNumber: session.week_number,
      dayOfWeek: session.day_of_week,
      sessionName: session.session_name,
      trainingType: session.training_type,
      notes: session.notes ?? '',
      exercises: session.exercises ?? [],
    });
  }

  return (
    <ResponsiveModal isOpen onClose={onClose} maxWidth="3xl" title={isEditing ? 'Edit Block' : 'New Training Block'}>
      <div className="space-y-4">
        {/* Block Header */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div className="sm:col-span-2">
            <label className="block text-xs text-white/50 mb-1">Block Name</label>
            <input
              type="text"
              value={blockName}
              onChange={(e) => setBlockName(e.target.value)}
              className="input-field w-full"
              placeholder="e.g. 4-Week Strength Block"
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">Weeks</label>
            <input
              type="number"
              value={numWeeks}
              onChange={(e) => setNumWeeks(Math.min(16, Math.max(1, parseInt(e.target.value) || 1)))}
              className="input-field w-full"
              min={1}
              max={16}
            />
          </div>
          <div>
            <label className="block text-xs text-white/50 mb-1">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="input-field w-full"
            >
              {BLOCK_CATEGORIES.map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs text-white/50 mb-1">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="input-field w-full"
            rows={2}
            placeholder="Optional block description..."
          />
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-sm text-red-400">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-200">&times;</button>
          </div>
        )}

        {/* Session Editor (inline when editing) */}
        {editingSession ? (
          <div className="border border-accent/30 rounded-lg p-4 bg-accent/5">
            <h3 className="text-sm font-medium mb-3">
              {editingSession.blockSessionId ? 'Edit' : 'New'} Session — Week {editingSession.weekNumber}, {DAY_LABELS[editingSession.dayOfWeek - 1]}
            </h3>
            <BlockSessionEditor
              sessionName={editingSession.sessionName}
              trainingType={editingSession.trainingType}
              notes={editingSession.notes}
              exercises={editingSession.exercises}
              onSessionNameChange={(v) => setEditingSession({ ...editingSession, sessionName: v })}
              onTrainingTypeChange={(v) => setEditingSession({ ...editingSession, trainingType: v })}
              onNotesChange={(v) => setEditingSession({ ...editingSession, notes: v })}
              onExercisesChange={(v) => setEditingSession({ ...editingSession, exercises: v })}
              onSave={handleSaveSession}
              onCancel={() => setEditingSession(null)}
            />
          </div>
        ) : (
          <>
            {/* Week Tabs */}
            <div className="flex items-center gap-1 flex-wrap">
              {Array.from({ length: numWeeks }, (_, i) => i + 1).map(week => {
                const weekSessionCount = sessions.filter(s => s.week_number === week).length;
                return (
                  <button
                    key={week}
                    onClick={() => setActiveWeek(week)}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                      activeWeek === week
                        ? 'bg-accent text-[#090A3D]'
                        : 'bg-white/5 text-white/60 hover:bg-white/10'
                    }`}
                  >
                    Wk {week}
                    {weekSessionCount > 0 && (
                      <span className="ml-1 text-[10px] opacity-70">({weekSessionCount})</span>
                    )}
                  </button>
                );
              })}

              {/* Copy Week */}
              {blockId && sessions.filter(s => s.week_number === activeWeek).length > 0 && (
                <div className="ml-auto flex items-center gap-1">
                  {copyFromWeek === activeWeek ? (
                    <>
                      <span className="text-xs text-white/40">{saving ? 'Copying...' : 'Copy to:'}</span>
                      {Array.from({ length: numWeeks }, (_, i) => i + 1)
                        .filter(w => w !== activeWeek)
                        .map(w => (
                          <button
                            key={w}
                            onClick={() => handleCopyWeek(activeWeek, w)}
                            disabled={saving}
                            className="px-2 py-1 rounded text-[10px] bg-white/5 text-white/60 hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Wk {w}
                          </button>
                        ))}
                      <button
                        onClick={() => setCopyFromWeek(null)}
                        disabled={saving}
                        className="text-xs text-white/40 hover:text-white ml-1 disabled:opacity-50"
                      >
                        &times;
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => setCopyFromWeek(activeWeek)}
                      className="px-2 py-1 rounded text-[10px] bg-white/5 text-white/60 hover:bg-white/10"
                    >
                      Copy Week
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Day Grid */}
            <div className="grid grid-cols-7 gap-1">
              {DAY_LABELS.map((label, i) => (
                <div key={label} className="text-center text-[10px] text-white/40 pb-1">
                  {label}
                </div>
              ))}
              {Array.from({ length: 7 }, (_, i) => i + 1).map(day => {
                const daySessions = sessionsForWeekDay(activeWeek, day);
                return (
                  <div
                    key={day}
                    className="min-h-[80px] border border-secondary-muted rounded p-1 hover:border-accent/30 transition-colors"
                  >
                    {daySessions.map(session => (
                      <div
                        key={session.id}
                        className="mb-1 p-1.5 rounded bg-accent/10 border border-accent/20 cursor-pointer hover:bg-accent/20 transition-colors"
                        onClick={() => openEditSession(session)}
                      >
                        <p className="text-[10px] font-medium truncate">{session.session_name}</p>
                        <p className="text-[9px] text-white/40 truncate">
                          {session.training_type} &middot; {session.exercises?.length ?? 0} ex
                        </p>
                        <button
                          onClick={(e) => { e.stopPropagation(); handleDeleteSession(session.id); }}
                          className="text-[9px] text-red-400/60 hover:text-red-400 mt-0.5"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                    <button
                      onClick={() => openNewSession(activeWeek, day)}
                      className="w-full text-center text-[10px] text-white/30 hover:text-accent py-1 transition-colors"
                    >
                      +
                    </button>
                  </div>
                );
              })}
            </div>
          </>
        )}

        {/* Footer */}
        {!editingSession && (
          <div className="flex justify-end gap-2 pt-2 border-t border-secondary-muted">
            <button
              onClick={onClose}
              className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleDone}
              disabled={!blockName.trim() || saving}
              className="px-4 py-2 min-h-[44px] rounded text-sm font-medium bg-accent text-[#090A3D] hover:bg-accent/80 transition-colors disabled:opacity-50"
            >
              {saving ? 'Saving...' : blockId ? 'Done' : 'Create Block'}
            </button>
          </div>
        )}
      </div>
    </ResponsiveModal>
  );
}
