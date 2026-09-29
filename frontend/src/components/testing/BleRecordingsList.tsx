'use client';

import { useState, useEffect, useCallback } from 'react';
import { airBikeRecordingApi } from '@/lib/api';
import { BleRecordingDetail } from './BleRecordingDetail';
import type { AirBikeRecordingListItem, AirBikeRecording } from '@/lib/types';

interface BleRecordingsListProps {
  athleteId: string;
  refreshKey: number;
  readOnly?: boolean;
}

export function BleRecordingsList({ athleteId, refreshKey, readOnly }: BleRecordingsListProps) {
  const [recordings, setRecordings] = useState<AirBikeRecordingListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<AirBikeRecording | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadRecordings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await airBikeRecordingApi.listRecordings(athleteId);
      setRecordings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load recordings');
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadRecordings();
  }, [loadRecordings, refreshKey]);

  async function handleExpand(recordingId: string) {
    if (expandedId === recordingId) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    try {
      const full = await airBikeRecordingApi.getRecording(recordingId);
      setExpandedDetail(full);
      setExpandedId(recordingId);
    } catch {
      // Silently fail expand
    }
  }

  async function handleDelete(recordingId: string) {
    if (!confirm('Delete this recording?')) return;
    setDeleting(recordingId);
    try {
      await airBikeRecordingApi.deleteRecording(recordingId);
      setRecordings(prev => prev.filter(r => r.id !== recordingId));
      if (expandedId === recordingId) {
        setExpandedId(null);
        setExpandedDetail(null);
      }
    } catch {
      // Silently fail
    } finally {
      setDeleting(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="inline-block w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) return <p className="text-red-400 text-sm">{error}</p>;

  if (recordings.length === 0) {
    return (
      <p className="text-center text-white/30 text-sm py-8">No saved recordings yet</p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-white/40">
        {recordings.length} recording{recordings.length !== 1 ? 's' : ''}
      </p>
      {recordings.map(r => (
        <div key={r.id} className="border border-secondary-muted/50 rounded-lg overflow-hidden">
          <div
            className="flex items-center justify-between px-4 py-3 min-h-[44px] cursor-pointer hover:bg-secondary-muted/20 active:bg-secondary-muted/30 transition-colors"
            onClick={() => handleExpand(r.id)}
          >
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-sm text-white/80">
                {new Date(r.test_date).toLocaleDateString('en-GB', {
                  day: 'numeric', month: 'short', year: 'numeric',
                })}
              </span>
              <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-cyan-500/20 text-cyan-400">
                {r.duration_s}s
              </span>
              {r.avg_power_w != null && (
                <span className="text-sm text-white">
                  Avg: {Math.round(r.avg_power_w)} W
                </span>
              )}
              {r.peak_power_w != null && (
                <span className="text-sm text-white/60">
                  Peak: {Math.round(r.peak_power_w)} W
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {!readOnly && (
                <button
                  onClick={e => { e.stopPropagation(); handleDelete(r.id); }}
                  disabled={deleting === r.id}
                  className="text-white/30 hover:text-red-400 p-2 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors disabled:opacity-50"
                  title="Delete"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" className="w-4 h-4">
                    <path fillRule="evenodd" d="M5 3.25V4H2.75a.75.75 0 0 0 0 1.5h.3l.815 8.15A1.5 1.5 0 0 0 5.357 15h5.285a1.5 1.5 0 0 0 1.493-1.35l.815-8.15h.3a.75.75 0 0 0 0-1.5H11v-.75A2.25 2.25 0 0 0 8.75 1h-1.5A2.25 2.25 0 0 0 5 3.25Zm2.25-.75a.75.75 0 0 0-.75.75V4h3v-.75a.75.75 0 0 0-.75-.75h-1.5ZM6.05 6a.75.75 0 0 1 .787.713l.275 5.5a.75.75 0 0 1-1.498.075l-.275-5.5A.75.75 0 0 1 6.05 6Zm3.9 0a.75.75 0 0 1 .712.787l-.275 5.5a.75.75 0 0 1-1.498-.075l.275-5.5a.75.75 0 0 1 .786-.711Z" clipRule="evenodd" />
                  </svg>
                </button>
              )}
              <svg
                xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor"
                className={`w-4 h-4 text-white/30 transition-transform ${expandedId === r.id ? 'rotate-180' : ''}`}
              >
                <path fillRule="evenodd" d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
              </svg>
            </div>
          </div>

          {expandedId === r.id && expandedDetail && (
            <div className="border-t border-secondary-muted/50 px-4 py-3 bg-primary-dark/30">
              <BleRecordingDetail recording={expandedDetail} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
