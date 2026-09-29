/**
 * Metabolic profile calculation engine — TypeScript mirror of metabolic_engine.py.
 * Ferretti/di Prampero protocol for anaerobic glycolytic profiling.
 */

const BETA = 63;   // J/kg/mM
const ETA = 0.25;  // gross mechanical efficiency
const TAU = 15;    // min (lactate half-life)

export interface MetabolicResult {
  mechWork: [number, number, number];
  alacticCapacity: number;
  maxGlycolyticPower: number | null;
  anaerobicCost: number | null;
  fatigueSlope: number | null;
  alactic: [number, number, number];
  glycolytic: [number, number, number];
  warnings: string[];
}

export interface PowerSample {
  elapsed_ms: number;
  watts: number;
}

export interface MetabolicInsight {
  category: string;
  label: string;
  text: string;
  color: 'cyan' | 'red' | 'amber';
}

export function sumWatts(
  samples: PowerSample[],
  fromSec: number,
  toSec: number,
  trimSec: number = 0
): number {
  const fromMs = fromSec * 1000;
  const toMs = toSec * 1000;
  const trimMs = trimSec * 1000;

  const filtered = samples.filter(
    s => s.elapsed_ms >= fromMs + trimMs && s.elapsed_ms < toMs
  );
  if (filtered.length === 0) return 0;

  let totalJ = 0;
  for (let i = 0; i < filtered.length; i++) {
    let dt: number;
    if (i === 0) {
      dt = filtered.length > 1
        ? (filtered[1].elapsed_ms - filtered[0].elapsed_ms) / 1000
        : 1;
    } else {
      dt = (filtered[i].elapsed_ms - filtered[i - 1].elapsed_ms) / 1000;
    }
    dt = Math.max(0.1, Math.min(3, dt));
    totalJ += filtered[i].watts * dt;
  }
  return totalJ;
}

export function calculateMetabolicProfile(
  bodyMassKg: number,
  restingLactate: number,
  laPeaks: [number, number, number],
  mechWorkJ: [number, number, number]
): MetabolicResult {
  const warnings: string[] = [];

  // Baseline corrections
  const base2 = laPeaks[0] * Math.pow(0.5, 3 / TAU);
  const base3 = laPeaks[1] * Math.pow(0.5, 12 / TAU);

  // Delta lactates
  const dLa1 = laPeaks[0] - restingLactate;
  const dLa2 = laPeaks[1] - base2;
  const dLa3 = laPeaks[2] - base3;

  if (dLa1 < 0) warnings.push('Negative delta lactate for Sprint 1 — physiologically implausible');
  if (dLa2 < 0) warnings.push('Negative delta lactate for Sprint 2');
  if (dLa3 < 0) warnings.push('Negative delta lactate for Sprint 3');

  // Computed results (unclamped)
  const alacticCapacity = mechWorkJ[0] - dLa1 * bodyMassKg * BETA * ETA;
  const maxGlycolyticPower = mechWorkJ[1] > 0 ? (dLa2 * bodyMassKg * BETA * ETA) / 10 : null;
  const anaerobicCost = mechWorkJ[1] > 0 ? (dLa2 * bodyMassKg * BETA * ETA) / mechWorkJ[1] : null;
  const fatigueSlope = mechWorkJ[2] > 0 ? (dLa3 * bodyMassKg * BETA * ETA) / 10 : null;

  // Per-sprint energy breakdown (unclamped)
  const glycolytic: [number, number, number] = [
    dLa1 * bodyMassKg * BETA * ETA,
    dLa2 * bodyMassKg * BETA * ETA,
    dLa3 * bodyMassKg * BETA * ETA,
  ];
  const alactic: [number, number, number] = [
    mechWorkJ[0] - glycolytic[0],
    mechWorkJ[1] - glycolytic[1],
    mechWorkJ[2] - glycolytic[2],
  ];

  if (mechWorkJ[0] === 0) warnings.push('Zero mechanical work for Sprint 1');
  if (mechWorkJ[1] === 0) warnings.push('Zero mechanical work for Sprint 2');
  if (mechWorkJ[2] === 0) warnings.push('Zero mechanical work for Sprint 3');

  return {
    mechWork: mechWorkJ,
    alacticCapacity,
    maxGlycolyticPower,
    anaerobicCost,
    fatigueSlope,
    alactic,
    glycolytic,
    warnings,
  };
}

