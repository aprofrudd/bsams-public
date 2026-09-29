/**
 * What each station asks for, and how those inputs become an attempt payload.
 *
 * Keeping this as data rather than six near-identical form components means the
 * station screen is one component, and adding a station later is one entry here.
 *
 * Two things are event-dependent rather than fixed: which velocity the landmine
 * ranks on, and which unit the dynamometers read. Both come in as `StationSettings`
 * so the screen asks for exactly what the event will score.
 */

import type { CombineEvent, CombineMeasures, CombineRfdUnit, CombineStation } from '@/lib/types';

export interface StationField {
  key: string;
  label: string;
  unit?: string;
  /** Optional fields sit behind a disclosure so the normal flow stays short. */
  optional?: boolean;
  maxDecimals?: number;
  maxIntegerDigits?: number;
  /** Mirrors the bounds in backend schemas/combine.py — outside them is a 422. */
  min: number;
  max: number;
  /** The schema says `gt=`, not `ge=`: a typed 0 is rejected. */
  minExclusive?: boolean;
}

export interface StationDefinition {
  station: CombineStation;
  label: string;
  shortLabel: string;
  fields: StationField[];
  /** Extra chips shown above the keypad (sprint number, load, side). */
  chips?: { key: string; label: string };
  hint?: string;
}

/** The event settings that change what a station asks for. */
export type StationSettings = Pick<CombineEvent, 'rfd_unit' | 'landmine_velocity_metric'>;

const DEFAULT_SETTINGS: StationSettings = {
  rfd_unit: 'n_s',
  landmine_velocity_metric: 'peak',
};

// RFD is stored in N/s. A kg/s dynamometer's reading is multiplied by g on the way
// in, so the typed ceiling is the stored ceiling divided by g.
const KGF_TO_NEWTONS = 9.80665;
const RFD_MAX_N_S = 20000;
const RFD_MAX_KG_S = Math.floor(RFD_MAX_N_S / KGF_TO_NEWTONS);

