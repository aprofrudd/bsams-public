-- Migration 022: Add per-rep durations support
-- Allows variable durations per rep within a set (e.g., pyramid intervals: 15s, 30s, 45s, 60s)

-- Exercise prescriptions: per-rep durations for individual exercises in a session
ALTER TABLE exercise_prescriptions
  ADD COLUMN IF NOT EXISTS rep_durations JSONB;

-- Exercise library: default per-rep durations template
ALTER TABLE exercise_library
  ADD COLUMN IF NOT EXISTS default_rep_durations JSONB;

-- Template exercises: per-rep durations in session templates
ALTER TABLE template_exercises
  ADD COLUMN IF NOT EXISTS rep_durations JSONB;
