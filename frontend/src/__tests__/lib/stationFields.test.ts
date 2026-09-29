import {
  buildMeasures,
  guardValue,
  isImplausible,
  liveAsymmetry,
  livePogoRsi,
  missingRequired,
  newClientAttemptId,
  rangeError,
  stationFields,
} from '@/components/combine/stations/stationFields';

const PEAK = { rfd_unit: 'n_s', landmine_velocity_metric: 'peak' } as const;
const MEAN = { rfd_unit: 'n_s', landmine_velocity_metric: 'mean' } as const;
const KG_S = { rfd_unit: 'kg_s', landmine_velocity_metric: 'peak' } as const;

describe('missingRequired', () => {
  it('requires a jump height for CMJ', () => {
    expect(missingRequired('cmj', {})).toEqual(['height_cm']);
    expect(missingRequired('cmj', { height_cm: '41.2' })).toEqual([]);
  });

  it('accepts either the flight/contact pair or a direct RSI', () => {
    expect(missingRequired('pogo', {})).toHaveLength(2);
    expect(missingRequired('pogo', { flight_time_ms: '480' })).toHaveLength(2);
    expect(missingRequired('pogo', { flight_time_ms: '480', contact_time_ms: '192' })).toEqual([]);
    expect(missingRequired('pogo', { rsi: '2.5' })).toEqual([]);
  });

  it('accepts a single side for the dynamometer stations', () => {
    expect(missingRequired('grip', {})).toHaveLength(2);
    expect(missingRequired('grip', { right_kg: '50' })).toEqual([]);
    expect(missingRequired('trunk_rotation', { left_kg: '80' })).toEqual([]);
  });

  it('requires all three splits on the bike', () => {
    expect(missingRequired('air_bike', { power_7s: '855', power_17s: '700' })).toEqual([
      'power_27s',
    ]);
  });

  it('treats lactate as optional', () => {
    expect(
      missingRequired('air_bike', { power_7s: '855', power_17s: '700', power_27s: '600' })
    ).toEqual([]);
  });

  it('requires the landmine velocity the event ranks on, not either one', () => {
    // A mean-velocity event given only a peak reading ranks nobody, and the
    // router rejects it — so SAVE must not be reachable.
    expect(missingRequired('landmine', { peak_velocity_ms: '4.2' }, MEAN)).toEqual([
      'mean_velocity_ms',
    ]);
    expect(missingRequired('landmine', { mean_velocity_ms: '2.1' }, MEAN)).toEqual([]);
    expect(missingRequired('landmine', { mean_velocity_ms: '2.1' }, PEAK)).toEqual([
      'peak_velocity_ms',
    ]);
    expect(missingRequired('landmine', { peak_velocity_ms: '4.2' }, PEAK)).toEqual([]);
  });
});

describe('stationFields', () => {
  it('puts the ranked landmine velocity first and makes the other optional', () => {
    const fields = stationFields('landmine', MEAN);
    expect(fields[0].key).toBe('mean_velocity_ms');
    expect(fields[0].optional).toBeFalsy();
    expect(fields.find((f) => f.key === 'peak_velocity_ms')?.optional).toBe(true);
  });

  it('labels RFD in the unit the event dynamometer reads', () => {
    const n_s = stationFields('grip', PEAK).find((f) => f.key === 'rfd_left_n_s');
    expect(n_s?.unit).toBe('N/s');
    expect(n_s?.max).toBe(20000);

    const kg_s = stationFields('grip', KG_S).find((f) => f.key === 'rfd_left_n_s');
    expect(kg_s?.unit).toBe('kg/s');
    // 20000 N/s is the stored ceiling, so the typed kg/s ceiling is that ÷ g.
    expect(kg_s?.max).toBe(2039);
  });

  it('mirrors the backend ranges, exclusive zeros included', () => {
    const height = stationFields('cmj', PEAK)[0];
    expect(height).toMatchObject({ min: 0, max: 90, minExclusive: true });

    const lactate = stationFields('air_bike', PEAK).find(
      (f) => f.key === 'blood_lactate_mmol'
    );
    expect(lactate).toMatchObject({ min: 0, max: 30 });
    expect(lactate?.minExclusive).toBeFalsy();
  });
});

describe('rangeError', () => {
  it('rejects a zero in a gt=0 field before the backend has to', () => {
    expect(rangeError('cmj', { height_cm: '0' })).toMatch(/Jump Height/);
  });

  it('allows a zero where the schema does', () => {
    expect(
      rangeError('air_bike', {
        power_7s: '855',
        power_17s: '700',
        power_27s: '600',
        blood_lactate_mmol: '0',
      })
    ).toBeNull();
    expect(rangeError('grip', { left_kg: '45', rfd_left_n_s: '0' })).toBeNull();
  });

  it('catches a value above the ceiling', () => {
    expect(rangeError('cmj', { height_cm: '92' })).toMatch(/90/);
  });

  it('says nothing about a half-typed decimal', () => {
    // The keypad turns a leading "." into "0.", which reads as zero mid-typing.
    expect(rangeError('landmine', { peak_velocity_ms: '0.' })).toBeNull();
  });

  it('applies the kg/s ceiling when that is what was typed', () => {
    expect(rangeError('grip', { left_kg: '45', rfd_left_n_s: '2500' }, KG_S)).toMatch(/kg\/s/);
    expect(rangeError('grip', { left_kg: '45', rfd_left_n_s: '2500' }, PEAK)).toBeNull();
  });

  it('ignores empty fields', () => {
    expect(rangeError('cmj', {})).toBeNull();
  });
});

