'use client';

import { useMemo, useState, useCallback } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, LineChart, Line, ScatterChart, Scatter,
  ComposedChart,
} from 'recharts';
import {
  calculateMetabolicProfile, sumWatts, generateInsights,
} from '@/lib/metabolicEngine';
import type { MetabolicResult, MetabolicInsight, PowerSample } from '@/lib/metabolicEngine';
import { metabolicApi } from '@/lib/api';
import type { MetabolicProfileCreate } from '@/lib/types';

interface MetabolicResultsProps {
  bodyMassKg: number;
  restingLactate: number;
  laPeaks: [number, number, number];
  dataSource: 'ble' | 'manual';
  sprint1Samples: PowerSample[];
  sprint2Samples: PowerSample[];
  sprint3Samples: PowerSample[];
  athleteId: string;
  onSaved: () => void;
  onReset: () => void;
}

const INSIGHT_COLORS: Record<string, string> = {
  alactic: 'border-l-cyan-400',
  glycolytic: 'border-l-red-400',
  fatigue: 'border-l-amber-400',
  dominance: 'border-l-cyan-400',
  lactate: 'border-l-red-400',
  training: 'border-l-cyan-400',
};

const INSIGHT_TAG_COLORS: Record<string, string> = {
  alactic: 'bg-cyan-400/15 text-cyan-400',
  glycolytic: 'bg-red-400/15 text-red-400',
  fatigue: 'bg-amber-400/15 text-amber-400',
  dominance: 'bg-cyan-400/15 text-cyan-400',
  lactate: 'bg-red-400/15 text-red-400',
  training: 'bg-cyan-400/15 text-cyan-400',
};

