'use client';

import { useState, useEffect } from 'react';
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { vbtApi } from '@/lib/api';
import type { VbtProfileListItem } from '@/lib/types';

interface VbtRadarProps {
  athleteId: string;
}

interface VbtRadarDataPoint {
  exercise: string;
  label: string;
  zScore: number;
  estimated1rm: number;
  fullMark: 3;
  zoneOuter: 3;
  zoneMid1: 1;
  zoneMid2: 0;
  zoneInner: -1;
}

// Placeholder benchmarks — NOT production data.
// These will be replaced with real population benchmarks when available.
const VBT_PLACEHOLDER_BENCHMARKS: Record<string, { mean: number; sd: number }> = {
  'back squat': { mean: 130, sd: 25 },
  'bench press': { mean: 100, sd: 20 },
  'front squat': { mean: 110, sd: 20 },
  'overhead press': { mean: 65, sd: 15 },
  'trap bar deadlift': { mean: 160, sd: 30 },
  'landmine punch throw': { mean: 40, sd: 10 },
};

function getZColor(z: number): string {
  if (z >= 1) return '#4ade80';
  if (z >= 0) return '#33CBF4';
  if (z >= -1) return '#facc15';
  return '#f87171';
}

export function VbtRadar({ athleteId }: VbtRadarProps) {
  const [data, setData] = useState<VbtRadarDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchProfiles() {
      try {
        setIsLoading(true);
        setError(null);
        const profiles = await vbtApi.listProfiles(athleteId);

        if (cancelled) return;

        // Group by exercise name (case-insensitive), take latest per exercise
        const latestByExercise = new Map<string, VbtProfileListItem>();
        for (const profile of profiles) {
          const key = profile.exercise_name.toLowerCase();
          const existing = latestByExercise.get(key);
          if (
            !existing ||
            new Date(profile.profile_date) > new Date(existing.profile_date)
          ) {
            latestByExercise.set(key, profile);
          }
        }

        // Build radar data points
        const radarData: VbtRadarDataPoint[] = [];
        for (const [exerciseKey, profile] of Array.from(latestByExercise.entries())) {
          const benchmark = VBT_PLACEHOLDER_BENCHMARKS[exerciseKey];
          if (!benchmark) continue;
          const estimated1rm = profile.analysis?.estimated_1rm_kg;
          if (estimated1rm == null) continue;

          const zScore = (estimated1rm - benchmark.mean) / benchmark.sd;

          radarData.push({
            exercise: exerciseKey,
            label: profile.exercise_name,
            zScore: Math.max(-3, Math.min(3, zScore)),
            estimated1rm,
            fullMark: 3 as const,
            zoneOuter: 3 as const,
            zoneMid1: 1 as const,
            zoneMid2: 0 as const,
            zoneInner: -1 as const,
          });
        }

        setData(radarData);
      } catch (err) {
        if (!cancelled) {
          setError('Failed to load VBT profiles');
          console.error(err);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchProfiles();
    return () => {
      cancelled = true;
    };
  }, [athleteId]);

  if (isLoading) {
    return (
      <div className="text-center py-8">
        <div className="inline-block w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin" />
        <p className="mt-2 text-white/60">Loading VBT radar...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-white font-medium mb-4">VBT Estimated 1RM Radar</h3>

      {/* Placeholder benchmark warning */}
      <div className="mb-4 p-3 rounded-lg border border-yellow-500/50 bg-yellow-500/10">
        <p className="text-yellow-300 text-sm">
          Placeholder benchmarks — not production data. Z-scores use estimated population averages and will be replaced with real benchmarks when available.
        </p>
      </div>

      {data.length < 3 ? (
        <div className="text-center py-8">
          <p className="text-white/60">
            Need at least 3 exercises with matching benchmarks for radar chart ({data.length} available).
            Supported exercises: {Object.keys(VBT_PLACEHOLDER_BENCHMARKS).join(', ')}.
          </p>
        </div>
      ) : (
        <>
          {/* Vertical Legend */}
          <div className="flex flex-col gap-2 mb-4 text-sm">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-green-400" />
              <span className="text-white/60">Above average (Z &ge; 1)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-[#33CBF4]" />
              <span className="text-white/60">Average (0 to 1)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-yellow-400" />
              <span className="text-white/60">Below average (-1 to 0)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <span className="text-white/60">Well below (Z &lt; -1)</span>
            </div>
          </div>

          <div className="h-[350px] sm:h-[400px]">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={data} outerRadius="80%">
                {/* Zone band radars */}
                <Radar
                  dataKey="zoneOuter"
                  stroke="none"
                  fill="#4ade80"
                  fillOpacity={0.06}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
                <Radar
                  dataKey="zoneMid1"
                  stroke="none"
                  fill="#33CBF4"
                  fillOpacity={0.08}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
                <Radar
                  dataKey="zoneMid2"
                  stroke="none"
                  fill="#facc15"
                  fillOpacity={0.10}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />
                <Radar
                  dataKey="zoneInner"
                  stroke="none"
                  fill="#f87171"
                  fillOpacity={0.12}
                  dot={false}
                  activeDot={false}
                  isAnimationActive={false}
                />

                <PolarGrid stroke="#2D5585" />
                <PolarAngleAxis
                  dataKey="label"
                  tick={{ fill: '#ffffff99', fontSize: 11 }}
                />
                <PolarRadiusAxis
                  domain={[-3, 3]}
                  tick={{ fill: '#ffffff66', fontSize: 10 }}
                  tickCount={7}
                  axisLine={false}
                />
                <Tooltip
                  content={({ active, payload, label }: any) => {
                    if (!active || !payload || payload.length === 0) return null;
                    const zEntry = payload.find((p: any) => p.dataKey === 'zScore');
                    if (!zEntry) return null;
                    const z = zEntry.value as number;
                    const dp = zEntry.payload as VbtRadarDataPoint;
                    const formatted = `${z >= 0 ? '+' : ''}${z.toFixed(2)}`;
                    return (
                      <div
                        style={{
                          backgroundColor: '#07083D',
                          border: '1px solid #2D5585',
                          borderRadius: '8px',
                          padding: '8px 12px',
                        }}
                      >
                        <p style={{ color: '#ffffff99', marginBottom: 4 }}>{label}</p>
                        <p style={{ color: getZColor(z), fontWeight: 600 }}>
                          Z-Score: {formatted}
                        </p>
                        <p style={{ color: '#ffffffcc', fontSize: 12 }}>
                          Est. 1RM: {dp.estimated1rm.toFixed(1)} kg
                        </p>
                      </div>
                    );
                  }}
                />
                {/* Main data radar */}
                <Radar
                  name="Z-Score"
                  dataKey="zScore"
                  stroke="#33CBF4"
                  fill="#33CBF4"
                  fillOpacity={0.25}
                  strokeWidth={2}
                  dot={(props: any) => {
                    const { cx, cy, payload, value } = props;
                    const z = typeof value === 'number' ? value : payload?.zScore;
                    if (z == null || cx == null || cy == null) return <circle r={0} />;
                    const color = getZColor(z);
                    return (
                      <circle
                        key={payload?.exercise || `${cx}-${cy}`}
                        cx={cx}
                        cy={cy}
                        r={6}
                        fill={color}
                        stroke="white"
                        strokeWidth={2}
                      />
                    );
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