/** Defaults: N/s dynamometers and a peak-velocity landmine. `stationFields` adapts. */
export const STATION_DEFINITIONS: Record<CombineStation, StationDefinition> = {
  cmj: {
    station: 'cmj',
    label: 'Countermovement Jump',
    shortLabel: 'CMJ',
    fields: [
      {
        key: 'height_cm',
        label: 'Jump Height',
        unit: 'cm',
        maxDecimals: 1,
        maxIntegerDigits: 2,
        min: 0,
        max: 90,
        minExclusive: true,
      },
    ],
  },
  pogo: {
    station: 'pogo',
    label: '10-5 Pogo',
    shortLabel: 'Pogo',
    fields: [
      {
        key: 'flight_time_ms',
        label: 'Flight Time',
        unit: 'ms',
        maxDecimals: 0,
        maxIntegerDigits: 4,
        min: 0,
        max: 1500,
        minExclusive: true,
      },
      {
        key: 'contact_time_ms',
        label: 'Contact Time',
        unit: 'ms',
        maxDecimals: 0,
        maxIntegerDigits: 4,
        min: 0,
        max: 1500,
        minExclusive: true,
      },
      {
        key: 'rsi',
        label: 'RSI (direct)',
        optional: true,
        maxDecimals: 2,
        maxIntegerDigits: 1,
        min: 0,
        max: 10,
        minExclusive: true,
      },
    ],
    hint: 'RSI is calculated from flight ÷ contact — enter it directly only if your system reports it.',
  },
  landmine: {
    station: 'landmine',
    label: 'Landmine Punch',
    shortLabel: 'Punch',
    chips: { key: 'load_kg', label: 'Load' },
    fields: [
      {
        key: 'peak_velocity_ms',
        label: 'Peak Velocity',
        unit: 'm/s',
        maxDecimals: 2,
        maxIntegerDigits: 1,
        min: 0,
        max: 10,
        minExclusive: true,
      },
      {
        key: 'mean_velocity_ms',
        label: 'Mean Velocity',
        unit: 'm/s',
        optional: true,
        maxDecimals: 2,
        maxIntegerDigits: 1,
        min: 0,
        max: 5,
        minExclusive: true,
      },
    ],
  },
  grip: {
    station: 'grip',
    label: 'Grip Strength',
    shortLabel: 'Grip',
    fields: [
      { key: 'left_kg', label: 'Left', unit: 'kg', maxDecimals: 1, maxIntegerDigits: 3, min: 0, max: 120, minExclusive: true },
      { key: 'right_kg', label: 'Right', unit: 'kg', maxDecimals: 1, maxIntegerDigits: 3, min: 0, max: 120, minExclusive: true },
      { key: 'rfd_left_n_s', label: 'RFD Left', unit: 'N/s', optional: true, maxDecimals: 0, maxIntegerDigits: 5, min: 0, max: RFD_MAX_N_S },
      { key: 'rfd_right_n_s', label: 'RFD Right', unit: 'N/s', optional: true, maxDecimals: 0, maxIntegerDigits: 5, min: 0, max: RFD_MAX_N_S },
    ],
  },
  trunk_rotation: {
    station: 'trunk_rotation',
    label: 'Trunk Rotation',
    shortLabel: 'Rotation',
    fields: [
      { key: 'left_kg', label: 'Left', unit: 'kg', maxDecimals: 1, maxIntegerDigits: 3, min: 0, max: 200, minExclusive: true },
      { key: 'right_kg', label: 'Right', unit: 'kg', maxDecimals: 1, maxIntegerDigits: 3, min: 0, max: 200, minExclusive: true },
      { key: 'rfd_left_n_s', label: 'RFD Left', unit: 'N/s', optional: true, maxDecimals: 0, maxIntegerDigits: 5, min: 0, max: RFD_MAX_N_S },
      { key: 'rfd_right_n_s', label: 'RFD Right', unit: 'N/s', optional: true, maxDecimals: 0, maxIntegerDigits: 5, min: 0, max: RFD_MAX_N_S },
    ],
  },
  air_bike: {
    station: 'air_bike',
    label: 'Air Bike 30s Sprint',
    shortLabel: 'Bike',
    chips: { key: 'sprint_number', label: 'Sprint' },
    fields: [
      { key: 'power_7s', label: '7s Power', unit: 'W', maxDecimals: 0, maxIntegerDigits: 4, min: 0, max: 3000, minExclusive: true },
      { key: 'power_17s', label: '17s Power', unit: 'W', maxDecimals: 0, maxIntegerDigits: 4, min: 0, max: 3000, minExclusive: true },
      { key: 'power_27s', label: '27s Power', unit: 'W', maxDecimals: 0, maxIntegerDigits: 4, min: 0, max: 3000, minExclusive: true },
      { key: 'blood_lactate_mmol', label: 'Lactate', unit: 'mmol/L', optional: true, maxDecimals: 2, maxIntegerDigits: 2, min: 0, max: 30 },
    ],
  },
};

export type FieldValues = Record<string, string>;

/** The velocity key this event ranks the landmine on. */
function velocityKey(settings: StationSettings): string {
  return settings.landmine_velocity_metric === 'mean' ? 'mean_velocity_ms' : 'peak_velocity_ms';
}

/**
 * The fields this station asks for at this event.
 *
 * The landmine's ranked velocity leads and is required — the board ranks on one
 * metric with no fallback, so an attempt without it cannot be scored. RFD fields
 * are relabelled and re-bounded when the dynamometer reads kg/s.
 */
