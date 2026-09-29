import { parseRosterText } from '@/components/combine/RosterImport';

describe('parseRosterText', () => {
  it('parses comma separated rows', () => {
    const { rows, errors } = parseRosterText('Jack, Reid, M, Repton, 57kg, Junior, 57.2');
    expect(errors).toEqual([]);
    expect(rows[0]).toEqual({
      first_name: 'Jack',
      surname: 'Reid',
      gender: 'male',
      club: 'Repton',
      weight_category: '57kg',
      age_group: 'Junior',
      body_mass_kg: 57.2,
    });
  });

  it('parses tab separated rows pasted from a spreadsheet', () => {
    const { rows } = parseRosterText('Sam\tOkoro\tF\tGBB');
    expect(rows[0]).toMatchObject({ first_name: 'Sam', gender: 'female', club: 'GBB' });
  });

  it('skips a pasted header row', () => {
    const { rows } = parseRosterText('First name, Surname, Gender\nJack, Reid, M');
    expect(rows).toHaveLength(1);
  });

  it('reports a missing gender rather than guessing male', () => {
    const { rows, errors } = parseRosterText('Jack, Reid');
    expect(rows).toHaveLength(0);
    expect(errors[0]).toContain('gender must be M or F');
  });

  it('accepts full words for gender', () => {
    const { rows } = parseRosterText('Jack, Reid, Male');
    expect(rows[0].gender).toBe('male');
  });

  it('ignores blank lines', () => {
    const { rows } = parseRosterText('Jack, Reid, M\n\n\nSam, Okoro, F\n');
    expect(rows).toHaveLength(2);
  });

  it('leaves body mass undefined when it is not a number', () => {
    const { rows } = parseRosterText('Jack, Reid, M, Repton, 57kg, Junior, tbc');
    expect(rows[0].body_mass_kg).toBeUndefined();
  });

  it('normalises a weight category typed without the kg', () => {
    // Spreadsheets hold "57"; the board filters on "57kg".
    const { rows } = parseRosterText('Jack, Reid, M, Repton, 57');
    expect(rows[0].weight_category).toBe('57kg');
  });

  it('normalises an open-ended category however it is typed', () => {
    const { rows } = parseRosterText('Jack, Reid, M, Repton, +91');
    expect(rows[0].weight_category).toBe('91+kg');
  });

  it('rejects a division that does not exist instead of importing it', () => {
    const { rows, errors } = parseRosterText('Jack, Reid, M, Repton, 58kg');
    expect(rows).toHaveLength(0);
    expect(errors[0]).toContain('weight category');
  });

  it('leaves a blank weight category alone', () => {
    const { rows, errors } = parseRosterText('Jack, Reid, M, Repton');
    expect(errors).toEqual([]);
    expect(rows[0].weight_category).toBeUndefined();
  });
});
