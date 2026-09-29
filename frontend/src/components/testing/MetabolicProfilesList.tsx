'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { metabolicApi } from '@/lib/api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts';
import { calculateMetabolicProfile, sumWatts, generateInsights } from '@/lib/metabolicEngine';
import type { MetabolicProfileListItem, MetabolicProfile } from '@/lib/types';

interface MetabolicProfilesListProps {
  athleteId: string;
  refreshKey: number;
  readOnly?: boolean;
}

function ProfileDetail({ profile }: { profile: MetabolicProfile }) {
  const isBle = profile.data_source === 'ble';

  // Compute results client-side for display
  const mechWork: [number, number, number] = useMemo(() => {
    if (!isBle) {
      return [
        (profile.sprint_1_avg_power_w ?? 0) * 10,
        (profile.sprint_2_avg_power_w ?? 0) * 10,
        (profile.sprint_3_avg_power_w ?? 0) * 10,
      ];
    }
    return [
      profile.mech_work_sprint_1_j ?? 0,
      profile.mech_work_sprint_2_j ?? 0,
      profile.mech_work_sprint_3_j ?? 0,
    ];
  }, [profile, isBle]);

  const energyData = [
    {
      name: 'Sprint 1',
      alactic: Math.max(0, profile.alactic_1_j ?? 0),
      glycolytic: Math.max(0, profile.glycolytic_1_j ?? 0),
    },
    {
      name: 'Sprint 2',
      alactic: Math.max(0, profile.alactic_2_j ?? 0),
      glycolytic: Math.max(0, profile.glycolytic_2_j ?? 0),
    },
    {
      name: 'Sprint 3',
      alactic: Math.max(0, profile.alactic_3_j ?? 0),
      glycolytic: Math.max(0, profile.glycolytic_3_j ?? 0),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Key metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {[
          { label: 'Alactic Capacity', value: profile.alactic_capacity_j?.toFixed(0), unit: 'J' },
          { label: 'Max Glycolytic Power', value: profile.max_glycolytic_power_w?.toFixed(1), unit: 'W' },
          { label: 'Anaerobic Cost', value: profile.anaerobic_cost?.toFixed(3), unit: '' },
          { label: 'Fatigue Slope', value: profile.fatigue_slope_w?.toFixed(1), unit: 'W' },
        ].map(item => (
          <div key={item.label} className="bg-primary-dark/50 rounded p-2 text-center">
            <div className="text-[10px] text-white/30 uppercase font-heading tracking-wider">{item.label}</div>
            <div className="text-sm font-bold mt-0.5">
              {item.value ?? 'N/A'}
              {item.unit && <span className="text-xs text-white/30 font-normal ml-0.5">{item.unit}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Lactate values */}
      <div className="flex gap-4 text-xs text-white/50">
        <span>Resting: {profile.resting_lactate_mmol} mM</span>
        <span>La1: {profile.la_peak_1_mmol} mM</span>
        <span>La2: {profile.la_peak_2_mmol} mM</span>
        <span>La3: {profile.la_peak_3_mmol} mM</span>
      </div>

      {/* Energy breakdown chart */}
      <div>
        <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Energy Breakdown</div>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={energyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" strokeOpacity={0.3} />
              <XAxis dataKey="name" tick={{ fill: '#2074AA', fontSize: 10 }} />
              <YAxis tick={{ fill: '#2074AA', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#07083D', border: '1px solid #2D5585', borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="alactic" stackId="e" fill="#33CBF4" name="Alactic (J)" />
              <Bar dataKey="glycolytic" stackId="e" fill="#2074AA" radius={[4, 4, 0, 0]} name="Glycolytic (J)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Mech work */}
      <div className="flex gap-4 text-xs text-white/40">
        <span>Work 1: {mechWork[0].toFixed(0)} J</span>
        <span>Work 2: {mechWork[1].toFixed(0)} J</span>
        <span>Work 3: {mechWork[2].toFixed(0)} J</span>
      </div>

      {profile.notes && <p className="text-xs text-white/40">{profile.notes}</p>}
    </div>
  );
}

export function MetabolicProfilesList({ athleteId, refreshKey, readOnly }: MetabolicProfilesListProps) {
  const [profiles, setProfiles] = useState<MetabolicProfileListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [expandedDetail, setExpandedDetail] = useState<MetabolicProfile | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadProfiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await metabolicApi.listProfiles(athleteId);
      setProfiles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load profiles');
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadProfiles();
  }, [loadProfiles, refreshKey]);

  async function handleExpand(profileId: string) {
    if (expandedId === profileId) {
      setExpandedId(null);
      setExpandedDetail(null);
      return;
    }
    try {
      const full = await metabolicApi.getProfile(profileId);
      setExpandedDetail(full);
      setExpandedId(profileId);
    } catch {
      // Silently fail
    }
  }

  async function handleDelete(profileId: string) {
    if (!confirm('Delete this metabolic profile?')) return;
    setDeleting(profileId);
    try {
      await metabolicApi.deleteProfile(profileId);
      setProfiles(prev => prev.filter(p => p.id !== profileId));
      if (expandedId === profileId) {
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

  if (profiles.length === 0) {
    return <p className="text-center text-white/30 text-sm py-8">No metabolic profiles yet</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm text-white/40">
        {profiles.length} profile{profiles.length !== 1 ? 's' : ''}
      </p>
      {profiles.map(p => (
        <div key={p.id} className="border border-secondary-muted/50 rounded-lg overflow-hidden">
          <div
            className="flex items-center justify-between px-4 py-3 min-h-[44px] cursor-pointer hover:bg-secondary-muted/20 active:bg-secondary-muted/30 transition-colors"
            onClick={() => handleExpand(p.id)}
          >
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-sm text-white/80">
                {new Date(p.test_date).toLocaleDateString('en-GB', {
                  day: 'numeric', month: 'short', year: 'numeric',
                })}
              </span>
              <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${
                p.data_source === 'ble' ? 'bg-cyan-500/20 text-cyan-400' : 'bg-amber-500/20 text-amber-400'
              }`}>
                {p.data_source === 'ble' ? 'BLE' : 'Manual'}
              </span>
              <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-blue-500/20 text-blue-400">
                {p.body_mass_kg} kg
              </span>
              {p.alactic_capacity_j != null && (
                <span className="text-sm text-white">
                  Alactic: {Math.round(p.alactic_capacity_j)} J
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {!readOnly && (
                <button
                  onClick={e => { e.stopPropagation(); handleDelete(p.id); }}
                  disabled={deleting === p.id}
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
                className={`w-4 h-4 text-white/30 transition-transform ${expandedId === p.id ? 'rotate-180' : ''}`}
              >
                <path fillRule="evenodd" d="M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94l2.72-2.72a.75.75 0 1 1 1.06 1.06l-3.25 3.25a.75.75 0 0 1-1.06 0L4.22 7.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
              </svg>
            </div>
          </div>

          {expandedId === p.id && expandedDetail && (
            <div className="border-t border-secondary-muted/50 px-4 py-3 bg-primary-dark/30">
              <ProfileDetail profile={expandedDetail} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
