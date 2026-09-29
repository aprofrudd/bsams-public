/**
 * Add / edit one boxer on a combine roster.
 *
 * The logic lives here rather than in the component so the validation rules — the
 * ones that stop a bad roster reaching the stations — can be tested directly.
 */

import type { AthleteUpdate, CombineParticipant, CombineRosterRow } from './types';

export interface ParticipantFormValues {
  first_name: string;
  surname: string;
  gender: '' | 'male' | 'female';
  bib: string;
  club: string;
  weight_category: string;
  age_group: string;
  body_mass_kg: string;
  withdrawn: boolean;
}

export const EMPTY_PARTICIPANT: ParticipantFormValues = {
  first_name: '',
  surname: '',
  gender: '',
  bib: '',
  club: '',
  weight_category: '',
  age_group: '',
  body_mass_kg: '',
  withdrawn: false,
};

/**
 * The 20 England Boxing amateur categories, ascending.
 *
 * Mirrors WEIGHT_CATEGORIES in backend/app/schemas/combine.py — the two lists must
 * stay in step, because the backend rejects anything outside this vocabulary and a
 * free-text division would sit in the board's filter chips matching one boxer.
 */
export const WEIGHT_CATEGORIES = [
  '46kg', '48kg', '50kg', '51kg', '52kg', '54kg', '56kg', '57kg',
  '60kg', '63.5kg', '64kg', '67kg', '69kg', '71kg', '75kg', '80kg',
  '81kg', '86kg', '91kg', '91+kg',
];

export const AGE_GROUP_SUGGESTIONS = ['Schoolboy/girl', 'Junior', 'Youth', 'Elite', 'Masters'];

/**
 * Map a typed weight category onto the England Boxing vocabulary.
 *
 * Rosters are pasted from spreadsheets, so "57", "57 kg", "57KG", "+91" and "91kg+"
 * all mean a category the board already knows. Anything else returns null, which the
 * caller turns into a rejected row. Mirrors `normalise_weight_category` in
 * backend/app/schemas/combine.py.
 */
export function normaliseWeightCategory(raw: string | null | undefined): string | null {
  if (raw == null) return null;
  let text = raw.trim().toLowerCase().replace(/\s/g, '').replace(/kg/g, '');
  const openEnded = text.includes('+');
  text = text.replace(/\+/g, '');
  if (!text) return null;
  const mass = Number(text);
  if (!Number.isFinite(mass)) return null;
  // 57.0 -> "57", 63.5 -> "63.5"
  const candidate = `${mass}${openEnded ? '+kg' : 'kg'}`;
  return WEIGHT_CATEGORIES.includes(candidate) ? candidate : null;
}

export type FormErrors = Partial<Record<keyof ParticipantFormValues, string>>;

/**
 * Validate the form.
 *
 * Only first name and gender are genuinely required — gender because the backend
 * needs it and the CSV path's silent "male" default is the wrong behaviour for a
 * mixed roster. Everything else can be filled in later from the same form.
 */
export function validateParticipant(
  values: ParticipantFormValues,
  opts?: { takenBibs?: number[]; currentBib?: number | null }
): FormErrors {
  const errors: FormErrors = {};

  if (!values.first_name.trim()) {
    errors.first_name = 'First name is required';
  }
  if (!values.gender) {
    errors.gender = 'Pick male or female';
  }

  if (values.bib.trim()) {
    const bib = Number(values.bib);
    if (!Number.isInteger(bib) || bib < 1 || bib > 9999) {
      errors.bib = 'Bib must be a whole number between 1 and 9999';
    } else if (
      opts?.takenBibs?.includes(bib) &&
      bib !== (opts?.currentBib ?? null)
    ) {
      errors.bib = `Bib ${bib} is already taken`;
    }
  }

  if (values.body_mass_kg.trim()) {
    const mass = Number(values.body_mass_kg);
    if (!Number.isFinite(mass) || mass <= 0 || mass > 300) {
      errors.body_mass_kg = 'Body mass must be between 0 and 300 kg';
    }
  }

  // Caught here rather than at save time: the backend is strict, and a 422 after
  // the boxer has walked away is no use to anyone.
  if (values.weight_category.trim() && normaliseWeightCategory(values.weight_category) === null) {
    errors.weight_category = 'Pick a weight category from the list';
  }

  return errors;
}

