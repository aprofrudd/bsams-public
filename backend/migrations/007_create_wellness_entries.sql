-- Migration: 007_create_wellness_entries
-- Description: Creates the wellness_entries table for daily wellness questionnaires
-- Run this in Supabase SQL Editor

-- Create wellness_entries table
CREATE TABLE IF NOT EXISTS wellness_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    entry_date DATE NOT NULL,
    sleep_quality INTEGER NOT NULL CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
    fatigue INTEGER NOT NULL CHECK (fatigue >= 1 AND fatigue <= 5),
    soreness INTEGER NOT NULL CHECK (soreness >= 1 AND soreness <= 5),
    stress INTEGER NOT NULL CHECK (stress >= 1 AND stress <= 5),
    mood INTEGER NOT NULL CHECK (mood >= 1 AND mood <= 5),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, entry_date)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_wellness_entries_athlete_id ON wellness_entries(athlete_id);
CREATE INDEX IF NOT EXISTS idx_wellness_entries_entry_date ON wellness_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_wellness_entries_athlete_date ON wellness_entries(athlete_id, entry_date);

-- Enable RLS
ALTER TABLE wellness_entries ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Coaches can view wellness entries for their own athletes
CREATE POLICY "Coaches can view own athletes wellness entries"
    ON wellness_entries
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = wellness_entries.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can insert wellness entries for their own athletes
CREATE POLICY "Coaches can insert own athletes wellness entries"
    ON wellness_entries
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = wellness_entries.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can update wellness entries for their own athletes
CREATE POLICY "Coaches can update own athletes wellness entries"
    ON wellness_entries
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = wellness_entries.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can delete wellness entries for their own athletes
CREATE POLICY "Coaches can delete own athletes wellness entries"
    ON wellness_entries
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = wellness_entries.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at
CREATE TRIGGER update_wellness_entries_updated_at
    BEFORE UPDATE ON wellness_entries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
