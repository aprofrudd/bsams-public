-- Migration 023: Per-rep rest intervals
-- Adds JSONB array column for per-rep rest durations (parallel to rep_durations)
-- Run on Supabase SQL editor

-- exercise_prescriptions
ALTER TABLE exercise_prescriptions
  ADD COLUMN rest_between_reps JSONB;

-- exercise_library
ALTER TABLE exercise_library
  ADD COLUMN default_rest_between_reps JSONB;

-- template_exercises
ALTER TABLE template_exercises
  ADD COLUMN rest_between_reps JSONB;
