-- Migration: 010_create_exercise_library
-- Description: Creates the exercise_library table for coach-level exercise database
-- Run this in Supabase SQL Editor

-- Create exercise_library table
CREATE TABLE IF NOT EXISTS exercise_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    exercise_name TEXT NOT NULL,
    exercise_category TEXT,
    default_reps INTEGER,
    default_weight_kg NUMERIC(6,2),
    default_tempo TEXT,
    default_rest_seconds INTEGER,
    default_duration_seconds INTEGER,
    default_distance_meters NUMERIC(8,2),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(coach_id, exercise_name)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_exercise_library_coach_id ON exercise_library(coach_id);
CREATE INDEX IF NOT EXISTS idx_exercise_library_coach_name ON exercise_library(coach_id, exercise_name);

-- Enable RLS
ALTER TABLE exercise_library ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Coaches can view their own exercises
CREATE POLICY "Coaches can view own exercise library"
    ON exercise_library
    FOR SELECT
    USING (coach_id = auth.uid());

-- RLS Policy: Coaches can insert their own exercises
CREATE POLICY "Coaches can insert own exercise library"
    ON exercise_library
    FOR INSERT
    WITH CHECK (coach_id = auth.uid());

-- RLS Policy: Coaches can update their own exercises
CREATE POLICY "Coaches can update own exercise library"
    ON exercise_library
    FOR UPDATE
    USING (coach_id = auth.uid());

-- RLS Policy: Coaches can delete their own exercises
CREATE POLICY "Coaches can delete own exercise library"
    ON exercise_library
    FOR DELETE
    USING (coach_id = auth.uid());

-- Trigger to auto-update updated_at
CREATE TRIGGER update_exercise_library_updated_at
    BEFORE UPDATE ON exercise_library
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
