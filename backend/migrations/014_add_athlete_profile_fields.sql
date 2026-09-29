-- Migration 014: Add athlete profile fields
-- Adds first_name, surname, body_mass_kg, stature_cm, status, notes to athletes table
-- Includes trigger to sync name from first_name + surname

ALTER TABLE athletes ADD COLUMN IF NOT EXISTS first_name TEXT;
ALTER TABLE athletes ADD COLUMN IF NOT EXISTS surname TEXT;
ALTER TABLE athletes ADD COLUMN IF NOT EXISTS body_mass_kg DECIMAL;
ALTER TABLE athletes ADD COLUMN IF NOT EXISTS stature_cm DECIMAL;
ALTER TABLE athletes ADD COLUMN IF NOT EXISTS status TEXT CHECK (status IN ('amateur', 'professional'));
ALTER TABLE athletes ADD COLUMN IF NOT EXISTS notes TEXT;

-- Constraints
ALTER TABLE athletes ADD CONSTRAINT chk_first_name_length CHECK (char_length(first_name) <= 50);
ALTER TABLE athletes ADD CONSTRAINT chk_surname_length CHECK (char_length(surname) <= 50);
ALTER TABLE athletes ADD CONSTRAINT chk_body_mass_range CHECK (body_mass_kg > 0 AND body_mass_kg <= 500);
ALTER TABLE athletes ADD CONSTRAINT chk_stature_range CHECK (stature_cm > 0 AND stature_cm <= 300);

-- Trigger: sync name from first_name + surname
CREATE OR REPLACE FUNCTION sync_athlete_name() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.first_name IS NOT NULL THEN
    NEW.name = trim(NEW.first_name || ' ' || coalesce(NEW.surname, ''));
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_sync_athlete_name
  BEFORE INSERT OR UPDATE ON athletes
  FOR EACH ROW
  WHEN (NEW.first_name IS NOT NULL)
  EXECUTE FUNCTION sync_athlete_name();
