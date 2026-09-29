-- Migration: 015_create_lactate_tables
-- Description: Creates lactate_tests and lactate_stages tables for lactate threshold profiling
-- Run this in Supabase SQL Editor

-- Create lactate_tests table
CREATE TABLE IF NOT EXISTS lactate_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    test_date DATE NOT NULL,
    test_type TEXT NOT NULL CHECK (test_type IN ('running', 'cycling')),
    lt1_value NUMERIC(7,2),
    lt1_lactate NUMERIC(5,2),
    lt1_hr INTEGER,
    lt2_value NUMERIC(7,2),
    lt2_lactate NUMERIC(5,2),
    lt2_hr INTEGER,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, test_type, test_date)
);

-- Create lactate_stages table
CREATE TABLE IF NOT EXISTS lactate_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES lactate_tests(id) ON DELETE CASCADE,
    stage_number INTEGER NOT NULL DEFAULT 1,
    intensity_value NUMERIC(7,2) NOT NULL,
    heart_rate_bpm INTEGER,
    blood_lactate_mmol NUMERIC(5,2) NOT NULL,
    rpe NUMERIC(3,1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_lactate_tests_athlete_id ON lactate_tests(athlete_id);
CREATE INDEX IF NOT EXISTS idx_lactate_tests_athlete_type ON lactate_tests(athlete_id, test_type);
CREATE INDEX IF NOT EXISTS idx_lactate_stages_test_id ON lactate_stages(test_id);

-- Enable RLS
ALTER TABLE lactate_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE lactate_stages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for lactate_tests (coach owns via athletes.coach_id)
CREATE POLICY "Coaches can view own athletes lactate tests"
    ON lactate_tests
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = lactate_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes lactate tests"
    ON lactate_tests
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = lactate_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes lactate tests"
    ON lactate_tests
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = lactate_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes lactate tests"
    ON lactate_tests
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = lactate_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

-- RLS Policies for lactate_stages (coach owns via lactate_tests → athletes chain)
CREATE POLICY "Coaches can view own athletes lactate stages"
    ON lactate_stages
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM lactate_tests lt
            JOIN athletes a ON a.id = lt.athlete_id
            WHERE lt.id = lactate_stages.test_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes lactate stages"
    ON lactate_stages
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM lactate_tests lt
            JOIN athletes a ON a.id = lt.athlete_id
            WHERE lt.id = lactate_stages.test_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes lactate stages"
    ON lactate_stages
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM lactate_tests lt
            JOIN athletes a ON a.id = lt.athlete_id
            WHERE lt.id = lactate_stages.test_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes lactate stages"
    ON lactate_stages
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM lactate_tests lt
            JOIN athletes a ON a.id = lt.athlete_id
            WHERE lt.id = lactate_stages.test_id
            AND a.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at on lactate_tests
CREATE TRIGGER update_lactate_tests_updated_at
    BEFORE UPDATE ON lactate_tests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