export function MetabolicResults({
  bodyMassKg, restingLactate, laPeaks, dataSource,
  sprint1Samples, sprint2Samples, sprint3Samples,
  athleteId, onSaved, onReset,
}: MetabolicResultsProps) {
  const [trim1, setTrim1] = useState(0);
  const [trim2, setTrim2] = useState(0);
  const [trim3, setTrim3] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const isBle = dataSource === 'ble';
  const isManual = dataSource === 'manual';

  const mechWork = useMemo((): [number, number, number] => {
    if (isManual) {
      // For manual mode, samples contain a single entry with avg power
      const p1 = sprint1Samples[0]?.watts ?? 0;
      const p2 = sprint2Samples[0]?.watts ?? 0;
      const p3 = sprint3Samples[0]?.watts ?? 0;
      return [p1 * 10, p2 * 10, p3 * 10];
    }
    return [
      sumWatts(sprint1Samples, 0, 10, trim1),
      sumWatts(sprint2Samples, 10, 20, trim2),
      sumWatts(sprint3Samples, 20, 30, trim3),
    ];
  }, [sprint1Samples, sprint2Samples, sprint3Samples, trim1, trim2, trim3, isManual]);

  const result = useMemo((): MetabolicResult => {
    return calculateMetabolicProfile(bodyMassKg, restingLactate, laPeaks, mechWork);
  }, [bodyMassKg, restingLactate, laPeaks, mechWork]);

  const insights = useMemo((): MetabolicInsight[] => {
    return generateInsights(result, bodyMassKg);
  }, [result, bodyMassKg]);

  // Chart data
  const workChartData = [
    { name: 'Sprint 1\n(0-10s)', work: result.mechWork[0] },
    { name: 'Sprint 2\n(10-20s)', work: result.mechWork[1] },
    { name: 'Sprint 3\n(20-30s)', work: result.mechWork[2] },
  ];

  const energyChartData = [
    { name: 'Sprint 1', alactic: Math.max(0, result.alactic[0]), glycolytic: Math.max(0, result.glycolytic[0]) },
    { name: 'Sprint 2', alactic: Math.max(0, result.alactic[1]), glycolytic: Math.max(0, result.glycolytic[1]) },
    { name: 'Sprint 3', alactic: Math.max(0, result.alactic[2]), glycolytic: Math.max(0, result.glycolytic[2]) },
  ];

  const summaryChartData = [
    { name: 'Alactic Capacity (J)', value: result.alacticCapacity },
    { name: 'Max Glycolytic Power (W)', value: result.maxGlycolyticPower ?? 0 },
    { name: 'Fatigue Slope (W)', value: result.fatigueSlope ?? 0 },
  ];

  // Power decay chart (BLE only)
  const powerDecayData = useMemo(() => {
    if (isManual) return [];
    const toPoints = (samples: PowerSample[], trimS: number) =>
      samples.filter(s => s.elapsed_ms >= trimS * 1000).map(s => ({ x: s.elapsed_ms / 1000, y: s.watts }));
    return [
      { label: 'Sprint 1', color: '#33CBF4', data: toPoints(sprint1Samples, trim1) },
      { label: 'Sprint 2', color: '#2074AA', data: toPoints(sprint2Samples, trim2) },
      { label: 'Sprint 3', color: '#2D5585', data: toPoints(sprint3Samples, trim3) },
    ];
  }, [sprint1Samples, sprint2Samples, sprint3Samples, trim1, trim2, trim3, isManual]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveError(null);
    try {
      const today = new Date().toISOString().split('T')[0];
      const data: MetabolicProfileCreate = {
        test_date: today,
        body_mass_kg: bodyMassKg,
        data_source: dataSource,
        resting_lactate_mmol: restingLactate,
        la_peak_1_mmol: laPeaks[0],
        la_peak_2_mmol: laPeaks[1],
        la_peak_3_mmol: laPeaks[2],
        trim_1_s: trim1,
        trim_2_s: trim2,
        trim_3_s: trim3,
        notes: undefined,
      };

      if (isManual) {
        data.sprint_1_avg_power_w = sprint1Samples[0]?.watts;
        data.sprint_2_avg_power_w = sprint2Samples[0]?.watts;
        data.sprint_3_avg_power_w = sprint3Samples[0]?.watts;
      } else {
        data.sprint_1_samples = sprint1Samples;
        data.sprint_2_samples = sprint2Samples;
        data.sprint_3_samples = sprint3Samples;
      }

      await metabolicApi.createProfile(athleteId, data);
      setSaved(true);
      onSaved();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  }, [athleteId, bodyMassKg, dataSource, restingLactate, laPeaks, trim1, trim2, trim3, sprint1Samples, sprint2Samples, sprint3Samples, isManual, onSaved]);

  return (
    <div className="space-y-6 max-w-lg mx-auto overflow-y-auto">
      <h2 className="text-xl font-heading font-bold text-center">Results</h2>

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="space-y-1">
          {result.warnings.map((w, i) => (
            <div key={i} className="text-xs text-amber-400 bg-amber-400/5 px-3 py-1.5 rounded">{w}</div>
          ))}
        </div>
      )}

      {/* Results table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-white/30">
              <th className="text-left py-1">Metric</th>
              <th className="text-right py-1">Value</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-secondary-muted/20">
            <tr><td className="py-1.5 text-white/60">Weight</td><td className="py-1.5 text-right font-bold">{bodyMassKg.toFixed(1)} kg</td></tr>
            <tr><td className="py-1.5 text-white/60">Mech. Work Sprint 1</td><td className="py-1.5 text-right font-bold">{result.mechWork[0].toFixed(0)} J</td></tr>
            <tr><td className="py-1.5 text-white/60">Mech. Work Sprint 2</td><td className="py-1.5 text-right font-bold">{result.mechWork[1].toFixed(0)} J</td></tr>
            <tr><td className="py-1.5 text-white/60">Mech. Work Sprint 3</td><td className="py-1.5 text-right font-bold">{result.mechWork[2].toFixed(0)} J</td></tr>
            <tr><td className="py-1.5 text-white/60">Alactic Capacity</td><td className="py-1.5 text-right font-bold text-accent">{result.alacticCapacity.toFixed(0)} J</td></tr>
            <tr><td className="py-1.5 text-white/60">Max Glycolytic Power</td><td className="py-1.5 text-right font-bold">{result.maxGlycolyticPower?.toFixed(1) ?? 'N/A'} W</td></tr>
            <tr><td className="py-1.5 text-white/60">Anaerobic Cost</td><td className="py-1.5 text-right font-bold">{result.anaerobicCost?.toFixed(3) ?? 'N/A'}</td></tr>
            <tr><td className="py-1.5 text-white/60">Fatigue Slope</td><td className="py-1.5 text-right font-bold">{result.fatigueSlope?.toFixed(1) ?? 'N/A'} W</td></tr>
          </tbody>
        </table>
      </div>

      {/* Chart 1: Mechanical Work */}
      <div>
        <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Mechanical Work by Sprint</div>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={workChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" strokeOpacity={0.3} />
              <XAxis dataKey="name" tick={{ fill: '#2074AA', fontSize: 10 }} />
              <YAxis tick={{ fill: '#2074AA', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#07083D', border: '1px solid #2D5585', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="work" fill="#33CBF4" radius={[4, 4, 0, 0]} name="Work (J)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 2: Energy Breakdown */}
      <div>
        <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Energy System Breakdown</div>
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={energyChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" strokeOpacity={0.3} />
              <XAxis dataKey="name" tick={{ fill: '#2074AA', fontSize: 10 }} />
              <YAxis tick={{ fill: '#2074AA', fontSize: 10 }} />
              <Tooltip contentStyle={{ background: '#07083D', border: '1px solid #2D5585', borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#fff' }} />
              <Bar dataKey="alactic" stackId="energy" fill="#33CBF4" radius={[0, 0, 0, 0]} name="Alactic (J)" />
              <Bar dataKey="glycolytic" stackId="energy" fill="#2074AA" radius={[4, 4, 0, 0]} name="Glycolytic (J)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 3: Summary */}
      <div>
        <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Anaerobic Profile Summary</div>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={summaryChartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" strokeOpacity={0.3} />
              <XAxis type="number" tick={{ fill: '#2074AA', fontSize: 10 }} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#2074AA', fontSize: 9 }} width={130} />
              <Tooltip contentStyle={{ background: '#07083D', border: '1px solid #2D5585', borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="value" fill="#33CBF4" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Chart 4: Power Decay (BLE only) */}
      {isBle && powerDecayData.some(d => d.data.length > 0) && (
        <div>
          <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Power Decay</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#2D5585" strokeOpacity={0.3} />
                <XAxis
                  type="number" dataKey="x" domain={[0, 30]}
                  tick={{ fill: '#2074AA', fontSize: 10 }}
                  label={{ value: 'Time (s)', fill: '#2074AA', fontSize: 10, position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  tick={{ fill: '#2074AA', fontSize: 10 }}
                  label={{ value: 'Power (W)', fill: '#2074AA', fontSize: 10, angle: -90, position: 'insideLeft' }}
                />
                <Tooltip contentStyle={{ background: '#07083D', border: '1px solid #2D5585', borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11, color: '#fff' }} />
                {powerDecayData.map(d => d.data.length > 0 && (
                  <Scatter key={d.label} name={d.label} data={d.data} fill={d.color} shape="circle" legendType="circle">
                    {/* No explicit children needed */}
                  </Scatter>
                ))}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Insights */}
      <div>
        <div className="text-xs text-white/30 uppercase font-heading tracking-wider mb-2">Insights</div>
        <div className="space-y-2">
          {insights.map((insight, i) => (
            <div
              key={i}
              className={`bg-primary-dark/50 rounded-lg p-3 border-l-4 ${INSIGHT_COLORS[insight.category] || 'border-l-white/20'}`}
            >
              <span className={`inline-block text-[10px] font-heading font-bold uppercase tracking-wider px-2 py-0.5 rounded mb-1.5 ${INSIGHT_TAG_COLORS[insight.category] || 'bg-white/10 text-white/60'}`}>
                {insight.label}
              </span>
              <p className="text-sm text-white/80 leading-relaxed">{insight.text}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Trim controls (BLE only) */}
      {isBle && (
        <div className="bg-primary-dark/50 rounded-lg p-3 space-y-2">
          <div className="text-xs text-white/30 uppercase font-heading tracking-wider">Trim Controls</div>
          {[
            { label: 'Sprint 1', value: trim1, set: setTrim1, max: 9 },
            { label: 'Sprint 2', value: trim2, set: setTrim2, max: 19 },
            { label: 'Sprint 3', value: trim3, set: setTrim3, max: 29 },
          ].map(item => (
            <div key={item.label} className="flex items-center gap-2">
              <span className="text-sm text-white/50 w-16">{item.label}:</span>
              <input
                type="number"
                min={0}
                max={item.max}
                step={0.1}
                value={item.value}
                onChange={e => item.set(parseFloat(e.target.value) || 0)}
                className="w-20 px-2 py-1 text-sm bg-primary-dark border border-secondary-muted/50 rounded text-white text-center"
              />
              <span className="text-xs text-white/30">s to skip</span>
            </div>
          ))}
        </div>
      )}

      {/* Save / Actions */}
      <div className="flex gap-2">
        {!saved ? (
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary flex-1 py-2.5 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save to BSAMS'}
          </button>
        ) : (
          <div className="flex-1 text-center text-sm text-green-400 py-2.5">
            Saved successfully
          </div>
        )}
        <button
          onClick={onReset}
          className="px-4 py-2.5 rounded bg-secondary-muted/30 text-white/60 hover:text-white hover:bg-secondary-muted/50 transition-colors"
        >
          Reset
        </button>
      </div>

      {saveError && <p className="text-xs text-red-400 text-center">{saveError}</p>}
    </div>
  );
}
