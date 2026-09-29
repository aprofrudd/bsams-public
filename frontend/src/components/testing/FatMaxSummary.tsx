'use client';

import { computeFatMax, findCrossoverIntensity, interpolateAtIntensity } from '@/lib/cpetAnalysis';
import type { GasAnalysisStageSummary, LactateStage } from '@/lib/types';

interface FatMaxSummaryProps {
  stageAverages: GasAnalysisStageSummary[];
  lactateStages: LactateStage[];
  unitLabel: string;
  lt1Value?: number | null;
  lt2Value?: number | null;
}

export function FatMaxSummary({ stageAverages, lactateStages, unitLabel, lt1Value, lt2Value }: FatMaxSummaryProps) {
  const fatMax = computeFatMax(stageAverages);
  const crossover = findCrossoverIntensity(stageAverages);

  if (!fatMax && !crossover) return null;

  // Interpolate associated metrics at fat max intensity
  const fatMaxHr = fatMax?.fat_max_intensity != null
    ? interpolateAtIntensity(stageAverages, fatMax.fat_max_intensity, 'avg_hr_bpm')
    : null;
  const fatMaxVo2 = fatMax?.fat_max_intensity != null
    ? interpolateAtIntensity(stageAverages, fatMax.fat_max_intensity, 'avg_vo2_ml_kg_min')
    : null;

  // Interpolate blood lactate at fat max from lactate stages
  let fatMaxLactate: number | null = null;
  if (fatMax?.fat_max_intensity != null && lactateStages.length >= 2) {
    const sorted = [...lactateStages]
      .filter((s) => s.intensity_value != null && s.blood_lactate_mmol != null)
      .sort((a, b) => a.intensity_value - b.intensity_value);
    if (sorted.length >= 2) {
      const target = fatMax.fat_max_intensity;
      let lower = sorted[0];
      let upper = sorted[1];
      for (const s of sorted) {
        if (s.intensity_value <= target) lower = s;
        else { upper = s; break; }
      }
      if (lower && upper && upper.intensity_value !== lower.intensity_value) {
        const t = (target - lower.intensity_value) / (upper.intensity_value - lower.intensity_value);
        fatMaxLactate = Math.round((lower.blood_lactate_mmol + t * (upper.blood_lactate_mmol - lower.blood_lactate_mmol)) * 100) / 100;
      }
    }
  }

  return (
    <div className="border border-secondary-muted/50 rounded-lg p-3 space-y-2">
      <h4 className="text-sm text-white/60 font-medium">Gas Analysis Summary</h4>

      {fatMax && (
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-orange-400 font-medium">Max Fat Oxidation:</span>
            <span className="text-white">{fatMax.max_fat_oxidation_gh} g/h</span>
            {fatMax.fat_max_intensity != null && (
              <span className="text-white/60">at {fatMax.fat_max_intensity} {unitLabel}</span>
            )}
          </div>
          <div className="flex flex-wrap gap-3 text-xs text-white/60">
            {fatMaxHr != null && <span>HR: {Math.round(fatMaxHr)} bpm</span>}
            {fatMaxVo2 != null && <span>VO2: {fatMaxVo2.toFixed(1)} ml/kg/min</span>}
            {fatMaxLactate != null && <span>BLa: {fatMaxLactate.toFixed(2)} mmol/L</span>}
          </div>
        </div>
      )}

      {crossover != null && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-yellow-400 font-medium">CHO/FAT Crossover:</span>
          <span className="text-white">{crossover} {unitLabel}</span>
        </div>
      )}

      {(() => {
        const crossoverLt1Gap = (crossover != null && lt1Value != null && lt1Value > 0)
          ? { absolute: Math.round((lt1Value - crossover) * 10) / 10, percent: Math.round(((lt1Value - crossover) / lt1Value) * 100) }
          : null;
        const fatMaxLt1Percent = (fatMax?.fat_max_intensity != null && lt1Value != null && lt1Value > 0)
          ? Math.round((fatMax.fat_max_intensity / lt1Value) * 100)
          : null;

        if (!crossoverLt1Gap && fatMaxLt1Percent == null) return null;

        let gapColor = 'text-green-400';
        let gapLabel = 'Balanced';
        let gapDetail = 'Crossover and LT1 well aligned';
        if (crossoverLt1Gap) {
          if (crossoverLt1Gap.percent < 0) {
            gapColor = 'text-red-400';
            gapLabel = 'Clearance limited';
            gapDetail = 'Good fat metabolism, needs threshold work';
          } else if (crossoverLt1Gap.percent > 10) {
            gapColor = 'text-amber-400';
            gapLabel = 'Fat oxidation limited';
            gapDetail = 'Good clearance, needs aerobic volume';
          }
        }

        return (
          <div className="border-t border-secondary-muted/30 pt-2 space-y-1">
            <h5 className="text-xs text-white/50 font-medium">Metabolic Gap</h5>
            {crossoverLt1Gap && (
              <div className="space-y-0.5">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-white/60">Crossover → LT1:</span>
                  <span className="text-white">{crossoverLt1Gap.absolute > 0 ? '+' : ''}{crossoverLt1Gap.absolute} {unitLabel}</span>
                  <span className="text-white/40">({crossoverLt1Gap.percent}%)</span>
                  <span className={`text-xs font-medium ${gapColor}`}>{gapLabel}</span>
                </div>
                <p className="text-xs text-white/40">{gapDetail}</p>
              </div>
            )}
            {fatMaxLt1Percent != null && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-white/60">Fat max at</span>
                <span className="text-white font-medium">{fatMaxLt1Percent}%</span>
                <span className="text-white/60">of LT1</span>
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}
