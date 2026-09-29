-- Migration: 002_create_athletes_table
-- Description: Creates the athletes table
-- Run this in Supabase SQL Editor

-- Create athletes table
CREATE TABLE IF NOT EXISTS athletes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    gender TEXT NOT NULL CHECK (gender IN ('male', 'female')),
    date_of_birth DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_athletes_coach_id ON athletes(coach_id);
CREATE INDEX IF NOT EXISTS idx_athletes_name ON athletes(name);

-- Enable RLS
ALTER TABLE athletes ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Coaches can only view their own athletes
CREATE POLICY "Coaches can view own athletes"
    ON athletes
    FOR SELECT
    USING (auth.uid() = coach_id);

-- RLS Policy: Coaches can insert their own athletes
CREATE POLICY "Coaches can insert own athletes"
    ON athletes
    FOR INSERT
    WITH CHECK (auth.uid() = coach_id);

-- RLS Policy: Coaches can update their own athletes
CREATE POLICY "Coaches can update own athletes"
    ON athletes
    FOR UPDATE
    USING (auth.uid() = coach_id);

-- RLS Policy: Coaches can delete their own athletes
CREATE POLICY "Coaches can delete own athletes"
    ON athletes
    FOR DELETE
    USING (auth.uid() = coach_id);

-- Trigger to auto-update updated_at
CREATE TRIGGER update_athletes_updated_at
    BEFORE UPDATE ON athletes
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