export function hasErrors(errors: FormErrors): boolean {
  return Object.keys(errors).length > 0;
}

/** Form values -> the roster row the bulk-import endpoint accepts. */
export function toRosterRow(values: ParticipantFormValues): CombineRosterRow {
  const trimmed = (value: string) => {
    const out = value.trim();
    return out === '' ? undefined : out;
  };
  const numeric = (value: string) => {
    const parsed = Number(value.trim());
    return value.trim() !== '' && Number.isFinite(parsed) ? parsed : undefined;
  };
  const category = values.weight_category.trim();

  return {
    first_name: values.first_name.trim(),
    surname: trimmed(values.surname),
    gender: values.gender as 'male' | 'female',
    club: trimmed(values.club),
    // An unrecognised value is sent as typed so the import rejects that row by
    // name, rather than the form quietly dropping what the coach entered.
    weight_category: category ? normaliseWeightCategory(category) ?? category : undefined,
    age_group: trimmed(values.age_group),
    body_mass_kg: numeric(values.body_mass_kg),
    bib: numeric(values.bib),
  };
}

/** Existing participant -> form values, for the edit case. */
export function fromParticipant(participant: CombineParticipant): ParticipantFormValues {
  // Prefer the athlete's stored name parts. Splitting the display name guesses,
  // and the guess is wrong for "Ana Maria Lopez" — whose first name is "Ana Maria".
  const storedFirst = (participant.first_name ?? '').trim();
  const storedSurname = (participant.surname ?? '').trim();
  const name = (participant.name || '').trim();
  const spaceAt = name.indexOf(' ');
  const hasParts = Boolean(storedFirst || storedSurname);

  return {
    first_name: hasParts ? storedFirst : spaceAt === -1 ? name : name.slice(0, spaceAt),
    surname: hasParts ? storedSurname : spaceAt === -1 ? '' : name.slice(spaceAt + 1),
    gender: participant.gender ?? '',
    bib: participant.bib != null ? String(participant.bib) : '',
    club: participant.club ?? '',
    weight_category: participant.weight_category ?? '',
    age_group: participant.age_group ?? '',
    body_mass_kg: participant.body_mass_kg != null ? String(participant.body_mass_kg) : '',
    withdrawn: participant.withdrawn_at != null,
  };
}

/** Only the fields the participant PATCH endpoint accepts. */
export function toParticipantUpdate(values: ParticipantFormValues) {
  // null, not undefined: JSON.stringify drops undefined, and the endpoint patches
  // with exclude_unset, so an undefined club could never be cleared.
  const cleared = (value: string) => value.trim() || null;
  const category = values.weight_category.trim();

  const update: Record<string, unknown> = {
    club: cleared(values.club),
    weight_category: category ? normaliseWeightCategory(category) ?? category : null,
    age_group: cleared(values.age_group),
    withdrawn: values.withdrawn,
  };
  if (values.bib.trim()) update.bib = Number(values.bib);
  if (values.body_mass_kg.trim()) update.body_mass_kg = Number(values.body_mass_kg);
  return update;
}

/**
 * The athlete-record half of an edit — or null when nothing on it changed.
 *
 * Name, gender and body mass live on the athlete, not the roster entry, so a
 * weigh-in used to PATCH all of them every time. That rewrote names: the form is
 * seeded by splitting a display name when the record has no stored parts, and
 * saving wrote the guess back. Comparing against what seeded the form means an
 * untouched field is never sent.
 */
export function toAthleteUpdate(
  values: ParticipantFormValues,
  participant: CombineParticipant
): AthleteUpdate | null {
  const current = fromParticipant(participant);
  const update: AthleteUpdate = {};

  const firstName = values.first_name.trim();
  if (firstName && firstName !== current.first_name.trim()) update.first_name = firstName;

  const surname = values.surname.trim();
  if (surname !== current.surname.trim()) update.surname = surname;

  if (values.gender && values.gender !== current.gender) update.gender = values.gender;

  const mass = Number(values.body_mass_kg.trim());
  if (values.body_mass_kg.trim() && Number.isFinite(mass) && mass !== participant.body_mass_kg) {
    update.body_mass_kg = mass;
  }

  return Object.keys(update).length > 0 ? update : null;
}