export function stationFields(
  station: CombineStation,
  settings: StationSettings = DEFAULT_SETTINGS
): StationField[] {
  const fields = STATION_DEFINITIONS[station].fields;

  if (station === 'landmine') {
    const required = velocityKey(settings);
    return fields
      .map((field) => ({ ...field, optional: field.key !== required }))
      .sort((a, b) => Number(a.optional) - Number(b.optional));
  }

  if ((station === 'grip' || station === 'trunk_rotation') && settings.rfd_unit === 'kg_s') {
    return fields.map((field) =>
      field.key.startsWith('rfd_')
        ? { ...field, unit: 'kg/s', max: RFD_MAX_KG_S, maxIntegerDigits: 4 }
        : field
    );
  }

  return fields;
}

/** Which required fields are still empty. Empty array means the attempt can be saved. */
export function missingRequired(
  station: CombineStation,
  values: FieldValues,
  settings: StationSettings = DEFAULT_SETTINGS
): string[] {
  if (station === 'pogo') {
    const hasPair = Boolean(values.flight_time_ms && values.contact_time_ms);
    const hasRsi = Boolean(values.rsi);
    return hasPair || hasRsi ? [] : ['flight_time_ms', 'contact_time_ms'];
  }

  if (station === 'grip' || station === 'trunk_rotation') {
    return values.left_kg || values.right_kg ? [] : ['left_kg', 'right_kg'];
  }

  if (station === 'landmine') {
    const required = velocityKey(settings);
    return values[required] ? [] : [required];
  }

  return stationFields(station, settings)
    .filter((field) => !field.optional && !values[field.key])
    .map((field) => field.key);
}

/**
 * The first typed value the backend would reject, as copy for the operator.
 *
 * Catching it here keeps SAVE disabled with a reason on screen, rather than
 * sending the attempt and turning a 422 into a red line beside a waiting boxer.
 */
export function rangeError(
  station: CombineStation,
  values: FieldValues,
  settings: StationSettings = DEFAULT_SETTINGS
): string | null {
  for (const field of stationFields(station, settings)) {
    const raw = values[field.key];
    // "0." is the keypad mid-decimal, not a zero: 0.85 is on its way.
    if (!raw || raw.endsWith('.')) continue;

    const value = Number(raw);
    if (!Number.isFinite(value)) continue;

    const tooLow = field.minExclusive ? value <= field.min : value < field.min;
    if (!tooLow && value <= field.max) continue;

    const floor = field.minExclusive ? `over ${field.min}` : `at least ${field.min}`;
    const unit = field.unit ? ` ${field.unit}` : '';
    return `${field.label} must be ${floor} and at most ${field.max}${unit}`;
  }
  return null;
}

/** Build the API payload. Blank fields are dropped rather than sent as zero. */
export function buildMeasures(
  station: CombineStation,
  values: FieldValues,
  extras: {
    load_kg?: number;
    sprint_number?: number;
    side?: 'left' | 'right';
    rfd_unit?: CombineRfdUnit;
  } = {}
): CombineMeasures {
  const num = (key: string): number | undefined => {
    const raw = values[key];
    if (raw === undefined || raw === '') return undefined;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : undefined;
  };

  switch (station) {
    case 'cmj':
      return { station, height_cm: num('height_cm') as number };
    case 'pogo':
      return {
        station,
        flight_time_ms: num('flight_time_ms'),
        contact_time_ms: num('contact_time_ms'),
        rsi: num('rsi'),
      };
    case 'landmine':
      return {
        station,
        load_kg: extras.load_kg as number,
        peak_velocity_ms: num('peak_velocity_ms'),
        mean_velocity_ms: num('mean_velocity_ms'),
        side: extras.side,
      };
    case 'grip':
    case 'trunk_rotation':
      return {
        station,
        left_kg: num('left_kg'),
        right_kg: num('right_kg'),
        rfd_left_n_s: num('rfd_left_n_s'),
        rfd_right_n_s: num('rfd_right_n_s'),
        // What the numbers above were typed in; the backend converts to N/s.
        rfd_unit: extras.rfd_unit,
      };
    case 'air_bike':
      return {
        station,
        sprint_number: extras.sprint_number ?? 1,
        power_7s: num('power_7s') as number,
        power_17s: num('power_17s') as number,
        power_27s: num('power_27s') as number,
        blood_lactate_mmol: num('blood_lactate_mmol'),
      };
  }
}

