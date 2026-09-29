'use client';

import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import type { VbtProfile } from '@/lib/types';

interface ReportVbtChartProps {
  profile: VbtProfile;
}

export function ReportVbtChart({ profile }: ReportVbtChartProps) {
  const { sets, analysis } = profile;

  const scatterData = sets
    .filter(s => s.mean_velocity_ms != null || s.peak_velocity_ms != null)
    .map(s => ({
      load_kg: s.load_kg,
      velocity_ms: (s.mean_velocity_ms ?? s.peak_velocity_ms)!,
    }))
    .sort((a, b) => a.load_kg - b.load_kg);

  if (scatterData.length < 2 || !analysis) return null;

  const minLoad = Math.min(...scatterData.map(d => d.load_kg));
  const maxLoad = analysis.estimated_1rm_kg
    ? Math.max(analysis.estimated_1rm_kg, ...scatterData.map(d => d.load_kg))
    : Math.max(...scatterData.map(d => d.load_kg)) * 1.2;

  const lineSteps = 50;
  const lineData = Array.from({ length: lineSteps + 1 }, (_, i) => {
    const load = minLoad + ((maxLoad - minLoad) * i) / lineSteps;
    const vel = analysis.slope * load + analysis.intercept;
    return { load_kg: load, regression_velocity: Math.max(vel, 0) };
  });

  const combinedData = lineData.map(ld => {
    const match = scatterData.find(sd => Math.abs(sd.load_kg - ld.load_kg) < 0.5);
    return { ...ld, velocity_ms: match?.velocity_ms ?? undefined };
  });

  for (const sp of scatterData) {
    if (!combinedData.find(d => d.velocity_ms === sp.velocity_ms && Math.abs(d.load_kg - sp.load_kg) < 0.5)) {
      combinedData.push({
        load_kg: sp.load_kg,
        regression_velocity: analysis.slope * sp.load_kg + analysis.intercept,
        velocity_ms: sp.velocity_ms,
      });
    }
  }
  combinedData.sort((a, b) => a.load_kg - b.load_kg);

  const maxVelocity = Math.max(...scatterData.map(d => d.velocity_ms));

  return (
    <ComposedChart
      width={700}
      height={250}
      data={combinedData}
      margin={{ top: 10, right: 20, bottom: 20, left: 10 }}
    >
      <CartesianGrid strokeDasharray="3 3" stroke="#d1d5db" opacity={0.5} />
      <XAxis
        dataKey="load_kg"
        type="number"
        domain={[minLoad * 0.9, maxLoad * 1.05]}
        tick={{ fill: '#333', fontSize: 11 }}
        label={{ value: 'Load (kg)', position: 'bottom', offset: 5, fill: '#555', fontSize: 11 }}
      />
      <YAxis
        domain={[0, Math.ceil(maxVelocity * 10) / 10 + 0.1]}
        tick={{ fill: '#333', fontSize: 11 }}
        label={{ value: 'Velocity (m/s)', angle: -90, position: 'insideLeft', offset: 0, fill: '#555', fontSize: 11 }}
      />
      <ReferenceLine y={analysis.mvt_used_ms} stroke="#ef4444" strokeDasharray="6 3" />
      {analysis.estimated_1rm_kg && (
        <ReferenceLine x={analysis.estimated_1rm_kg} stroke="#22c55e" strokeDasharray="6 3" />
      )}
      <Line type="linear" dataKey="regression_velocity" stroke="#f59e0b" strokeDasharray="6 3" strokeWidth={2} dot={false} isAnimationActive={false} />
      <Scatter dataKey="velocity_ms" fill="#0891b2" stroke="#333" strokeWidth={1.5} r={5} isAnimationActive={false} />
    </ComposedChart>
  );
}
