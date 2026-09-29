'use client';

import { useState, useEffect, useCallback } from 'react';
import { trainingApi, wellnessApi } from '@/lib/api';
import type { TrainingLoadAnalysis, WellnessEntry } from '@/lib/types';

interface ReadinessIndicatorProps {
  athleteId: string;
  dataVersion?: number;
}

type ReadinessLevel = 'green' | 'amber' | 'red' | 'unknown';

function getReadinessLevel(
  acwr: number | null,
  latestWellness: WellnessEntry | null,
): ReadinessLevel {
  if (acwr === null && !latestWellness) return 'unknown';

  let score = 0;
  let factors = 0;

  // ACWR scoring
  if (acwr !== null) {
    factors++;
    if (acwr >= 0.8 && acwr <= 1.3) score += 2; // Optimal
    else if (acwr > 1.5 || acwr < 0.5) score += 0; // High risk
    else score += 1; // Moderate
  }

  // Wellness scoring using Hooper Index (4-28, lower is better)
  if (latestWellness) {
    factors++;
    const hi = latestWellness.hooper_index;
    if (hi <= 10) score += 2;       // Good recovery
    else if (hi <= 16) score += 1;  // Moderate
    else score += 0;                // Poor recovery
  }

  if (factors === 0) return 'unknown';
  const avg = score / factors;
  if (avg >= 1.5) return 'green';
  if (avg >= 0.5) return 'amber';
  return 'red';
}

const READINESS_CONFIG: Record<ReadinessLevel, { label: string; dotColor: string; textColor: string }> = {
  green: { label: 'Good to Go', dotColor: 'bg-green-400', textColor: 'text-green-400' },
  amber: { label: 'Caution', dotColor: 'bg-yellow-400', textColor: 'text-yellow-400' },
  red: { label: 'High Risk', dotColor: 'bg-red-400', textColor: 'text-red-400' },
  unknown: { label: 'No Data', dotColor: 'bg-white/30', textColor: 'text-white/60' },
};

function getAcwrLabel(acwr: number): string {
  if (acwr >= 0.8 && acwr <= 1.3) return 'Optimal';
  if (acwr > 1.5) return 'Danger';
  if (acwr < 0.5) return 'Low';
  return 'Caution';
}

function getHooperLabel(hi: number): string {
  if (hi <= 10) return 'Good';
  if (hi <= 16) return 'Moderate';
  return 'Poor';
}

function getAcwrValueColor(acwr: number): string {
  if (acwr >= 0.8 && acwr <= 1.3) return 'text-green-400';
  if (acwr > 1.5 || acwr < 0.5) return 'text-red-400';
  return 'text-yellow-400';
}

function getHooperValueColor(hi: number): string {
  if (hi <= 10) return 'text-green-400';
  if (hi <= 16) return 'text-yellow-400';
  return 'text-red-400';
}

export function ReadinessIndicator({ athleteId, dataVersion }: ReadinessIndicatorProps) {
  const [loadData, setLoadData] = useState<TrainingLoadAnalysis | null>(null);
  const [latestWellness, setLatestWellness] = useState<WellnessEntry | null>(null);
  const [loading, setLoading] = useState(true);

  const loadReadiness = useCallback(async () => {
    try {
      setLoading(true);
      const [load, wellness] = await Promise.all([
        trainingApi.getLoadAnalysis(athleteId, 28).catch(() => null),
        wellnessApi.listEntries(athleteId).catch(() => []),
      ]);
      setLoadData(load);
      setLatestWellness(wellness.length > 0 ? wellness[0] : null);
    } catch {
      // Silently handle - indicator is supplementary
    } finally {
      setLoading(false);
    }
  }, [athleteId]);

  useEffect(() => {
    loadReadiness();
  }, [loadReadiness, dataVersion]);

  if (loading) {
    return (
      <div className="flex items-center gap-3 bg-secondary-muted/10 rounded-lg px-4 py-2 animate-pulse">
        <div className="w-2.5 h-2.5 rounded-full bg-white/20" />
        <span className="text-xs text-white/40">Loading readiness...</span>
      </div>
    );
  }

  const level = getReadinessLevel(loadData?.acwr ?? null, latestWellness);
  const config = READINESS_CONFIG[level];

  return (
    <div className="flex items-center gap-3 bg-secondary-muted/10 rounded-lg px-4 py-2 flex-wrap">
      {/* Traffic light dot + label */}
      <div className="flex items-center gap-2">
        <div className={`w-2.5 h-2.5 rounded-full ${config.dotColor} shrink-0`} />
        <span className={`text-sm font-semibold ${config.textColor}`}>{config.label}</span>
      </div>

      {/* Separator */}
      <div className="w-px h-4 bg-secondary-muted/50 hidden sm:block" />

      {/* ACWR */}
      {loadData?.acwr != null && (
        <span className="text-xs text-white/60">
          ACWR: <span className={`${getAcwrValueColor(loadData.acwr)} font-medium`}>{loadData.acwr}</span>
          <span className="text-white/40 ml-1">({getAcwrLabel(loadData.acwr)})</span>
        </span>
      )}

      {/* Hooper Index */}
      {latestWellness && (
        <>
          {loadData?.acwr != null && <div className="w-px h-3 bg-secondary-muted/30 hidden sm:block" />}
          <span className="text-xs text-white/60">
            HI: <span className={`${getHooperValueColor(latestWellness.hooper_index)} font-medium`}>{latestWellness.hooper_index}</span>
            <span className="text-white/40 ml-1">({getHooperLabel(latestWellness.hooper_index)})</span>
          </span>
        </>
      )}
    </div>
  );
}
