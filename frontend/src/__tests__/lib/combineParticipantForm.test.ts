import {
  EMPTY_PARTICIPANT,
  WEIGHT_CATEGORIES,
  fromParticipant,
  hasErrors,
  normaliseWeightCategory,
  toAthleteUpdate,
  toParticipantUpdate,
  toRosterRow,
  validateParticipant,
} from '@/lib/combineParticipantForm';
import type { CombineParticipant } from '@/lib/types';

const valid = { ...EMPTY_PARTICIPANT, first_name: 'Jack', surname: 'Reid', gender: 'male' as const };

describe('WEIGHT_CATEGORIES', () => {
  it('mirrors WEIGHT_CATEGORIES in schemas/combine.py, in the same order', () => {
    // The two lists are the same vocabulary on both sides of the API: a value the
    // picker offers must be one the strict backend validator accepts.
    expect(WEIGHT_CATEGORIES).toEqual([
      '46kg', '48kg', '50kg', '51kg', '52kg', '54kg', '56kg', '57kg',
      '60kg', '63.5kg', '64kg', '67kg', '69kg', '71kg', '75kg', '80kg',
      '81kg', '86kg', '91kg', '91+kg',
    ]);
  });
});

describe('normaliseWeightCategory', () => {
  it.each([
    ['57', '57kg'],
    ['57 kg', '57kg'],
    ['57KG', '57kg'],
    ['  71  ', '71kg'],
    ['63.5', '63.5kg'],
    ['91+', '91+kg'],
    ['+91', '91+kg'],
    ['91kg+', '91+kg'],
  ])('maps %s onto the England Boxing vocabulary as %s', (raw, expected) => {
    expect(normaliseWeightCategory(raw)).toBe(expected);
  });

  it('returns null for a division that does not exist', () => {
    // A free-text division would sit in the board's filter chips matching one boxer.
    expect(normaliseWeightCategory('58kg')).toBeNull();
    expect(normaliseWeightCategory('heavyweight')).toBeNull();
  });

  it('returns null for blank or missing input', () => {
    expect(normaliseWeightCategory('')).toBeNull();
    expect(normaliseWeightCategory('   ')).toBeNull();
    expect(normaliseWeightCategory(null)).toBeNull();
    expect(normaliseWeightCategory(undefined)).toBeNull();
  });
});

describe('validateParticipant', () => {
  it('accepts a name and a gender alone — everything else can come later', () => {
    expect(validateParticipant(valid)).toEqual({});
  });

  it('requires a first name', () => {
    expect(validateParticipant({ ...valid, first_name: '  ' }).first_name).toMatch(/required/i);
  });

  it('requires gender rather than defaulting it', () => {
    // The CSV path silently defaults to male; that is wrong for a mixed roster.
    expect(validateParticipant({ ...valid, gender: '' }).gender).toMatch(/male or female/i);
  });

  it('rejects a bib that is already on the roster', () => {
    const errors = validateParticipant({ ...valid, bib: '7' }, { takenBibs: [7, 8] });
    expect(errors.bib).toMatch(/already taken/i);
  });

  it('lets a boxer keep their own bib when editing', () => {
    const errors = validateParticipant({ ...valid, bib: '7' }, { takenBibs: [7], currentBib: 7 });
    expect(errors.bib).toBeUndefined();
  });

  it('rejects a non-numeric or out-of-range bib', () => {
    expect(validateParticipant({ ...valid, bib: 'abc' }).bib).toBeDefined();
    expect(validateParticipant({ ...valid, bib: '0' }).bib).toBeDefined();
    expect(validateParticipant({ ...valid, bib: '10000' }).bib).toBeDefined();
  });

  it('allows a blank bib, which the server auto-assigns', () => {
    expect(validateParticipant({ ...valid, bib: '' }).bib).toBeUndefined();
  });

  it('rejects an implausible body mass', () => {
    expect(validateParticipant({ ...valid, body_mass_kg: '0' }).body_mass_kg).toBeDefined();
    expect(validateParticipant({ ...valid, body_mass_kg: '400' }).body_mass_kg).toBeDefined();
  });

  it('allows a blank body mass so a boxer can be added before weigh-in', () => {
    expect(validateParticipant({ ...valid, body_mass_kg: '' }).body_mass_kg).toBeUndefined();
  });

  it('rejects a weight category outside the England Boxing vocabulary', () => {
    const errors = validateParticipant({ ...valid, weight_category: '58kg' });
    expect(errors.weight_category).toMatch(/weight category/i);
  });

  it('accepts a category that only needs normalising', () => {
    expect(validateParticipant({ ...valid, weight_category: '57 kg' }).weight_category).toBeUndefined();
  });

  it('allows a blank weight category — it is filled in at weigh-in', () => {
    expect(validateParticipant({ ...valid, weight_category: '' }).weight_category).toBeUndefined();
  });

  it('hasErrors reflects the error map', () => {
    expect(hasErrors({})).toBe(false);
    expect(hasErrors({ first_name: 'x' })).toBe(true);
  });
});