/** Live RSI as the operator types flight and contact — no waiting for the save. */
export function livePogoRsi(values: FieldValues): number | null {
  const flight = Number(values.flight_time_ms);
  const contact = Number(values.contact_time_ms);
  if (!Number.isFinite(flight) || !Number.isFinite(contact) || contact <= 0) return null;
  return Math.round((flight / contact) * 1000) / 1000;
}

/** Live left/right asymmetry, shown while the second side is typed. */
export function liveAsymmetry(values: FieldValues): number | null {
  const left = Number(values.left_kg);
  const right = Number(values.right_kg);
  if (!Number.isFinite(left) || !Number.isFinite(right)) return null;
  const stronger = Math.max(left, right);
  if (stronger <= 0) return null;
  return Math.round((Math.abs(left - right) / stronger) * 1000) / 10;
}

/**
 * The typed attempt reduced to the number the roster's `best_value` holds.
 *
 * The outlier guard compares against the cohort best, and the cohort best is the
 * station's ranked value — RSI, W/kg, the better side. Comparing raw flight time
 * with an RSI turned SAVE amber for every boxer after the first, which trains the
 * operator to tap through the one warning that matters.
 *
 * Returns null where no honest comparison exists: a bike sprint before weigh-in,
 * or a landmine throw at a load the board does not rank.
 */
export function guardValue(
  station: CombineStation,
  values: FieldValues,
  context: {
    bodyMassKg?: number | null;
    isReferenceLoad?: boolean;
    velocityMetric?: 'peak' | 'mean';
  } = {}
): number | null {
  const num = (key: string): number | null => {
    const parsed = Number(values[key]);
    return values[key] && Number.isFinite(parsed) ? parsed : null;
  };

  switch (station) {
    case 'cmj':
      return num('height_cm');
    case 'pogo':
      return livePogoRsi(values) ?? num('rsi');
    case 'landmine': {
      if (!context.isReferenceLoad) return null;
      return num(velocityKey({ rfd_unit: 'n_s', landmine_velocity_metric: context.velocityMetric ?? 'peak' }));
    }
    case 'grip':
    case 'trunk_rotation': {
      const sides = [num('left_kg'), num('right_kg')].filter(
        (value): value is number => value != null
      );
      return sides.length ? Math.max(...sides) : null;
    }
    case 'air_bike': {
      const power = num('power_7s');
      const mass = context.bodyMassKg;
      if (power == null || !mass || mass <= 0) return null;
      return power / mass;
    }
  }
}

/**
 * Flags a value far above everything logged so far.
 *
 * Catches the missed decimal point — a 412 cm jump would otherwise own the big
 * screen for the rest of the day.
 */
export function isImplausible(value: number, cohortMax: number | null | undefined): boolean {
  if (cohortMax == null || cohortMax <= 0) return false;
  return value > cohortMax * 1.5;
}

/**
 * A UUID for `client_attempt_id`, which is what makes a retry idempotent.
 *
 * `crypto.randomUUID` needs a secure context, so it is missing on a rehearsal iPad
 * pointed at the dev server over plain http on the gym LAN — and there it throws
 * inside SAVE, losing the attempt entirely. The fallback keeps the station working.
 */
export function newClientAttemptId(): string {
  const webCrypto = typeof crypto !== 'undefined' ? crypto : undefined;
  if (webCrypto?.randomUUID) return webCrypto.randomUUID();

  const bytes = new Uint8Array(16);
  if (webCrypto?.getRandomValues) {
    webCrypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < bytes.length; i += 1) bytes[i] = Math.floor(Math.random() * 256);
  }
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 1

  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  return [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ].join('-');
}
