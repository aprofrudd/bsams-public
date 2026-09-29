'use client';

import { useState } from 'react';
import {
  ComposedChart,
  Scatter,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { LactateTest, GasAnalysisStageSummary } from '@/lib/types';
import { findCrossoverIntensity } from '@/lib/cpetAnalysis';

interface LactateChartProps {
  test: LactateTest;
  gasAnalysis?: {
    stage_averages: GasAnalysisStageSummary[];
    fat_max_intensity: number | null;
  } | null;
}

type OverlayKey = 'vo2' | 've' | 'bf' | 'fat' | 'cho' | 'ee';

const OVERLAY_CONFIG: Record<OverlayKey, { label: string; key: keyof GasAnalysisStageSummary; color: string; unit: string }> = {
  vo2: { label: 'VO2', key: 'avg_vo2_ml_kg_min', color: '#a855f7', unit: 'ml/kg/min' },
  ve: { label: 'VE', key: 'avg_ve_l_min', color: '#14b8a6', unit: 'L/min' },
  bf: { label: 'BF', key: 'avg_bf_per_min', color: '#ec4899', unit: '/min' },
  fat: { label: 'FAT', key: 'avg_fat_gh', color: '#f97316', unit: 'g/h' },
  cho: { label: 'CHO', key: 'avg_cho_gh', color: '#84cc16', unit: 'g/h' },
  ee: { label: 'EE', key: 'avg_ee_kcal_h', color: '#eab308', unit: 'kcal/h' },
};

const MAX_OVERLAYS = 2;

export function LactateChart({ test, gasAnalysis }: LactateChartProps) {
  const [activeOverlays, setActiveOverlays] = useState<OverlayKey[]>([]);
  const { stages, analysis } = test;
  const unitLabel = test.test_type === 'running' ? 'km/h' : 'W';

  // Build scatter data
  const lactatePoints = stages
    .filter((s) => s.intensity_value != null && s.blood_lactate_mmol != null)
    .map((s) => ({ intensity: s.intensity_value, lactate: s.blood_lactate_mmol }))
    .sort((a, b) => a.intensity - b.intensity);

  const hrPoints = stages
    .filter((s) => s.intensity_value != null && s.heart_rate_bpm != null)
    .map((s) => ({ intensity: s.intensity_value, hr: s.heart_rate_bpm! }))
    .sort((a, b) => a.intensity - b.intensity);

  if (lactatePoints.length < 2) {
    return (
      <p className="text-sm text-white/40 text-center py-4">
        Need at least 2 stages with data for chart
      </p>
    );
  }

  // Build segment regression lines (if analysis exists)
  const segmentLines: { data: { intensity: number; lactate: number }[]; color: string }[] = [];
  if (analysis?.segments?.length === 3) {
    const colors = ['#22c55e', '#eab308', '#ef4444']; // green, yellow, red
    analysis.segments.forEach((seg, idx) => {
      const points: { intensity: number; lactate: number }[] = [];
      const range = seg.end_x - seg.start_x;
      const steps = Math.max(20, 2);
      for (let i = 0; i <= steps; i++) {
        const x = seg.start_x + (range * i) / steps;
        points.push({ intensity: x, lactate: seg.slope * x + seg.intercept });
      }
      segmentLines.push({ data: points, color: colors[idx] });
    });
  }

  // Build overlay data from gas analysis stage averages
  const overlayData: Record<OverlayKey, { intensity: number; value: number }[]> = {
    vo2: [], ve: [], bf: [], fat: [], cho: [], ee: [],
  };

  if (gasAnalysis?.stage_averages) {
    for (const sa of gasAnalysis.stage_averages) {
      if (sa.intensity_value == null) continue;
      for (const [key, config] of Object.entries(OVERLAY_CONFIG)) {
        const val = sa[config.key];
        if (val != null) {
          overlayData[key as OverlayKey].push({ intensity: sa.intensity_value, value: val as number });
        }
      }
    }
  }

  // Determine axis domains with clean intervals
  const allIntensities = lactatePoints.map((p) => p.intensity);
  const minX = Math.min(...allIntensities);
  const maxX = Math.max(...allIntensities);
  const xFloor = Math.floor(minX);
  const xCeil = Math.ceil(maxX);
  const xTicks: number[] = [];
  for (let v = xFloor; v <= xCeil; v++) xTicks.push(v);

  const allLactates = lactatePoints.map((p) => p.lactate);
  const maxLactate = Math.max(...allLactates);

  const allHr = hrPoints.map((p) => p.hr);
  const minHr = allHr.length > 0 ? Math.min(...allHr) : 0;
  const maxHr = allHr.length > 0 ? Math.max(...allHr) : 200;
  const hrFloor = Math.floor(minHr / 10) * 10;
  const hrCeil = Math.ceil(maxHr / 10) * 10;
  const hrTicks: number[] = [];
  for (let v = hrFloor; v <= hrCeil; v += 10) hrTicks.push(v);

  // Fat max and crossover reference lines
  const fatMaxIntensity = gasAnalysis?.fat_max_intensity;
  const crossoverIntensity = gasAnalysis?.stage_averages
    ? findCrossoverIntensity(gasAnalysis.stage_averages)
    : null;

  // Toggle overlay
  function toggleOverlay(key: OverlayKey) {
    setActiveOverlays((prev) => {
      if (prev.includes(key)) return prev.filter((k) => k !== key);
      if (prev.length >= MAX_OVERLAYS) return [...prev.slice(1), key];
      return [...prev, key];
    });
  }

  // Available overlays (only show toggles that have data)
  const availableOverlays = (Object.keys(OVERLAY_CONFIG) as OverlayKey[]).filter(
    (k) => overlayData[k].length > 0
  );

  return (
    <div>
      {/* Overlay toggles */}
      {availableOverlays.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {availableOverlays.map((key) => {
            const config = OVERLAY_CONFIG[key];
            const active = activeOverlays.includes(key);
            return (
              <button
                key={key}
                type="button"
                onClick={() => toggleOverlay(key)}
                className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                  active
                    ? 'border-current bg-current/10'
                    : 'border-secondary-muted/50 text-white/30 hover:text-white/50'
                }`}
                style={active ? { color: config.color, borderColor: config.color } : undefined}
              >
                {config.label}
              </button>
            );
          })}
          <span className="text-[10px] text-white/20 self-center ml-1">max {MAX_OVERLAYS}</span>
        </div>
      )}

      <div className="h-[240px] sm:h-[300px] md:h-[350px] overflow-hidden">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart margin={{ top: 25, right: 50, bottom: 20, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" opacity={0.3} />
          <XAxis
            dataKey="intensity"
            type="number"
            domain={[xFloor, xCeil]}
            ticks={xTicks}
            tick={{ fill: '#ffffff80', fontSize: 11 }}
            allowDuplicatedCategory={false}
            label={{
              value: `Speed (${unitLabel})`,
              position: 'bottom',
              offset: 5,
              fill: '#ffffff60',
              fontSize: 11,
            }}
          />
          <YAxis
            yAxisId="lactate"
            domain={[0, Math.ceil(maxLactate) + 1]}
            tick={{ fill: '#ffffff80', fontSize: 11 }}
            label={{
              value: 'Lactate (mmol/L)',
              angle: -90,
              position: 'insideLeft',
              offset: 0,
              fill: '#ffffff60',
              fontSize: 11,
            }}
          />
          {hrPoints.length > 0 && (
            <YAxis
              yAxisId="hr"
              orientation="right"
              domain={[hrFloor, hrCeil]}
              ticks={hrTicks}
              tick={{ fill: '#f59e0b80', fontSize: 11 }}
              label={{
                value: 'HR (bpm)',
                angle: 90,
                position: 'insideRight',
                offset: 0,
                fill: '#f59e0b80',
                fontSize: 11,
              }}
            />
          )}

          {/* Dynamic overlay Y-axes */}
          {activeOverlays.map((key, idx) => {
            const config = OVERLAY_CONFIG[key];
            const data = overlayData[key];
            const vals = data.map((d) => d.value);
            const maxVal = Math.max(...vals);
            return (
              <YAxis
                key={`overlay-axis-${key}`}
                yAxisId={`overlay-${key}`}
                orientation={idx === 0 ? 'right' : 'right'}
                domain={[0, Math.ceil(maxVal * 1.1)]}
                tick={{ fill: `${config.color}80`, fontSize: 9 }}
                hide={true}
              />
            );
          })}

          <Tooltip
            contentStyle={{
              backgroundColor: '#07083D',
              border: '1px solid #2D5585',
              borderRadius: 8,
              fontSize: 12,
            }}
            labelFormatter={(val) => `${Number(val).toFixed(1)} ${unitLabel}`}
            formatter={(value: number, name: string) => {
              if (name === 'lactate') return [`${value.toFixed(2)} mmol/L`, 'Lactate'];
              if (name === 'hr') return [`${value} bpm`, 'Heart Rate'];
              // Gas overlay tooltips
              for (const [key, config] of Object.entries(OVERLAY_CONFIG)) {
                if (name === `overlay-${key}`) {
                  return [`${value.toFixed(1)} ${config.unit}`, config.label];
                }
              }
              return [value, name];
            }}
          />

          {/* LT1 vertical reference line */}
          {test.lt1_value != null && (
            <ReferenceLine
              x={test.lt1_value}
              yAxisId="lactate"
              stroke="#22c55e"
              strokeDasharray="6 3"
              label={{
                value: 'LT1',
                position: 'insideTopRight',
                fill: '#22c55e',
                fontSize: 10,
                fontWeight: 600,
              }}
            />
          )}

          {/* LT2 vertical reference line */}
          {test.lt2_value != null && (
            <ReferenceLine
              x={test.lt2_value}
              yAxisId="lactate"
              stroke="#ef4444"
              strokeDasharray="6 3"
              label={{
                value: 'LT2',
                position: 'insideTopRight',
                fill: '#ef4444',
                fontSize: 10,
                fontWeight: 600,
              }}
            />
          )}

          {/* Fat Max reference line */}
          {fatMaxIntensity != null && (
            <ReferenceLine
              x={fatMaxIntensity}
              yAxisId="lactate"
              stroke="#f97316"
              strokeDasharray="4 4"
              label={{
                value: 'FatMax',
                position: 'insideTopLeft',
                fill: '#f97316',
                fontSize: 9,
                fontWeight: 600,
              }}
            />
          )}

          {/* Crossover reference line */}
          {crossoverIntensity != null && (
            <ReferenceLine
              x={crossoverIntensity}
              yAxisId="lactate"
              stroke="#eab308"
              strokeDasharray="4 4"
              label={{
                value: 'Crossover',
                position: 'insideTopLeft',
                fill: '#eab308',
                fontSize: 9,
                fontWeight: 600,
              }}
            />
          )}

          {/* Piecewise regression segment lines */}
          {segmentLines.map((seg, idx) => (
            <Line
              key={`seg-${idx}`}
              data={seg.data}
              type="linear"
              dataKey="lactate"
              stroke={seg.color}
              strokeWidth={2}
              dot={false}
              activeDot={false}
              yAxisId="lactate"
              isAnimationActive={false}
            />
          ))}

          {/* Gas overlay lines + scatter */}
          {activeOverlays.map((key) => {
            const config = OVERLAY_CONFIG[key];
            const data = overlayData[key].sort((a, b) => a.intensity - b.intensity);
            return [
              <Line
                key={`overlay-line-${key}`}
                data={data}
                type="monotone"
                dataKey="value"
                name={`overlay-${key}`}
                stroke={config.color}
                strokeWidth={1.5}
                dot={false}
                activeDot={false}
                yAxisId={`overlay-${key}`}
                isAnimationActive={false}
              />,
              <Scatter
                key={`overlay-scatter-${key}`}
                data={data}
                dataKey="value"
                name={`overlay-${key}`}
                fill={config.color}
                stroke="#ffffff"
                strokeWidth={1}
                yAxisId={`overlay-${key}`}
                r={3}
                isAnimationActive={false}
              />,
            ];
          })}

          {/* Lactate connecting line (behind scatter) */}
          <Line
            data={lactatePoints}
            type="monotone"
            dataKey="lactate"
            stroke="#33CBF4"
            strokeWidth={1.5}
            dot={false}
            activeDot={false}
            yAxisId="lactate"
            isAnimationActive={false}
          />

          {/* HR connecting line (behind scatter) */}
          {hrPoints.length > 1 && (
            <Line
              data={hrPoints}
              type="monotone"
              dataKey="hr"
              stroke="#f59e0b"
              strokeWidth={1.5}
              dot={false}
              activeDot={false}
              yAxisId="hr"
              isAnimationActive={false}
            />
          )}

          {/* HR scatter */}
          {hrPoints.length > 0 && (
            <Scatter
              data={hrPoints}
              dataKey="hr"
              fill="#f59e0b"
              stroke="#ffffff"
              strokeWidth={1}
              yAxisId="hr"
              r={4}
              isAnimationActive={false}
            />
          )}

          {/* Lactate scatter */}
          <Scatter
            data={lactatePoints}
            dataKey="lactate"
            fill="#33CBF4"
            stroke="#ffffff"
            strokeWidth={1.5}
            yAxisId="lactate"
            r={5}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
      </div>
    </div>
  );
}
