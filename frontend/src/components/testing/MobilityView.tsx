'use client';

import { useState, useEffect, useCallback } from 'react';
import { assessmentApi } from '@/lib/api';
import { AssessmentForm } from './AssessmentForm';
import type { MovementAssessmentListItem, MovementAssessment } from '@/lib/types';

interface MobilityViewProps {
  athleteId: string;
  readOnly?: boolean;
}

const ASSESSMENT_TYPE_LABELS: Record<string, string> = {
  overhead_squat: 'Overhead Squat',
  single_leg_squat_left: 'Single Leg Squat (Left)',
  single_leg_squat_right: 'Single Leg Squat (Right)',
};

function SeverityBadge({ severity }: { severity: string }) {
  let color = 'bg-yellow-500/20 text-yellow-400';
  if (severity === 'mild') color = 'bg-green-500/20 text-green-400';
  else if (severity === 'significant') color = 'bg-red-500/20 text-red-400';
  return (
    <span className={`inline-block px-1.5 py-0.5 rounded text-xs ${color}`}>
      {severity}
    </span>
  );
}

function FindingsDisplay({ findings }: { findings: Record<string, any> }) {
  const regions = Object.entries(findings);
  if (regions.length === 0) {
    return <p className="text-xs text-white/30 italic">No findings recorded</p>;
  }

  const regionLabels: Record<string, string> = {
    feet_ankles: 'Feet & Ankles',
    knees: 'Knees',
    lphc: 'LPHC',
    shoulders: 'Shoulders',
    head: 'Head',
  };

  const compensationLabels: Record<string, string> = {
    turn_out: 'Turn Out',
    flatten: 'Flatten',
    heels_rise: 'Heels Rise',
    valgus: 'Knee Valgus',
    excessive_forward: 'Excessive Forward',
    forward_lean: 'Forward Lean',
    low_back_arch: 'Low Back Arch',
    hip_shift: 'Hip Shift',
    arms_fall_forward: 'Arms Fall Forward',
    forward_protrusion: 'Forward Protrusion',
    hip_hike: 'Hip Hike',
    hip_drop: 'Hip Drop',
    trunk_rotation: 'Trunk Rotation',
    loss_of_balance: 'Loss of Balance',
  };

  return (
    <div className="space-y-2">
      {regions.map(([regionKey, compensations]) => {
        const observed = Object.entries(compensations as Record<string, any>).filter(
          ([, comp]) => comp?.observed
        );
        if (observed.length === 0) return null;
        return (
          <div key={regionKey}>
            <div className="text-xs text-white/50 font-heading uppercase tracking-wider mb-1">
              {regionLabels[regionKey] ?? regionKey}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {observed.map(([compKey, comp]) => (
                <div key={compKey} className="flex items-center gap-1">
                  <span className="text-sm text-white/80">
                    {compensationLabels[compKey] ?? compKey}
                  </span>
                  {comp.severity && <SeverityBadge severity={comp.severity} />}
                  {comp.side && (
                    <span className="text-xs text-white/40">({comp.side})</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function MobilityView({ athleteId, readOnly }: MobilityViewProps) {
  const [assessments, setAssessments] = useState<MovementAssessmentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editAssessment, setEditAssessment] = useState<MovementAssessment | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedAssessment, setExpandedAssessment] = useState<MovementAssessment | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadAssessments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await assessmentApi.listAssessments(athleteId);
      setAssessments(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load assessments');
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadAssessments();
  }, [loadAssessments]);

  async function handleExpand(assessmentId: string) {
    if (expandedId === assessmentId) {
      setExpandedId(null);
      setExpandedAssessment(null);
      return;
    }
    try {
      const full = await assessmentApi.getAssessment(assessmentId);
      setExpandedAssessment(full);
      setExpandedId(assessmentId);
    } catch {
      // Silently fail expand
    }
  }

  async function handleEdit(assessmentId: string) {
    try {
      const full = await assessmentApi.getAssessment(assessmentId);
      setEditAssessment(full);
      setShowForm(true);
    } catch {
      // Silently fail
    }
  }

  async function handleDelete(assessmentId: string) {
    if (!confirm('Delete this assessment?')) return;
    setDeleting(assessmentId);
    try {
      await assessmentApi.deleteAssessment(assessmentId);
      setAssessments((prev) => prev.filter((a) => a.id !== assessmentId));
      if (expandedId === assessmentId) {
        setExpandedId(null);
        setExpandedAssessment(null);
      }
    } catch {
      // Silently fail delete
    } finally {
      setDeleting(null);
    }
  }

  function handleSaved() {
    setShowForm(false);
    setEditAssessment(null);
    loadAssessments();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="inline-block w-6 h-6 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-white/40">
          {assessments.length} assessment{assessments.length !== 1 ? 's' : ''}
        </p>
        {!readOnly && (
          <button
            onClick={() => {
              setEditAssessment(null);
              setShowForm(true);
            }}
            className="btn-primary text-sm px-4 py-1.5"
          >
            + New Assessment
          </button>
        )}
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {assessments.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-white/40 text-sm mb-3">No mobility assessments yet</p>
          {!readOnly && (
            <button
              onClick={() => setShowForm(true)}
              className="btn-primary text-sm px-4 py-1.5"
            >
              Create First Assessment
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {assessments.map((a) => (
            <div key={a.id} className="border border-secondary-muted/50 rounded-lg overflow-hidden">
              {/* Summary Row */}
              <div
                className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-secondary-muted/20 transition-colors"
                onClick={() => handleExpand(a.id)}
              >
                <div className="flex items-center gap-3 flex-wrap min-w-0">
                  <span className="text-sm text-white/80">
                    {new Date(a.assessment_date).toLocaleDateString('en-GB', {
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                    })}
                  </span>
                  <span className="text-sm font-semibold text-white">
                    {ASSESSMENT_TYPE_LABELS[a.assessment_type] ?? a.assessment_type}
                  </span>
                  {a.photo_count > 0 && (
                    <span className="text-xs text-white/30">
                      {a.photo_count} photo{a.photo_count !== 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {!readOnly && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEdit(a.id);
                      }}
                      className="text-white/30 hover:text-accent p-1 transition-colors"
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
                        handleDelete(a.id);
                      }}
                      disabled={deleting === a.id}
                      className="text-white/30 hover:text-red-400 p-1 transition-colors disabled:opacity-50"
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
                    className={`w-4 h-4 text-white/30 transition-transform ${expandedId === a.id ? 'rotate-180' : ''}`}
                  >
                    <path fillRule="evenodd" d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>

              {/* Expanded Detail */}
              {expandedId === a.id && expandedAssessment && (
                <div className="border-t border-secondary-muted/50 px-4 py-3 space-y-4 bg-primary-dark/30">
                  {/* Summary */}
                  {expandedAssessment.summary && (
                    <div className="bg-secondary-muted/20 rounded-lg p-3">
                      <div className="text-xs text-white/40 mb-1">Summary</div>
                      <p className="text-sm text-white/80">{expandedAssessment.summary}</p>
                    </div>
                  )}

                  {/* Findings */}
                  <FindingsDisplay findings={expandedAssessment.findings} />

                  {/* Photos */}
                  {expandedAssessment.photos.length > 0 && (
                    <div>
                      <div className="text-xs text-white/40 mb-2">Photos</div>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {expandedAssessment.photos.map((photo) => (
                          <div key={photo.id} className="relative group">
                            {photo.photo_url ? (
                              <img
                                src={photo.photo_url}
                                alt={`${photo.view_type} view`}
                                className="w-full h-32 object-cover rounded-lg border border-secondary-muted/30"
                              />
                            ) : (
                              <div className="w-full h-32 bg-secondary-muted/20 rounded-lg flex items-center justify-center text-white/30 text-xs">
                                No preview
                              </div>
                            )}
                            <span className="absolute bottom-1 left-1 bg-black/60 text-white/80 text-xs px-1.5 py-0.5 rounded">
                              {photo.view_type}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {expandedAssessment.notes && (
                    <div>
                      <div className="text-xs text-white/40 mb-1">Notes</div>
                      <p className="text-xs text-white/60">{expandedAssessment.notes}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <AssessmentForm
          athleteId={athleteId}
          existingAssessment={editAssessment}
          onClose={() => {
            setShowForm(false);
            setEditAssessment(null);
          }}
          onSaved={handleSaved}
        />
      )}
    </div>
  );
}