export function generateInsights(
  result: MetabolicResult,
  bodyMassKg: number
): MetabolicInsight[] {
  const insights: MetabolicInsight[] = [];
  const alacticPerKg = bodyMassKg > 0 ? result.alacticCapacity / bodyMassKg : 0;

  // Clamped values for chart/display
  const glyco1 = Math.max(0, result.glycolytic[0]);
  const glyco2 = Math.max(0, result.glycolytic[1]);
  const glyco3 = Math.max(0, result.glycolytic[2]);
  const alac1 = Math.max(0, result.alactic[0]);
  const alac2 = Math.max(0, result.alactic[1]);
  const alac3 = Math.max(0, result.alactic[2]);

  // 1. Alactic Capacity
  if (alacticPerKg < 50) {
    insights.push({
      category: 'alactic', label: 'Alactic Capacity', color: 'cyan',
      text: `Alactic capacity is low (${alacticPerKg.toFixed(1)} J/kg). Focus on short, maximal sprints (3-6s) with full recovery to develop the phosphocreatine system.`,
    });
  } else if (alacticPerKg <= 100) {
    insights.push({
      category: 'alactic', label: 'Alactic Capacity', color: 'cyan',
      text: `Alactic capacity is moderate (${alacticPerKg.toFixed(1)} J/kg). Maintain with regular sprint work and consider creatine supplementation if appropriate.`,
    });
  } else {
    insights.push({
      category: 'alactic', label: 'Alactic Capacity', color: 'cyan',
      text: `Alactic capacity is high (${alacticPerKg.toFixed(1)} J/kg). Well-developed phosphocreatine system — a strong foundation for explosive efforts.`,
    });
  }

  // 2. Glycolytic Trend
  const progressive = glyco3 > glyco2 && glyco2 > glyco1;
  insights.push({
    category: 'glycolytic', label: 'Glycolytic Trend', color: 'red',
    text: progressive
      ? `Glycolytic energy rises progressively (${glyco1.toFixed(0)} → ${glyco2.toFixed(0)} → ${glyco3.toFixed(0)} J), indicating increasing glycolytic engagement with sprint duration.`
      : `Glycolytic contribution is non-progressive (${glyco1.toFixed(0)} / ${glyco2.toFixed(0)} / ${glyco3.toFixed(0)} J). Consider lactate sampling timing or sprint pacing.`,
  });

  // 3. Fatigue Pattern
  const avgPow1 = result.mechWork[0] / 10;
  const avgPow2 = result.mechWork[1] / 10;
  const avgPow3 = result.mechWork[2] / 10;
  const peakPow = Math.max(avgPow1, avgPow2, avgPow3);
  const minPow = Math.min(avgPow1, avgPow2, avgPow3);
  const declinePct = peakPow > 0 ? ((peakPow - minPow) / peakPow) * 100 : 0;

  if (declinePct > 20) {
    insights.push({
      category: 'fatigue', label: 'Fatigue Pattern', color: 'amber',
      text: `Power declines by ${declinePct.toFixed(0)}% — significant. Incorporate repeated sprint training (6-10 x 6s with 30s rest) to improve buffering capacity.`,
    });
  } else if (declinePct > 10) {
    insights.push({
      category: 'fatigue', label: 'Fatigue Pattern', color: 'amber',
      text: `Power declines by ${declinePct.toFixed(0)}% — moderate. Work-to-rest ratio sessions (10s on / 50s off) can help maintain output.`,
    });
  } else {
    insights.push({
      category: 'fatigue', label: 'Fatigue Pattern', color: 'amber',
      text: `Power declines by only ${declinePct.toFixed(0)}% — good fatigue resistance. The athlete maintains output well under metabolic stress.`,
    });
  }

  // 4. Energy System Dominance
  const pctStr = (a: number, g: number) => {
    const t = a + g;
    return t > 0 ? `${(a / t * 100).toFixed(0)}% alactic / ${(g / t * 100).toFixed(0)}% glycolytic` : 'N/A';
  };
  insights.push({
    category: 'dominance', label: 'Energy System Dominance', color: 'cyan',
    text: `Sprint 1: ${pctStr(alac1, glyco1)}. Sprint 2: ${pctStr(alac2, glyco2)}. Sprint 3: ${pctStr(alac3, glyco3)}.`,
  });

  // 5. Lactate Response
  const totalGlyco = glyco1 + glyco2 + glyco3;
  if (totalGlyco > 12000) {
    insights.push({
      category: 'lactate', label: 'Lactate Response', color: 'red',
      text: `High total glycolytic energy (${totalGlyco.toFixed(0)} J) indicates strong anaerobic glycolytic capacity. Recovery strategies and buffering training are advisable.`,
    });
  } else if (totalGlyco > 5000) {
    insights.push({
      category: 'lactate', label: 'Lactate Response', color: 'red',
      text: `Moderate total glycolytic energy (${totalGlyco.toFixed(0)} J) reflects a balanced glycolytic response.`,
    });
  } else {
    insights.push({
      category: 'lactate', label: 'Lactate Response', color: 'red',
      text: `Low total glycolytic energy (${totalGlyco.toFixed(0)} J). Consider whether sprint effort was truly maximal.`,
    });
  }

  // 6. Training Recommendations
  if (alacticPerKg < 50 && declinePct > 20) {
    insights.push({
      category: 'training', label: 'Training Recommendations', color: 'cyan',
      text: 'Priority: develop alactic power (short max sprints, 3-6s, full recovery) and fatigue resistance (repeated sprints with short rest). Consider a two-block periodisation approach.',
    });
  } else if (alacticPerKg < 50) {
    insights.push({
      category: 'training', label: 'Training Recommendations', color: 'cyan',
      text: 'Priority: develop alactic capacity with short, maximal sprints (3-6s) and full recovery (2-3 min). Fatigue resistance is adequate.',
    });
  } else if (declinePct > 20) {
    insights.push({
      category: 'training', label: 'Training Recommendations', color: 'cyan',
      text: 'Alactic base is solid. Priority: improve repeated sprint ability and glycolytic buffering. Use 6-10s sprints with reducing rest intervals.',
    });
  } else {
    insights.push({
      category: 'training', label: 'Training Recommendations', color: 'cyan',
      text: 'Well-balanced anaerobic profile. Maintain with mixed sprint training and periodically retest to track adaptations.',
    });
  }

  return insights;
}
