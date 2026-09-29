-- Migration 024: Per-rep intensity values
-- Adds rep_intensity_values JSONB column to exercise_prescriptions,
-- exercise_library (as default_rep_intensity_values), and template_exercises.
-- Allows different intensity targets per rep (e.g. different speeds for each interval).

-- Exercise prescriptions
ALTER TABLE exercise_prescriptions
ADD COLUMN IF NOT EXISTS rep_intensity_values JSONB DEFAULT NULL;

-- Exercise library (defaults)
ALTER TABLE exercise_library
ADD COLUMN IF NOT EXISTS default_rep_intensity_values JSONB DEFAULT NULL;

-- Template exercises
ALTER TABLE template_exercises
ADD COLUMN IF NOT EXISTS rep_intensity_values JSONB DEFAULT NULL;
