-- Migration: 013_create_movement_assessments
-- Description: Creates movement_assessments and assessment_photos tables for NASM movement screening
-- Run this in Supabase SQL Editor

-- Create movement_assessments table
CREATE TABLE IF NOT EXISTS movement_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL,
    assessment_type TEXT NOT NULL,
    findings JSONB NOT NULL DEFAULT '{}',
    notes TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, assessment_date, assessment_type)
);

-- Create assessment_photos table
CREATE TABLE IF NOT EXISTS assessment_photos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES movement_assessments(id) ON DELETE CASCADE,
    view_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_movement_assessments_athlete_id ON movement_assessments(athlete_id);
CREATE INDEX IF NOT EXISTS idx_assessment_photos_assessment_id ON assessment_photos(assessment_id);

-- Enable RLS
ALTER TABLE movement_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessment_photos ENABLE ROW LEVEL SECURITY;

-- RLS Policies for movement_assessments (coach owns via athletes.coach_id)
CREATE POLICY "Coaches can view own athletes movement assessments"
    ON movement_assessments
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = movement_assessments.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes movement assessments"
    ON movement_assessments
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = movement_assessments.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes movement assessments"
    ON movement_assessments
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = movement_assessments.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes movement assessments"
    ON movement_assessments
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = movement_assessments.athlete_id
            AND a.coach_id = auth.uid()
        )
    );

-- RLS Policies for assessment_photos (coach owns via movement_assessments → athletes chain)
CREATE POLICY "Coaches can view own athletes assessment photos"
    ON assessment_photos
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM movement_assessments ma
            JOIN athletes a ON a.id = ma.athlete_id
            WHERE ma.id = assessment_photos.assessment_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own athletes assessment photos"
    ON assessment_photos
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM movement_assessments ma
            JOIN athletes a ON a.id = ma.athlete_id
            WHERE ma.id = assessment_photos.assessment_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own athletes assessment photos"
    ON assessment_photos
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM movement_assessments ma
            JOIN athletes a ON a.id = ma.athlete_id
            WHERE ma.id = assessment_photos.assessment_id
            AND a.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own athletes assessment photos"
    ON assessment_photos
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM movement_assessments ma
            JOIN athletes a ON a.id = ma.athlete_id
            WHERE ma.id = assessment_photos.assessment_id
            AND a.coach_id = auth.uid()
        )
    );

-- Trigger to auto-update updated_at on movement_assessments
CREATE TRIGGER update_movement_assessments_updated_at
    BEFORE UPDATE ON movement_assessments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
