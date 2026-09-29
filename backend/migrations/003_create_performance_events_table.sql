-- Migration: 003_create_performance_events_table
-- Description: Creates the performance_events table with JSONB metrics
-- Run this in Supabase SQL Editor

-- Create performance_events table
CREATE TABLE IF NOT EXISTS performance_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    event_date DATE NOT NULL,
    metrics JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_performance_events_athlete_id ON performance_events(athlete_id);
CREATE INDEX IF NOT EXISTS idx_performance_events_event_date ON performance_events(event_date);

-- GIN index on metrics for fast JSONB querying
CREATE INDEX IF NOT EXISTS idx_performance_events_metrics ON performance_events USING GIN (metrics);

-- Enable RLS
ALTER TABLE performance_events ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Coaches can view events for their own athletes
CREATE POLICY "Coaches can view own athletes events"
    ON performance_events
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = performance_events.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can insert events for their own athletes
CREATE POLICY "Coaches can insert own athletes events"
    ON performance_events
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = performance_events.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can update events for their own athletes
CREATE POLICY "Coaches can update own athletes events"
    ON performance_events
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = performance_events.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- RLS Policy: Coaches can delete events for their own athletes
CREATE POLICY "Coaches can delete own athletes events"
    ON performance_events
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM athletes
            WHERE athletes.id = performance_events.athlete_id
            AND athletes.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at
CREATE TRIGGER update_performance_events_updated_at
    BEFORE UPDATE ON performance_events
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
