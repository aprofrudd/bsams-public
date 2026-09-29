'use client';

import { useState, useEffect, useCallback } from 'react';
import { vbtApi } from '@/lib/api';
import { VbtProfileForm } from './VbtProfileForm';
import { VbtChart } from './VbtChart';
import { VbtCalculator } from './VbtCalculator';
import { ResponsiveModal } from '@/components/ResponsiveModal';
import type { VbtProfileListItem, VbtProfile, VbtAnalysis } from '@/lib/types';

interface VbtProfilesViewProps {
  athleteId: string;
  readOnly?: boolean;
}

function R2Badge({ r2 }: { r2: number }) {
  let color = 'bg-red-500/20 text-red-400';
  if (r2 >= 0.95) color = 'bg-green-500/20 text-green-400';
  else if (r2 >= 0.90) color = 'bg-yellow-500/20 text-yellow-400';
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-mono ${color}`}>
      R²={r2.toFixed(3)}
    </span>
  );
}

export function VbtProfilesView({ athleteId, readOnly }: VbtProfilesViewProps) {
  const [profiles, setProfiles] = useState<VbtProfileListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editProfile, setEditProfile] = useState<VbtProfile | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedProfile, setExpandedProfile] = useState<VbtProfile | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [predictAnalysis, setPredictAnalysis] = useState<VbtAnalysis | null>(null);

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await vbtApi.listProfiles(athleteId);
      setProfiles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profiles');
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles]);

  async function handleExpand(profileId: string) {
    if (expandedId === profileId) {
      setExpandedId(null);
      setExpandedProfile(null);
      return;
    }
    try {
      const full = await vbtApi.getProfile(profileId);
      setExpandedProfile(full);
      setExpandedId(profileId);
    } catch {
      // Silently fail expand
    }
  }

  async function handleEdit(profileId: string) {
    try {
      const full = await vbtApi.getProfile(profileId);
      setEditProfile(full);
      setShowForm(true);
    } catch {
      // Silently fail
    }
  }

  async function handleDelete(profileId: string) {
    if (!confirm('Delete this VBT profile?')) return;
    setDeleting(profileId);
    try {
      await vbtApi.deleteProfile(profileId);
      setProfiles((prev) => prev.filter((p) => p.id !== profileId));
      if (expandedId === profileId) {
        setExpandedId(null);
        setExpandedProfile(null);
      }
    } catch {
      // Silently fail delete
    } finally {
      setDeleting(null);
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditProfile(null);
    loadProfiles();
  }

  // Group profiles by exercise
  const grouped = profiles.reduce<Record<string, VbtProfileListItem[]>>((acc, p) => {
    if (!acc[p.exercise_name]) acc[p.exercise_name] = [];
    acc[p.exercise_name].push(p);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with New Profile + Predict buttons */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">
          {profiles.length} profile{profiles.length !== 1 ? 's' : ''}
        </p>
        <div className="flex items-center gap-2">
          {profiles.some(p => p.analysis) && (
            <button
              onClick={async () => {
                const withAnalysis = profiles.filter(p => p.analysis);
                if (withAnalysis.length === 0) return;
                try {
                  const full = await vbtApi.getProfile(withAnalysis[0].id);
                  if (full.analysis) setPredictAnalysis(full.analysis);
                } catch {
                  // silently fail
                }
              }}
              className="btn-secondary text-sm px-4 py-1.5"
            >
              Predict
            </button>
          )}
          {!readOnly && (
            <button
              onClick={() => {
                setEditProfile(null);
                setShowForm(true);
              }}
              className="btn-primary text-sm px-4 py-1.5"
            >
              + New Profile
            </button>
          )}
        </div>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {profiles.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-white/40 text-sm mb-3">No VBT profiles yet</p>
          {!readOnly && (
            <button
              onClick={() => setShowForm(true)}
              className="btn-primary text-sm px-4 py-1.5"
            >
              Create First Profile
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(grouped).map(([exercise, exerciseProfiles]) => (
            <div key={exercise}>
              <h3 className="font-heading uppercase tracking-wider text-sm text-accent mb-2">
                {exercise}
              </h3>
              <div className="space-y-2">
                {exerciseProfiles.map((p) => (
                  <div key={p.id} className="border border-secondary-muted/50 rounded-lg overflow-hidden">
                    {/* Profile Summary Row */}
                    <div
                      className="flex items-center justify-between px-4 py-3 min-h-[44px] cursor-pointer hover:bg-secondary-muted/20 active:bg-secondary-muted/30 transition-colors"
                      onClick={() => handleExpand(p.id)}
                    >
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-sm text-white/80">
                          {new Date(p.profile_date).toLocaleDateString('en-GB', {
                            day: 'numeric',
                            month: 'short',
                            year: 'numeric',
                          })}
                        </span>
                        {p.analysis?.estimated_1rm_kg != null && (
                          <span className="text-sm font-semibold text-white">
                            Est. 1RM: {p.analysis.estimated_1rm_kg} kg
                          </span>
                        )}
                        {p.analysis && <R2Badge r2={p.analysis.r_squared} />}
                        <span className="text-xs text-white/30">{p.set_count} sets</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {!readOnly && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEdit(p.id);
                            }}
                            className="text-white/30 hover:text-accent active:text-accent/70 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors"
                            title="Edit"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
                              <path d="M13.488 2.513a1.75 1.75 0 0 0-2.475 0L6.75 6.774a2.75 2.75 0 0 0-.596.892l-.848 2.047a.75.75 0 0 0 .98.98l2.047-.848a2.75 2.75 0 0 0 .892-.596l4.261-4.262a1.75 1.75 0 0 0 0-2.474Z" />
                              <path d="M4.75 3.5c-.69 0-1.25.56-1.25 1.25v6.5c0 .69.56 1.25 1.25 1.25h6.5c.69 0 1.25-.56 1.25-1.25V9A.75.75 0 0 1 14 9v2.25A2.75 2.75 0 0 1 11.25 14h-6.5A2.75 2.75 0 0 1 2 11.25v-6.5A2.75 2.75 0 0 1 4.75 2H7a.75.75 0 0 1 0 1.5H4.75Z" />
                            </svg>
                          </button>
                        )}
                        {!readOnly && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(p.id);
                            }}
                            disabled={deleting === p.id}
                            className="text-white/30 hover:text-red-400 active:text-red-300 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors disabled:opacity-50"
                            title="Delete"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
                              <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
                            </svg>
                          </button>
                        )}
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 16 16"
                          fill="currentColor"
                          className={`w-4 h-4 text-white/30 transition-transform ${expandedId === p.id ? 'rotate-180' : ''}`}
                        >
                          <path fillRule="evenodd" d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                        </svg>
                      </div>
                    </div>

                    {/* Expanded Detail */}
                    {expandedId === p.id && expandedProfile && (
                      <div className="border-t border-secondary-muted/50 px-4 py-3 space-y-4 bg-primary-dark/30">
                        {/* Load-Velocity Chart */}
                        <VbtChart profile={expandedProfile} />

                        {/* Analysis Summary */}
                        {expandedProfile.analysis && (
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                            <div className="bg-secondary-muted/20 rounded-lg p-2 text-center">
                              <div className="text-xs text-white/40">Est. 1RM</div>
                              <div className="text-lg font-semibold text-white">
                                {expandedProfile.analysis.estimated_1rm_kg ?? '-'}{' '}
                                <span className="text-xs text-white/40">kg</span>
                              </div>
                            </div>
                            <div className="bg-secondary-muted/20 rounded-lg p-2 text-center">
                              <div className="text-xs text-white/40">V0</div>
                              <div className="text-lg font-semibold text-white">
                                {expandedProfile.analysis.v0_ms ?? '-'}{' '}
                                <span className="text-xs text-white/40">m/s</span>
                              </div>
                            </div>
                            <div className="bg-secondary-muted/20 rounded-lg p-2 text-center">
                              <div className="text-xs text-white/40">R²</div>
                              <div className="text-lg font-semibold text-white">
                                {expandedProfile.analysis.r_squared.toFixed(4)}
                              </div>
                            </div>
                            <div className="bg-secondary-muted/20 rounded-lg p-2 text-center">
                              <div className="text-xs text-white/40">MVT</div>
                              <div className="text-lg font-semibold text-white">
                                {expandedProfile.analysis.mvt_used_ms.toFixed(2)}{' '}
                                <span className="text-xs text-white/40">m/s</span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Sets Table */}
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead>
                              <tr className="text-white/40 text-xs">
                                <th className="text-left py-1 pr-3">Set</th>
                                <th className="text-right py-1 px-3">Load (kg)</th>
                                <th className="text-right py-1 px-3">Mean V (m/s)</th>
                                <th className="text-right py-1 px-3">Peak V (m/s)</th>
                                <th className="text-right py-1 pl-3">Reps</th>
                              </tr>
                            </thead>
                            <tbody>
                              {expandedProfile.sets.map((s) => (
                                <tr key={s.id} className="border-t border-secondary-muted/30">
                                  <td className="py-1.5 pr-3 text-white/60">{s.set_number}</td>
                                  <td className="py-1.5 px-3 text-right text-white">{s.load_kg}</td>
                                  <td className="py-1.5 px-3 text-right text-white/80">
                                    {s.mean_velocity_ms?.toFixed(3) ?? '-'}
                                  </td>
                                  <td className="py-1.5 px-3 text-right text-white/80">
                                    {s.peak_velocity_ms?.toFixed(3) ?? '-'}
                                  </td>
                                  <td className="py-1.5 pl-3 text-right text-white/60">
                                    {s.reps ?? '-'}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        {/* Velocity Threshold Calculator */}
                        {expandedProfile.analysis && (
                          <VbtCalculator analysis={expandedProfile.analysis} />
                        )}

                        {/* Notes */}
                        {expandedProfile.notes && (
                          <p className="text-xs text-white/40">{expandedProfile.notes}</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <VbtProfileForm
          athleteId={athleteId}
          existingProfile={editProfile}
          onClose={() => {
            setShowForm(false);
            setEditProfile(null);
          }}
          onSaved={handleSaved}
        />
      )}

      {/* Predict Modal */}
      <ResponsiveModal
        isOpen={predictAnalysis !== null}
        onClose={() => setPredictAnalysis(null)}
        title="VBT Predictor"
        maxWidth="md"
      >
        {predictAnalysis && <VbtCalculator analysis={predictAnalysis} />}
      </ResponsiveModal>
    </div>
  );
}
