-- Migration 030: Programme Forms + Exercise Prescription Extensions

CREATE TABLE IF NOT EXISTS programme_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    form_name TEXT NOT NULL,
    description TEXT,
    num_weeks INTEGER NOT NULL DEFAULT 4 CHECK (num_weeks >= 1 AND num_weeks <= 16),
    sessions_per_week INTEGER NOT NULL DEFAULT 2 CHECK (sessions_per_week >= 1 AND sessions_per_week <= 7),
    form_data JSONB NOT NULL DEFAULT '{"sessions":[]}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(coach_id, form_name)
);

CREATE INDEX IF NOT EXISTS idx_programme_forms_coach ON programme_forms(coach_id);

-- New columns on exercise_prescriptions for section grouping
ALTER TABLE exercise_prescriptions ADD COLUMN IF NOT EXISTS section_type TEXT;
ALTER TABLE exercise_prescriptions ADD COLUMN IF NOT EXISTS reps_text TEXT;
ALTER TABLE exercise_prescriptions ADD COLUMN IF NOT EXISTS recommended_weight_kg NUMERIC(6,2);

-- RLS
ALTER TABLE programme_forms ENABLE ROW LEVEL SECURITY;

CREATE POLICY programme_forms_coach_select ON programme_forms
    FOR SELECT USING (coach_id = auth.uid());
CREATE POLICY programme_forms_coach_insert ON programme_forms
    FOR INSERT WITH CHECK (coach_id = auth.uid());
CREATE POLICY programme_forms_coach_update ON programme_forms
    FOR UPDATE USING (coach_id = auth.uid());
CREATE POLICY programme_forms_coach_delete ON programme_forms
    FOR DELETE USING (coach_id = auth.uid());
