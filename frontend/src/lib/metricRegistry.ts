/**
 * Central metric registry — single source of truth for all metric definitions.
 *
 * Replaces scattered METRIC_LABELS in MetricSelector, CsvPreviewTable, etc.
 * Mirrors backend app/schemas/metric_registry.py
 */

export type MetricGroup = 'jump' | 'vbt' | 'mobility' | 'isometric' | 'metadata';

export interface MetricDefinition {
  key: string;
  label: string;
  unit: string;
  domain: 'testing' | 'training' | 'wellness';
  group: MetricGroup;
  range: [number, number] | null;
  higherIsBetter: boolean;
}

export const METRIC_DEFINITIONS: MetricDefinition[] = [
  // Jump testing metrics
  { key: 'height_cm', label: 'CMJ Height (cm)', unit: 'cm', domain: 'testing', group: 'jump', range: [0, 200], higherIsBetter: true },
  { key: 'sj_height_cm', label: 'SJ Height (cm)', unit: 'cm', domain: 'testing', group: 'jump', range: [0, 200], higherIsBetter: true },
  { key: 'eur_cm', label: 'Eccentric Utilisation Ratio (cm)', unit: 'cm', domain: 'testing', group: 'jump', range: [-100, 200], higherIsBetter: true },
  { key: 'rsi', label: 'Reactive Strength Index', unit: '', domain: 'testing', group: 'jump', range: [0, 50], higherIsBetter: true },
  { key: 'flight_time_ms', label: 'Flight Time (ms)', unit: 'ms', domain: 'testing', group: 'jump', range: [0, 2000], higherIsBetter: true },
  { key: 'contraction_time_ms', label: 'Contact Time (ms)', unit: 'ms', domain: 'testing', group: 'jump', range: [0, 2000], higherIsBetter: false },
  // 10-5 pogo test metrics (distinct from CMJ-derived RSI above)
  { key: 'pogo_flight_time_ms', label: '10-5 Pogo Flight Time (ms)', unit: 'ms', domain: 'testing', group: 'jump', range: [0, 1500], higherIsBetter: true },
  { key: 'pogo_contact_time_ms', label: '10-5 Pogo Contact Time (ms)', unit: 'ms', domain: 'testing', group: 'jump', range: [0, 1500], higherIsBetter: false },
  { key: 'pogo_rsi', label: '10-5 Pogo RSI', unit: '', domain: 'testing', group: 'jump', range: [0, 10], higherIsBetter: true },
  // VBT metrics
  { key: 'mean_velocity_ms', label: 'Mean Velocity (m/s)', unit: 'm/s', domain: 'testing', group: 'vbt', range: [0, 5], higherIsBetter: true },
  { key: 'peak_velocity_ms', label: 'Peak Velocity (m/s)', unit: 'm/s', domain: 'testing', group: 'vbt', range: [0, 10], higherIsBetter: true },
  { key: 'mean_power_w', label: 'Mean Power (W)', unit: 'W', domain: 'testing', group: 'vbt', range: [0, 10000], higherIsBetter: true },
  { key: 'peak_power_w', label: 'Peak Power (W)', unit: 'W', domain: 'testing', group: 'vbt', range: [0, 15000], higherIsBetter: true },
  { key: 'bar_speed_ms', label: 'Bar Speed (m/s)', unit: 'm/s', domain: 'testing', group: 'vbt', range: [0, 5], higherIsBetter: true },
  { key: 'rom_mm', label: 'Range of Motion (mm)', unit: 'mm', domain: 'testing', group: 'vbt', range: [0, 2000], higherIsBetter: true },
  { key: 'time_to_peak_velocity_ms', label: 'Time to Peak Velocity (ms)', unit: 'ms', domain: 'testing', group: 'vbt', range: [0, 5000], higherIsBetter: false },
  { key: 'rep_duration_ms', label: 'Rep Duration (ms)', unit: 'ms', domain: 'testing', group: 'vbt', range: [0, 10000], higherIsBetter: false },
  // Mobility metrics
  { key: 'shoulder_ir_deg', label: 'Shoulder Internal Rotation (deg)', unit: 'deg', domain: 'testing', group: 'mobility', range: [0, 180], higherIsBetter: true },
  { key: 'shoulder_er_deg', label: 'Shoulder External Rotation (deg)', unit: 'deg', domain: 'testing', group: 'mobility', range: [0, 180], higherIsBetter: true },
  { key: 'hip_flexion_deg', label: 'Hip Flexion (deg)', unit: 'deg', domain: 'testing', group: 'mobility', range: [0, 180], higherIsBetter: true },
  { key: 'ankle_dorsiflexion_deg', label: 'Ankle Dorsiflexion (deg)', unit: 'deg', domain: 'testing', group: 'mobility', range: [0, 90], higherIsBetter: true },
  { key: 'thoracic_rotation_deg', label: 'Thoracic Rotation (deg)', unit: 'deg', domain: 'testing', group: 'mobility', range: [0, 90], higherIsBetter: true },
  // Isometric metrics
  { key: 'iso_trunk_rotation_left_kg', label: 'Iso Trunk Rotation Left (kg)', unit: 'kg', domain: 'testing', group: 'isometric', range: [0, 500], higherIsBetter: true },
  { key: 'iso_trunk_rotation_right_kg', label: 'Iso Trunk Rotation Right (kg)', unit: 'kg', domain: 'testing', group: 'isometric', range: [0, 500], higherIsBetter: true },
  { key: 'grip_strength_left_kg', label: 'Grip Strength Left (kg)', unit: 'kg', domain: 'testing', group: 'isometric', range: [0, 200], higherIsBetter: true },
  { key: 'grip_strength_right_kg', label: 'Grip Strength Right (kg)', unit: 'kg', domain: 'testing', group: 'isometric', range: [0, 200], higherIsBetter: true },
  { key: 'grip_rfd_left_pct', label: 'Grip RFD Left (%)', unit: '%', domain: 'testing', group: 'isometric', range: [0, 200], higherIsBetter: true },
  { key: 'grip_rfd_right_pct', label: 'Grip RFD Right (%)', unit: '%', domain: 'testing', group: 'isometric', range: [0, 200], higherIsBetter: true },
  // Rate of force development in N/s (optional — dynamometer may not report it).
  // Appended deliberately: testing/page.tsx defaults the Isometrics tab to ISOMETRIC_METRIC_KEYS[0].
  { key: 'grip_rfd_left_n_s', label: 'Grip RFD Left (N/s)', unit: 'N/s', domain: 'testing', group: 'isometric', range: [0, 20000], higherIsBetter: true },
  { key: 'grip_rfd_right_n_s', label: 'Grip RFD Right (N/s)', unit: 'N/s', domain: 'testing', group: 'isometric', range: [0, 20000], higherIsBetter: true },
  { key: 'iso_trunk_rotation_rfd_left_n_s', label: 'Iso Trunk Rotation RFD Left (N/s)', unit: 'N/s', domain: 'testing', group: 'isometric', range: [0, 20000], higherIsBetter: true },
  { key: 'iso_trunk_rotation_rfd_right_n_s', label: 'Iso Trunk Rotation RFD Right (N/s)', unit: 'N/s', domain: 'testing', group: 'isometric', range: [0, 20000], higherIsBetter: true },
  // Metadata
  { key: 'body_mass_kg', label: 'Body Mass (kg)', unit: 'kg', domain: 'testing', group: 'metadata', range: [0, 500], higherIsBetter: false },
];

// Lookup helpers
export const METRIC_BY_KEY: Record<string, MetricDefinition> = Object.fromEntries(
  METRIC_DEFINITIONS.map((m) => [m.key, m])
);

export const METRIC_LABELS: Record<string, string> = Object.fromEntries(
  METRIC_DEFINITIONS.map((m) => [m.key, m.label])
);

export function getMetricLabel(key: string): string {
  return METRIC_LABELS[key] || key;
}

// Group display labels
export const GROUP_LABELS: Record<MetricGroup, string> = {
  jump: 'Jump Testing',
  vbt: 'Velocity Based Training',
  mobility: 'Mobility',
  isometric: 'Isometric Testing',
  metadata: 'Metadata',
};

// Metrics grouped by group (excluding metadata)
export function getMetricsByGroup(): { group: MetricGroup; label: string; metrics: MetricDefinition[] }[] {
  const groups: MetricGroup[] = ['jump', 'vbt', 'mobility', 'isometric'];
  return groups.map((g) => ({
    group: g,
    label: GROUP_LABELS[g],
    metrics: METRIC_DEFINITIONS.filter((m) => m.group === g),
  }));
}
