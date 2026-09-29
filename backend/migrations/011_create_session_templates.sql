-- Migration: 011_create_session_templates
-- Description: Creates session_templates and template_exercises tables
-- Run this in Supabase SQL Editor

-- Create session_templates table
CREATE TABLE IF NOT EXISTS session_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    template_name TEXT NOT NULL,
    training_type TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(coach_id, template_name)
);

-- Create template_exercises table
CREATE TABLE IF NOT EXISTS template_exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID NOT NULL REFERENCES session_templates(id) ON DELETE CASCADE,
    exercise_library_id UUID REFERENCES exercise_library(id) ON DELETE SET NULL,
    exercise_name TEXT NOT NULL,
    exercise_category TEXT,
    order_index INTEGER NOT NULL DEFAULT 1,
    sets INTEGER DEFAULT 1,
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
CREATE INDEX IF NOT EXISTS idx_session_templates_coach_id ON session_templates(coach_id);
CREATE INDEX IF NOT EXISTS idx_template_exercises_template_id ON template_exercises(template_id);

-- Enable RLS
ALTER TABLE session_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_exercises ENABLE ROW LEVEL SECURITY;

-- RLS Policies for session_templates
CREATE POLICY "Coaches can view own session templates"
    ON session_templates
    FOR SELECT
    USING (coach_id = auth.uid());

CREATE POLICY "Coaches can insert own session templates"
    ON session_templates
    FOR INSERT
    WITH CHECK (coach_id = auth.uid());

CREATE POLICY "Coaches can update own session templates"
    ON session_templates
    FOR UPDATE
    USING (coach_id = auth.uid());

CREATE POLICY "Coaches can delete own session templates"
    ON session_templates
    FOR DELETE
    USING (coach_id = auth.uid());

-- RLS Policies for template_exercises (via join to session_templates)
CREATE POLICY "Coaches can view own template exercises"
    ON template_exercises
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM session_templates st
            WHERE st.id = template_exercises.template_id
            AND st.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can insert own template exercises"
    ON template_exercises
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM session_templates st
            WHERE st.id = template_exercises.template_id
            AND st.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can update own template exercises"
    ON template_exercises
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM session_templates st
            WHERE st.id = template_exercises.template_id
            AND st.coach_id = auth.uid()
        )
    );

CREATE POLICY "Coaches can delete own template exercises"
    ON template_exercises
    FOR DELETE
    USING (
        EXISTS (
            SELECT 1 FROM session_templates st
            WHERE st.id = template_exercises.template_id
            AND st.coach_id = auth.uid()
        )
    );

-- Triggers to auto-update updated_at
CREATE TRIGGER update_session_templates_updated_at
    BEFORE UPDATE ON session_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_template_exercises_updated_at
    BEFORE UPDATE ON template_exercises
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
