'use client';

import type { PowerSample } from '@/lib/metabolicEngine';

interface MetabolicSprintProps {
  sprintNum: number;
  remaining: number;
  samples: PowerSample[];
  livePower: number | null;
}

const SPRINT_LABELS: Record<number, string> = {
  1: 'Sprint 1 — 10s',
  2: 'Sprint 2 — 20s',
  3: 'Sprint 3 — 30s',
};

export function MetabolicSprint({ sprintNum, remaining, samples, livePower }: MetabolicSprintProps) {
  return (
    <div className="text-center space-y-4">
      <div className="text-lg font-heading uppercase tracking-wider text-white">
        {SPRINT_LABELS[sprintNum] || `Sprint ${sprintNum}`}
      </div>

      <div className="text-7xl font-bold font-mono text-red-400 animate-pulse">
        {remaining}
      </div>

      <div className="text-3xl font-bold font-mono text-accent">
        {livePower != null ? `${livePower} W` : '-- W'}
      </div>

      <div className="text-sm text-secondary-muted">
        {samples.length} sample{samples.length !== 1 ? 's' : ''}
      </div>
    </div>
  );
}