describe('toRosterRow', () => {
  it('drops blank optional fields instead of sending empty strings', () => {
    expect(toRosterRow(valid)).toEqual({
      first_name: 'Jack',
      surname: 'Reid',
      gender: 'male',
      club: undefined,
      weight_category: undefined,
      age_group: undefined,
      body_mass_kg: undefined,
      bib: undefined,
    });
  });

  it('trims and converts what is filled in', () => {
    const row = toRosterRow({
      ...valid,
      club: '  Repton ',
      weight_category: '57kg',
      body_mass_kg: '57.2',
      bib: '12',
    });
    expect(row).toMatchObject({ club: 'Repton', weight_category: '57kg', body_mass_kg: 57.2, bib: 12 });
  });

  it('normalises the weight category on the way out', () => {
    expect(toRosterRow({ ...valid, weight_category: '57 kg' }).weight_category).toBe('57kg');
  });
});

describe('fromParticipant', () => {
  const participant = {
    id: 'p1',
    combine_event_id: 'e1',
    athlete_id: 'a1',
    name: 'Jack Reid',
    first_name: null,
    surname: null,
    gender: 'male',
    bib: 12,
    club: 'Repton',
    weight_category: '57kg',
    age_group: 'Junior',
    body_mass_kg: 57.2,
    squad: null,
    withdrawn_at: null,
    created_at: '2026-09-14T00:00:00Z',
  } as CombineParticipant;

  it('uses the stored name parts when the athlete record has them', () => {
    const values = fromParticipant({
      ...participant,
      name: 'Ana Maria Lopez',
      first_name: 'Ana Maria',
      surname: 'Lopez',
    });
    expect(values.first_name).toBe('Ana Maria');
    expect(values.surname).toBe('Lopez');
  });

  it('splits the stored name back into first and surname for a legacy row', () => {
    const values = fromParticipant(participant);
    expect(values.first_name).toBe('Jack');
    expect(values.surname).toBe('Reid');
  });

  it('keeps a double-barrelled surname intact', () => {
    const values = fromParticipant({ ...participant, name: 'Ana Maria Lopez Cruz' });
    expect(values.first_name).toBe('Ana');
    expect(values.surname).toBe('Maria Lopez Cruz');
  });

  it('handles a single-word name', () => {
    const values = fromParticipant({ ...participant, name: 'Kai' });
    expect(values.first_name).toBe('Kai');
    expect(values.surname).toBe('');
  });

  it('prefills gender so editing does not force it to be re-picked', () => {
    expect(fromParticipant(participant).gender).toBe('male');
  });

  it('leaves gender blank when the record has none', () => {
    expect(fromParticipant({ ...participant, gender: null }).gender).toBe('');
  });

  it('reflects a withdrawn boxer', () => {
    const values = fromParticipant({ ...participant, withdrawn_at: '2026-09-14T09:30:00Z' });
    expect(values.withdrawn).toBe(true);
  });
});

