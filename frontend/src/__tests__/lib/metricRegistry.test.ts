import { METRIC_DEFINITIONS } from '@/lib/metricRegistry';

const isometricKeys = METRIC_DEFINITIONS.filter((m) => m.group === 'isometric').map((m) => m.key);
const jumpKeys = METRIC_DEFINITIONS.filter((m) => m.group === 'jump').map((m) => m.key);

describe('metric registry ordering', () => {
  it('keeps iso_trunk_rotation_left_kg first in the isometric group', () => {
    // testing/page.tsx defaults the Isometrics tab to ISOMETRIC_METRIC_KEYS[0].
    // New isometric keys must be appended, never inserted.
    expect(isometricKeys[0]).toBe('iso_trunk_rotation_left_kg');
  });

  it('keeps the original six isometric keys in their original order', () => {
    expect(isometricKeys.slice(0, 6)).toEqual([
      'iso_trunk_rotation_left_kg',
      'iso_trunk_rotation_right_kg',
      'grip_strength_left_kg',
      'grip_strength_right_kg',
      'grip_rfd_left_pct',
      'grip_rfd_right_pct',
    ]);
  });
});

describe('combine metric keys', () => {
  it('exposes the 10-5 pogo keys in the jump group', () => {
    expect(jumpKeys).toEqual(
      expect.arrayContaining(['pogo_flight_time_ms', 'pogo_contact_time_ms', 'pogo_rsi'])
    );
  });

  it('keeps pogo RSI separate from CMJ RSI', () => {
    expect(jumpKeys).toContain('rsi');
    expect(jumpKeys).toContain('pogo_rsi');
  });

  it('marks pogo contact time as lower-is-better', () => {
    const contact = METRIC_DEFINITIONS.find((m) => m.key === 'pogo_contact_time_ms');
    expect(contact?.higherIsBetter).toBe(false);
  });

  it('exposes the optional RFD keys in N/s', () => {
    expect(isometricKeys).toEqual(
      expect.arrayContaining([
        'grip_rfd_left_n_s',
        'grip_rfd_right_n_s',
        'iso_trunk_rotation_rfd_left_n_s',
        'iso_trunk_rotation_rfd_right_n_s',
      ])
    );
  });
});
