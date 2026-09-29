-- Migration: 006_create_training_sessions
-- Description: Creates the training_sessions table for daily/weekly session logging
-- Run this in Supabase SQL Editor

-- Create training_sessions table
CREATE TABLE IF NOT EXISTS training_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    session_date DATE NOT NULL,
    training_type TEXT NOT NULL,
    duration_minutes INTEGER NOT NULL,
    rpe INTEGER NOT NULL CHECK (rpe >= 1 AND rpe <= 10),
    srpe INTEGER GENERATED ALWAYS AS (rpe * duration_minutes) STORED,
    notes TEXT,
    metrics JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_training_sessions_athlete_id ON training_sessions(athlete_id);
CREATE INDEX IF NOT EXISTS idx_training_sessions_session_date ON training_sessions(session_date);
CREATE INDEX IF NOT EXISTS idx_training_sessions_athlete_date ON training_sessions(athlete_id, session_date);

-- Enable RLS
ALTER TABLE training_sessions ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Coaches can view training sessions for their own athletes
CREATE POLICY "Coaches can view own athletes training sessions"
    ON training_sessions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = training_sessions.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can insert training sessions for their own athletes
CREATE POLICY "Coaches can insert own athletes training sessions"
    ON training_sessions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = training_sessions.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can update training sessions for their own athletes
CREATE POLICY "Coaches can update own athletes training sessions"
    ON training_sessions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = training_sessions.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can delete training sessions for their own athletes
CREATE POLICY "Coaches can delete own athletes training sessions"
    ON training_sessions
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = training_sessions.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at
CREATE TRIGGER update_training_sessions_updated_at
    BEFORE UPDATE ON training_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
