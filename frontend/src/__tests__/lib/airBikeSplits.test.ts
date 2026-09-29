import {
  midSplitSeconds,
  midSplitLabel,
  sprintMidPower,
  sprintMidSeconds,
  sprintMaxPower,
  sprintPowers,
  splitTicks,
} from '@/lib/airBikeSplits';

const base = {
  id: 'sprint-1',
  test_id: 'test-1',
  sprint_number: 1,
  power_7s: 850,
  power_27s: 580,
  blood_lactate_mmol: null,
  created_at: '2026-09-03T00:00:00Z',
};

const sprint14 = { ...base, power_14s: 720, power_17s: null };
const sprint17 = { ...base, power_14s: null, power_17s: 700 };

describe('midSplitSeconds', () => {
  it('returns 14 for the original protocol', () => {
    expect(midSplitSeconds('7_14_27')).toBe(14);
  });

  it('returns 17 for the combine protocol', () => {
    expect(midSplitSeconds('7_17_27')).toBe(17);
  });

  it('defaults to 14 when the scheme is missing', () => {
    expect(midSplitSeconds(null)).toBe(14);
    expect(midSplitSeconds(undefined)).toBe(14);
  });
});

describe('sprintMidPower', () => {
  it('reads power_14s on a 7/14/27 sprint', () => {
    expect(sprintMidPower(sprint14)).toBe(720);
  });

  it('reads power_17s on a 7/17/27 sprint', () => {
    expect(sprintMidPower(sprint17)).toBe(700);
  });

  it('returns null when neither split is present', () => {
    expect(sprintMidPower({ power_14s: null, power_17s: null })).toBeNull();
  });
});

describe('sprintMidSeconds', () => {
  it('infers the split from the data, not the scheme', () => {
    expect(sprintMidSeconds(sprint17)).toBe(17);
    expect(sprintMidSeconds(sprint14)).toBe(14);
  });

  it('falls back to the scheme when no mid split was recorded', () => {
    expect(sprintMidSeconds({ power_14s: null, power_17s: null }, '7_17_27')).toBe(17);
  });
});

describe('sprintMaxPower', () => {
  it('does not treat a null mid split as a value (regression)', () => {
    expect(sprintMaxPower(sprint17)).toBe(850);
    expect(sprintMaxPower(sprint14)).toBe(850);
  });

  it('still finds the peak when the mid split is highest', () => {
    expect(sprintMaxPower({ ...sprint17, power_17s: 900 })).toBe(900);
  });

  it('works with only the two mandatory splits', () => {
    expect(sprintMaxPower({ ...base, power_14s: null, power_17s: null })).toBe(850);
  });
});

describe('sprintPowers', () => {
  it('skips the absent mid split rather than emitting null', () => {
    expect(sprintPowers({ ...base, power_14s: null, power_17s: null })).toEqual([850, 580]);
    expect(sprintPowers(sprint17)).toEqual([850, 700, 580]);
  });
});

describe('axis helpers', () => {
  it('produces ticks matching the protocol', () => {
    expect(splitTicks('7_14_27')).toEqual([7, 14, 27]);
    expect(splitTicks('7_17_27')).toEqual([7, 17, 27]);
  });

  it('labels the mid split', () => {
    expect(midSplitLabel('7_17_27')).toBe('17s');
  });
});
