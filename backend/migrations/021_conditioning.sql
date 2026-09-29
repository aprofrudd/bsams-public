-- Migration 021: Conditioning & Interval Training fields
-- Run on Supabase SQL editor

-- exercise_prescriptions
ALTER TABLE exercise_prescriptions
  ADD COLUMN intensity_type TEXT CHECK (intensity_type IN ('rpe', 'speed_kmh', 'power_watts')),
  ADD COLUMN intensity_value NUMERIC,
  ADD COLUMN rest_between_reps_seconds INTEGER CHECK (rest_between_reps_seconds >= 0 AND rest_between_reps_seconds <= 600);

-- exercise_library
ALTER TABLE exercise_library
  ADD COLUMN default_intensity_type TEXT CHECK (default_intensity_type IN ('rpe', 'speed_kmh', 'power_watts')),
  ADD COLUMN default_intensity_value NUMERIC,
  ADD COLUMN default_rest_between_reps_seconds INTEGER CHECK (default_rest_between_reps_seconds >= 0 AND default_rest_between_reps_seconds <= 600);

-- template_exercises
ALTER TABLE template_exercises
  ADD COLUMN intensity_type TEXT CHECK (intensity_type IN ('rpe', 'speed_kmh', 'power_watts')),
  ADD COLUMN intensity_value NUMERIC,
  ADD COLUMN rest_between_reps_seconds INTEGER CHECK (rest_between_reps_seconds >= 0 AND rest_between_reps_seconds <= 600);
