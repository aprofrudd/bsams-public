-- Migration: 008_create_exercise_prescriptions
-- Description: Creates the exercise_prescriptions table for session exercise details
-- Run this in Supabase SQL Editor

-- Create exercise_prescriptions table
CREATE TABLE IF NOT EXISTS exercise_prescriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES training_sessions(id) ON DELETE CASCADE,
    exercise_name TEXT NOT NULL,
    exercise_category TEXT,
    set_number INTEGER NOT NULL,
    reps INTEGER,
    weight_kg NUMERIC(6,2),
    tempo TEXT,
    rest_seconds INTEGER,
    duration_seconds INTEGER,
    distance_meters NUMERIC(8,2),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_exercise_prescriptions_session_id ON exercise_prescriptions(session_id);

-- Enable RLS
ALTER TABLE exercise_prescriptions ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Coaches can view exercises for their own athletes' sessions
CREATE POLICY "Coaches can view own athletes exercise prescriptions"
    ON exercise_prescriptions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM training_sessions ts
            JOIN athletes a ON a.id = ts.athlete_id
            WHERE ts.id = exercise_prescriptions.session_id
            AND a.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can insert exercises for their own athletes' sessions
CREATE POLICY "Coaches can insert own athletes exercise prescriptions"
    ON exercise_prescriptions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM training_sessions ts
            JOIN athletes a ON a.id = ts.athlete_id
            WHERE ts.id = exercise_prescriptions.session_id
            AND a.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can update exercises for their own athletes' sessions
CREATE POLICY "Coaches can update own athletes exercise prescriptions"
    ON exercise_prescriptions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM training_sessions ts
            JOIN athletes a ON a.id = ts.athlete_id
            WHERE ts.id = exercise_prescriptions.session_id
            AND a.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can delete exercises for their own athletes' sessions
CREATE POLICY "Coaches can delete own athletes exercise prescriptions"
    ON exercise_prescriptions
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM training_sessions ts
            JOIN athletes a ON a.id = ts.athlete_id
            WHERE ts.id = exercise_prescriptions.session_id
            AND a.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at
CREATE TRIGGER update_exercise_prescriptions_updated_at
    BEFORE UPDATE ON exercise_prescriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
