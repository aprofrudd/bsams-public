-- Migration 031: Conditioning Templates
-- Adds description to sessions/templates, template_category/tier to session_templates,
-- and intensity_min/intensity_max range fields to exercise_prescriptions.

-- 1. Add description to training_sessions
ALTER TABLE training_sessions ADD COLUMN IF NOT EXISTS description TEXT;

-- 2. Add description, template_category, tier to session_templates
ALTER TABLE session_templates ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE session_templates ADD COLUMN IF NOT EXISTS template_category TEXT;
ALTER TABLE session_templates ADD COLUMN IF NOT EXISTS tier TEXT;

-- 3. Add intensity range fields to exercise_prescriptions
ALTER TABLE exercise_prescriptions ADD COLUMN IF NOT EXISTS intensity_min NUMERIC(7,1);
ALTER TABLE exercise_prescriptions ADD COLUMN IF NOT EXISTS intensity_max NUMERIC(7,1);
