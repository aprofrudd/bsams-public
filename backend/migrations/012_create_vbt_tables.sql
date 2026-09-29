-- Migration: 012_create_vbt_tables
-- Description: Creates vbt_profiles and vbt_sets tables for load-velocity profiling
-- Run this in Supabase SQL Editor

-- Create vbt_profiles table
CREATE TABLE IF NOT EXISTS vbt_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    exercise_name TEXT NOT NULL,
    profile_date DATE NOT NULL,
    mvt_ms NUMERIC(5,3),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, exercise_name, profile_date)
);

-- Create vbt_sets table
CREATE TABLE IF NOT EXISTS vbt_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES vbt_profiles(id) ON DELETE CASCADE,
    set_number INTEGER NOT NULL DEFAULT 1,
    load_kg NUMERIC(6,2) NOT NULL,
    mean_velocity_ms NUMERIC(5,3),
    peak_velocity_ms NUMERIC(5,3),
    reps INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_vbt_profiles_athlete_id ON vbt_profiles(athlete_id);
CREATE INDEX IF NOT EXISTS idx_vbt_profiles_athlete_exercise ON vbt_profiles(athlete_id, exercise_name);
CREATE INDEX IF NOT EXISTS idx_vbt_sets_profile_id ON vbt_sets(profile_id);

-- Enable RLS
ALTER TABLE vbt_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE vbt_sets ENABLE ROW LEVEL SECURITY;

-- RLS Policies for vbt_profiles (coach owns via athletes.coach_id)
CREATE POLICY "Coaches can view own athletes vbt profiles"
    ON vbt_profiles
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = vbt_profiles.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes vbt profiles"
    ON vbt_profiles
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = vbt_profiles.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes vbt profiles"
    ON vbt_profiles
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = vbt_profiles.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes vbt profiles"
    ON vbt_profiles
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = vbt_profiles.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

-- RLS Policies for vbt_sets (coach owns via vbt_profiles → athletes chain)
CREATE POLICY "Coaches can view own athletes vbt sets"
    ON vbt_sets
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM vbt_profiles vp
            JOIN athletes a ON a.id = vp.athlete_id
            WHERE vp.id = vbt_sets.profile_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes vbt sets"
    ON vbt_sets
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM vbt_profiles vp
            JOIN athletes a ON a.id = vp.athlete_id
            WHERE vp.id = vbt_sets.profile_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes vbt sets"
    ON vbt_sets
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM vbt_profiles vp
            JOIN athletes a ON a.id = vp.athlete_id
            WHERE vp.id = vbt_sets.profile_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes vbt sets"
    ON vbt_sets
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM vbt_profiles vp
            JOIN athletes a ON a.id = vp.athlete_id
            WHERE vp.id = vbt_sets.profile_id
            AND a.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at on vbt_profiles
CREATE TRIGGER update_vbt_profiles_updated_at
    BEFORE UPDATE ON vbt_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