describe('buildMeasures', () => {
  it('drops blank optional fields rather than sending zero', () => {
    const measures = buildMeasures('grip', { left_kg: '45', right_kg: '50' });
    expect(measures).toEqual({
      station: 'grip',
      left_kg: 45,
      right_kg: 50,
      rfd_left_n_s: undefined,
      rfd_right_n_s: undefined,
    });
  });

  it('tells the backend which unit the RFD numbers were typed in', () => {
    const measures = buildMeasures(
      'trunk_rotation',
      { left_kg: '80', rfd_left_n_s: '450' },
      { rfd_unit: 'kg_s' }
    );
    expect(measures).toMatchObject({ rfd_left_n_s: 450, rfd_unit: 'kg_s' });
  });

  it('carries the selected load and side for the landmine station', () => {
    const measures = buildMeasures(
      'landmine',
      { peak_velocity_ms: '4.2' },
      { load_kg: 20, side: 'right' }
    );
    expect(measures).toMatchObject({
      station: 'landmine',
      load_kg: 20,
      peak_velocity_ms: 4.2,
      side: 'right',
    });
  });

  it('carries the sprint number for the bike', () => {
    const measures = buildMeasures(
      'air_bike',
      { power_7s: '855', power_17s: '700', power_27s: '600' },
      { sprint_number: 2 }
    );
    expect(measures).toMatchObject({ station: 'air_bike', sprint_number: 2, power_17s: 700 });
  });
});

describe('live feedback', () => {
  it('shows RSI as flight and contact are typed', () => {
    expect(livePogoRsi({ flight_time_ms: '480', contact_time_ms: '192' })).toBe(2.5);
  });

  it('shows nothing until both pogo values exist', () => {
    expect(livePogoRsi({ flight_time_ms: '480' })).toBeNull();
  });

  it('never divides by a zero contact time', () => {
    expect(livePogoRsi({ flight_time_ms: '480', contact_time_ms: '0' })).toBeNull();
  });

  it('shows asymmetry once both sides exist', () => {
    expect(liveAsymmetry({ left_kg: '45', right_kg: '50' })).toBe(10);
  });

  it('shows nothing with one side', () => {
    expect(liveAsymmetry({ left_kg: '45' })).toBeNull();
  });
});

describe('isImplausible', () => {
  it('flags a missed decimal point', () => {
    expect(isImplausible(412, 45)).toBe(true);
  });

  it('accepts a genuinely good result', () => {
    expect(isImplausible(48, 45)).toBe(false);
  });

  it('does not flag anything before there is a cohort to compare with', () => {
    expect(isImplausible(412, null)).toBe(false);
  });
});

describe('guardValue', () => {
  it('compares pogo on RSI, which is what the cohort best holds', () => {
    // 480 ms of flight beside a cohort best of 2.5 RSI is not an outlier.
    expect(guardValue('pogo', { flight_time_ms: '480', contact_time_ms: '192' })).toBe(2.5);
  });

  it('falls back to a directly entered RSI', () => {
    expect(guardValue('pogo', { rsi: '2.5' })).toBe(2.5);
  });

  it('compares the bike in W/kg, and skips it without a body mass', () => {
    expect(
      guardValue('air_bike', { power_7s: '855' }, { bodyMassKg: 57 })
    ).toBeCloseTo(15.0, 1);
    expect(guardValue('air_bike', { power_7s: '855' }, { bodyMassKg: null })).toBeNull();
  });

  it('compares the better side on the dynamometers', () => {
    expect(guardValue('grip', { left_kg: '45', right_kg: '52' })).toBe(52);
    expect(guardValue('trunk_rotation', { right_kg: '80' })).toBe(80);
  });

  it('only guards the landmine at the reference load', () => {
    const values = { peak_velocity_ms: '4.2' };
    expect(guardValue('landmine', values, { isReferenceLoad: true })).toBe(4.2);
    expect(guardValue('landmine', values, { isReferenceLoad: false })).toBeNull();
  });

  it('guards a mean-velocity event on mean velocity', () => {
    expect(
      guardValue(
        'landmine',
        { peak_velocity_ms: '4.2', mean_velocity_ms: '2.1' },
        { isReferenceLoad: true, velocityMetric: 'mean' }
      )
    ).toBe(2.1);
  });
});

describe('newClientAttemptId', () => {
  it('mints a distinct UUID even where crypto.randomUUID is missing', () => {
    // Secure-context only: a rehearsal iPad on the gym LAN over plain http has no
    // crypto.randomUUID, and a station that throws on SAVE is the worst outcome.
    const first = newClientAttemptId();
    expect(first).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(newClientAttemptId()).not.toBe(first);
  });
});
