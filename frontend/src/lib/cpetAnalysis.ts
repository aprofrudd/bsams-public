/**
 * Client-side CPET gas analysis engine.
 *
 * TypeScript port of backend/app/services/cpet_engine.py.
 * Provides fat max detection, threshold interpolation, and crossover detection.
 */

import type { GasAnalysisStageSummary } from '@/lib/types';

export interface FatMaxResult {
  max_fat_oxidation_gh: number;
  fat_max_stage_number: number;
  fat_max_intensity: number | null;
  fat_max_hr: number | null;
}

export interface ThresholdGasMetrics {
  intensity: number;
  vo2_ml_kg_min: number | null;
  vo2_l_min: number | null;
  rer: number | null;
  ve_l_min: number | null;
  bf_per_min: number | null;
  hr_bpm: number | null;
  fat_gh: number | null;
  cho_gh: number | null;
  ee_kcal_h: number | null;
  cho_ee_kcal_h: number | null;
  fat_ee_kcal_h: number | null;
}

export function computeFatMax(stageAverages: GasAnalysisStageSummary[]): FatMaxResult | null {
  let bestFat = -1;
  let bestStage: GasAnalysisStageSummary | null = null;

  for (const sa of stageAverages) {
    if (sa.avg_fat_gh != null && sa.avg_fat_gh > bestFat) {
      bestFat = sa.avg_fat_gh;
      bestStage = sa;
    }
  }

  if (!bestStage || bestFat <= 0) return null;

  return {
    max_fat_oxidation_gh: Math.round(bestFat * 10) / 10,
    fat_max_stage_number: bestStage.stage_number,
    fat_max_intensity: bestStage.intensity_value,
    fat_max_hr: bestStage.avg_hr_bpm != null ? Math.round(bestStage.avg_hr_bpm) : null,
  };
}

export function interpolateAtIntensity(
  stageAverages: GasAnalysisStageSummary[],
  targetIntensity: number,
  metricKey: keyof GasAnalysisStageSummary
): number | null {
  const valid = stageAverages
    .filter((sa) => sa.intensity_value != null && sa[metricKey] != null)
    .sort((a, b) => a.intensity_value! - b.intensity_value!);

  if (valid.length === 0) return null;

  // Exact match
  for (const sa of valid) {
    if (sa.intensity_value === targetIntensity) return sa[metricKey] as number;
  }

  // Find bracketing stages
  let lower: GasAnalysisStageSummary | null = null;
  let upper: GasAnalysisStageSummary | null = null;

  for (const sa of valid) {
    if (sa.intensity_value! <= targetIntensity) lower = sa;
    else if (upper == null) upper = sa;
  }

  if (lower == null || upper == null) {
    if (valid.length < 2) return valid[0][metricKey] as number;
    if (lower == null) {
      lower = valid[0];
      upper = valid[1];
    } else {
      lower = valid[valid.length - 2];
      upper = valid[valid.length - 1];
    }
  }

  const x1 = lower.intensity_value!;
  const x2 = upper.intensity_value!;
  const y1 = lower[metricKey] as number;
  const y2 = upper[metricKey] as number;

  if (x2 === x1) return y1;

  const t = (targetIntensity - x1) / (x2 - x1);
  return Math.round((y1 + t * (y2 - y1)) * 100) / 100;
}

export function computeThresholdMetrics(
  stageAverages: GasAnalysisStageSummary[],
  thresholdIntensity: number
): ThresholdGasMetrics | null {
  if (stageAverages.length === 0) return null;

  const metrics: ThresholdGasMetrics = {
    intensity: thresholdIntensity,
    vo2_ml_kg_min: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_vo2_ml_kg_min'),
    vo2_l_min: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_vo2_l_min'),
    rer: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_rer'),
    ve_l_min: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_ve_l_min'),
    bf_per_min: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_bf_per_min'),
    hr_bpm: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_hr_bpm'),
    fat_gh: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_fat_gh'),
    cho_gh: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_cho_gh'),
    ee_kcal_h: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_ee_kcal_h'),
    cho_ee_kcal_h: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_cho_ee_kcal_h'),
    fat_ee_kcal_h: interpolateAtIntensity(stageAverages, thresholdIntensity, 'avg_fat_ee_kcal_h'),
  };

  // Return null if no metrics were interpolated
  const hasAny = Object.entries(metrics).some(
    ([k, v]) => k !== 'intensity' && v != null
  );
  return hasAny ? metrics : null;
}

export function findCrossoverIntensity(stageAverages: GasAnalysisStageSummary[]): number | null {
  const valid = stageAverages
    .filter((sa) => {
      const cho = sa.avg_cho_ee_kcal_h ?? sa.avg_cho_gh;
      const fat = sa.avg_fat_ee_kcal_h ?? sa.avg_fat_gh;
      return sa.intensity_value != null && cho != null && fat != null;
    })
    .sort((a, b) => a.intensity_value! - b.intensity_value!)
    .map((sa) => ({
      intensity: sa.intensity_value!,
      cho: (sa.avg_cho_ee_kcal_h ?? sa.avg_cho_gh)!,
      fat: (sa.avg_fat_ee_kcal_h ?? sa.avg_fat_gh)!,
    }));

  if (valid.length < 2) return null;

  for (let i = 0; i < valid.length - 1; i++) {
    const diffCurr = valid[i].cho - valid[i].fat;
    const diffNext = valid[i + 1].cho - valid[i + 1].fat;

    if (diffCurr <= 0 && diffNext > 0) {
      const x1 = valid[i].intensity;
      const x2 = valid[i + 1].intensity;
      if (diffNext === diffCurr) return x1;
      const t = -diffCurr / (diffNext - diffCurr);
      return Math.round((x1 + t * (x2 - x1)) * 100) / 100;
    }
  }

  return null;
}
