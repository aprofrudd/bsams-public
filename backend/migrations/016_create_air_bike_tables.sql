-- Migration: 016_create_air_bike_tables
-- Description: Creates air_bike_tests and air_bike_sprints tables for 30s sprint test
-- Run this in Supabase SQL Editor

-- Create air_bike_tests table
CREATE TABLE IF NOT EXISTS air_bike_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    test_date DATE NOT NULL,
    body_mass_kg NUMERIC(5,1) NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, test_date)
);

-- Create air_bike_sprints table
CREATE TABLE IF NOT EXISTS air_bike_sprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_id UUID NOT NULL REFERENCES air_bike_tests(id) ON DELETE CASCADE,
    sprint_number INTEGER NOT NULL CHECK (sprint_number IN (1, 2)),
    power_7s NUMERIC(7,1) NOT NULL,
    power_14s NUMERIC(7,1) NOT NULL,
    power_27s NUMERIC(7,1) NOT NULL,
    blood_lactate_mmol NUMERIC(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(test_id, sprint_number)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_air_bike_tests_athlete_id ON air_bike_tests(athlete_id);
CREATE INDEX IF NOT EXISTS idx_air_bike_sprints_test_id ON air_bike_sprints(test_id);

-- Enable RLS
ALTER TABLE air_bike_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE air_bike_sprints ENABLE ROW LEVEL SECURITY;

-- RLS Policies for air_bike_tests (coach owns via athletes.coach_id)
CREATE POLICY "Coaches can view own athletes air bike tests"
    ON air_bike_tests
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = air_bike_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes air bike tests"
    ON air_bike_tests
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = air_bike_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes air bike tests"
    ON air_bike_tests
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = air_bike_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes air bike tests"
    ON air_bike_tests
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = air_bike_tests.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

-- RLS Policies for air_bike_sprints (coach owns via air_bike_tests → athletes chain)
CREATE POLICY "Coaches can view own athletes air bike sprints"
    ON air_bike_sprints
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM air_bike_tests t
            JOIN athletes a ON a.id = t.athlete_id
            WHERE t.id = air_bike_sprints.test_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes air bike sprints"
    ON air_bike_sprints
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM air_bike_tests t
            JOIN athletes a ON a.id = t.athlete_id
            WHERE t.id = air_bike_sprints.test_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes air bike sprints"
    ON air_bike_sprints
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM air_bike_tests t
            JOIN athletes a ON a.id = t.athlete_id
            WHERE t.id = air_bike_sprints.test_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes air bike sprints"
    ON air_bike_sprints
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM air_bike_tests t
            JOIN athletes a ON a.id = t.athlete_id
            WHERE t.id = air_bike_sprints.test_id
            AND a.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at on air_bike_tests
CREATE TRIGGER update_air_bike_tests_updated_at
    BEFORE UPDATE ON air_bike_tests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
