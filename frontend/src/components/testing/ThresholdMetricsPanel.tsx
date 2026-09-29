'use client';

import { computeThresholdMetrics } from '@/lib/cpetAnalysis';
import type { GasAnalysisStageSummary } from '@/lib/types';

interface ThresholdMetricsPanelProps {
  stageAverages: GasAnalysisStageSummary[];
  lt1Value: number | null;
  lt2Value: number | null;
  unitLabel: string;
}

function MetricRow({ label, lt1, lt2, unit, decimals = 1 }: {
  label: string;
  lt1: number | null;
  lt2: number | null;
  unit: string;
  decimals?: number;
}) {
  const fmt = (v: number | null) => v != null ? `${v.toFixed(decimals)} ${unit}` : '-';
  return (
    <tr className="border-t border-secondary-muted/20">
      <td className="py-1 pr-3 text-white/60 text-xs">{label}</td>
      <td className="py-1 px-3 text-right text-white text-xs">{fmt(lt1)}</td>
      <td className="py-1 pl-3 text-right text-white text-xs">{fmt(lt2)}</td>
    </tr>
  );
}

export function ThresholdMetricsPanel({ stageAverages, lt1Value, lt2Value, unitLabel }: ThresholdMetricsPanelProps) {
  if (lt1Value == null && lt2Value == null) return null;

  const lt1Metrics = lt1Value != null ? computeThresholdMetrics(stageAverages, lt1Value) : null;
  const lt2Metrics = lt2Value != null ? computeThresholdMetrics(stageAverages, lt2Value) : null;

  if (!lt1Metrics && !lt2Metrics) return null;

  return (
    <div className="border border-secondary-muted/50 rounded-lg p-3">
      <h4 className="text-sm text-white/60 font-medium mb-2">Threshold Gas Metrics</h4>
      <div>
        <table className="w-full">
          <thead>
            <tr className="text-white/40 text-xs">
              <th className="text-left py-1 pr-3">Metric</th>
              <th className="text-right py-1 px-3">
                LT1{lt1Value != null && <span className="text-green-400 ml-1">({lt1Value} {unitLabel})</span>}
              </th>
              <th className="text-right py-1 pl-3">
                LT2{lt2Value != null && <span className="text-red-400 ml-1">({lt2Value} {unitLabel})</span>}
              </th>
            </tr>
          </thead>
          <tbody>
            <MetricRow label="VO2" lt1={lt1Metrics?.vo2_ml_kg_min ?? null} lt2={lt2Metrics?.vo2_ml_kg_min ?? null} unit="ml/kg/min" />
            <MetricRow label="HR" lt1={lt1Metrics?.hr_bpm ?? null} lt2={lt2Metrics?.hr_bpm ?? null} unit="bpm" decimals={0} />
            <MetricRow label="RER" lt1={lt1Metrics?.rer ?? null} lt2={lt2Metrics?.rer ?? null} unit="" decimals={2} />
            <MetricRow label="VE" lt1={lt1Metrics?.ve_l_min ?? null} lt2={lt2Metrics?.ve_l_min ?? null} unit="L/min" />
            <MetricRow label="FAT" lt1={lt1Metrics?.fat_gh ?? null} lt2={lt2Metrics?.fat_gh ?? null} unit="g/h" />
            <MetricRow label="CHO" lt1={lt1Metrics?.cho_gh ?? null} lt2={lt2Metrics?.cho_gh ?? null} unit="g/h" />
            <MetricRow label="EE" lt1={lt1Metrics?.ee_kcal_h ?? null} lt2={lt2Metrics?.ee_kcal_h ?? null} unit="kcal/h" decimals={0} />
            <MetricRow label="FAT EE" lt1={lt1Metrics?.fat_ee_kcal_h ?? null} lt2={lt2Metrics?.fat_ee_kcal_h ?? null} unit="kcal/h" decimals={0} />
            <MetricRow label="CHO EE" lt1={lt1Metrics?.cho_ee_kcal_h ?? null} lt2={lt2Metrics?.cho_ee_kcal_h ?? null} unit="kcal/h" decimals={0} />
          </tbody>
        </table>
      </div>
    </div>
  );
}