describe('toParticipantUpdate', () => {
  it('sends only the fields the participant endpoint owns', () => {
    const update = toParticipantUpdate({ ...valid, club: 'Repton', bib: '12', body_mass_kg: '57.2' });
    expect(update).toEqual({
      club: 'Repton',
      weight_category: null,
      age_group: null,
      withdrawn: false,
      bib: 12,
      body_mass_kg: 57.2,
    });
    expect(update).not.toHaveProperty('first_name');
  });

  it('sends null for a cleared text field so the console can empty it', () => {
    // undefined is dropped by JSON.stringify, and the endpoint patches with
    // exclude_unset — so an undefined club could never be cleared.
    const update = toParticipantUpdate({ ...valid, club: '', weight_category: '', age_group: '' });
    expect(update.club).toBeNull();
    expect(update.weight_category).toBeNull();
    expect(update.age_group).toBeNull();
  });

  it('normalises the weight category', () => {
    expect(toParticipantUpdate({ ...valid, weight_category: '91kg+' }).weight_category).toBe('91+kg');
  });

  it('passes an unrecognised category through for the server to reject', () => {
    // Silently clearing it would lose what the coach typed without saying so.
    expect(toParticipantUpdate({ ...valid, weight_category: '58kg' }).weight_category).toBe('58kg');
  });

  it('omits bib and body mass when they are blank rather than sending zero', () => {
    const update = toParticipantUpdate(valid);
    expect(update).not.toHaveProperty('bib');
    expect(update).not.toHaveProperty('body_mass_kg');
  });
});

describe('toAthleteUpdate', () => {
  const participant = {
    id: 'p1',
    combine_event_id: 'e1',
    athlete_id: 'a1',
    name: 'Ana Maria Lopez',
    first_name: 'Ana Maria',
    surname: 'Lopez',
    gender: 'female',
    bib: 12,
    club: 'Repton',
    weight_category: '57kg',
    age_group: 'Junior',
    body_mass_kg: null,
    squad: null,
    withdrawn_at: null,
    created_at: '2026-09-14T00:00:00Z',
  } as CombineParticipant;

  it('returns null when the weigh-in edit changed nothing on the athlete record', () => {
    expect(toAthleteUpdate(fromParticipant(participant), participant)).toBeNull();
  });

  it('never rewrites a name it was not asked to change', () => {
    // The bug: "Ana Maria Lopez" split to first "Ana", and the first weigh-in
    // PATCHed that back over the real first name.
    const values = { ...fromParticipant(participant), body_mass_kg: '58.4' };
    expect(toAthleteUpdate(values, participant)).toEqual({ body_mass_kg: 58.4 });
  });

  it('sends the name when the coach actually edits it', () => {
    const values = { ...fromParticipant(participant), surname: 'Lopez Cruz' };
    expect(toAthleteUpdate(values, participant)).toEqual({ surname: 'Lopez Cruz' });
  });

  it('sends gender when it is picked for a record that had none', () => {
    const unknownGender = { ...participant, gender: null } as CombineParticipant;
    const values = { ...fromParticipant(unknownGender), gender: 'female' as const };
    expect(toAthleteUpdate(values, unknownGender)).toEqual({ gender: 'female' });
  });

  it('ignores a body mass retyped as the same number', () => {
    const weighed = { ...participant, body_mass_kg: 57.2 } as CombineParticipant;
    const values = { ...fromParticipant(weighed), body_mass_kg: '57.20' };
    expect(toAthleteUpdate(values, weighed)).toBeNull();
  });

  it('does not write a split guess back to a legacy record nobody edited', () => {
    // A record with no stored parts seeds the form by splitting the display name.
    // Saving that guess is the rewrite this function exists to prevent.
    const legacy = { ...participant, first_name: null, surname: null } as CombineParticipant;
    const values = { ...fromParticipant(legacy), body_mass_kg: '58.4' };
    expect(toAthleteUpdate(values, legacy)).toEqual({ body_mass_kg: 58.4 });
  });

  it('sends a legacy name once the coach corrects it', () => {
    const legacy = { ...participant, first_name: null, surname: null } as CombineParticipant;
    const values = { ...fromParticipant(legacy), first_name: 'Ana Maria', surname: 'Lopez' };
    expect(toAthleteUpdate(values, legacy)).toEqual({ first_name: 'Ana Maria', surname: 'Lopez' });
  });
});
