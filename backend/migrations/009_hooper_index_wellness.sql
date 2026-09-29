-- Migration: 009_hooper_index_wellness
-- Description: Replaces 5-score wellness with Validated Hooper Index (4 items, 1-7 scale)
-- Hooper Index = sleep + fatigue + stress + doms (range 4-28, lower is better)
-- Run this in Supabase SQL Editor

-- Drop existing table (no production data yet)
DROP TABLE IF EXISTS wellness_entries CASCADE;

-- Recreate with Hooper Index schema
CREATE TABLE wellness_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    sleep INTEGER NOT NULL CHECK (sleep >= 1 AND sleep <= 7),
    fatigue INTEGER NOT NULL CHECK (fatigue >= 1 AND fatigue <= 7),
    stress INTEGER NOT NULL CHECK (stress >= 1 AND stress <= 7),
    doms INTEGER NOT NULL CHECK (doms >= 1 AND doms <= 7),
    hooper_index INTEGER GENERATED ALWAYS AS (sleep + fatigue + stress + doms) STORED,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, entry_date)
);

-- Create indexes
CREATE INDEX idx_wellness_entries_athlete_id ON wellness_entries(athlete_id);
CREATE INDEX idx_wellness_entries_entry_date ON wellness_entries(entry_date);
CREATE INDEX idx_wellness_entries_athlete_date ON wellness_entries(athlete_id, entry_date);

-- Enable RLS
ALTER TABLE wellness_entries ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Coaches can view own athletes wellness entries"
    ON wellness_entries FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM athletes
        WHERE athletes.id = wellness_entries.athlete_id
        AND athletes.coach_id = auth.uid()
    ));

CREATE POLICY "Coaches can insert own athletes wellness entries"
    ON wellness_entries FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM athletes
        WHERE athletes.id = wellness_entries.athlete_id
        AND athletes.coach_id = auth.uid()
    ));

CREATE POLICY "Coaches can update own athletes wellness entries"
    ON wellness_entries FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM athletes
        WHERE athletes.id = wellness_entries.athlete_id
        AND athletes.coach_id = auth.uid()
    ));

CREATE POLICY "Coaches can delete own athletes wellness entries"
    ON wellness_entries FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM athletes
        WHERE athletes.id = wellness_entries.athlete_id
        AND athletes.coach_id = auth.uid()
    ));

-- Trigger to auto-update updated_at
CREATE TRIGGER update_wellness_entries_updated_at
    BEFORE UPDATE ON wellness_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
