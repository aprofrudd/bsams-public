-- Migration 025: Custom training types per coach
CREATE TABLE IF NOT EXISTS custom_training_types (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    type_name VARCHAR(50) NOT NULL,
    display_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(coach_id, type_name)
);

-- RLS policies
ALTER TABLE custom_training_types ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Coaches can manage their own training types"
    ON custom_training_types
    FOR ALL
    USING (coach_id = auth.uid())
    WITH CHECK (coach_id = auth.uid());

-- Also add default_set_configs JSONB column to exercise_library (for Change 8)
ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS default_set_configs JSONB;
