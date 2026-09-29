-- Migration 029: Training Blocks, Block Sessions, Athlete Maxes, Block Applications
-- + Add video_url to exercise_library

-- Training Blocks: multi-week program definitions, coach-owned
CREATE TABLE IF NOT EXISTS training_blocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    block_name TEXT NOT NULL,
    description TEXT,
    num_weeks INTEGER NOT NULL DEFAULT 4 CHECK (num_weeks >= 1 AND num_weeks <= 16),
    category TEXT NOT NULL DEFAULT 'Strength',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(coach_id, block_name)
);

-- Block Sessions: session slots within a block (week + day)
-- exercises stored as JSONB (same shape as program_templates + percent_1rm)
CREATE TABLE IF NOT EXISTS block_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_id UUID NOT NULL REFERENCES training_blocks(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL CHECK (week_number >= 1 AND week_number <= 16),
    day_of_week INTEGER NOT NULL CHECK (day_of_week >= 1 AND day_of_week <= 7),
    session_name TEXT NOT NULL,
    training_type TEXT NOT NULL,
    notes TEXT,
    exercises JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(block_id, week_number, day_of_week, session_name)
);

-- Athlete Maxes: current 1RM per athlete per exercise (for % resolution)
CREATE TABLE IF NOT EXISTS athlete_maxes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    exercise_name TEXT NOT NULL,
    max_kg NUMERIC(6,2) NOT NULL CHECK (max_kg > 0 AND max_kg <= 1000),
    source TEXT NOT NULL DEFAULT 'manual',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, exercise_name)
);

-- Block Applications: audit trail of block deployments
CREATE TABLE IF NOT EXISTS block_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    block_id UUID NOT NULL REFERENCES training_blocks(id) ON DELETE CASCADE,
    coach_id UUID NOT NULL REFERENCES profiles(id),
    athlete_ids JSONB NOT NULL,
    start_date DATE NOT NULL,
    sessions_created INTEGER NOT NULL DEFAULT 0,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Add video_url to exercise_library
ALTER TABLE exercise_library ADD COLUMN IF NOT EXISTS video_url TEXT;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_training_blocks_coach ON training_blocks(coach_id);
CREATE INDEX IF NOT EXISTS idx_block_sessions_block ON block_sessions(block_id);
CREATE INDEX IF NOT EXISTS idx_block_sessions_week ON block_sessions(block_id, week_number);
CREATE INDEX IF NOT EXISTS idx_athlete_maxes_athlete ON athlete_maxes(athlete_id);
CREATE INDEX IF NOT EXISTS idx_block_applications_block ON block_applications(block_id);
CREATE INDEX IF NOT EXISTS idx_block_applications_coach ON block_applications(coach_id);

-- RLS Policies
ALTER TABLE training_blocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE block_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE athlete_maxes ENABLE ROW LEVEL SECURITY;
ALTER TABLE block_applications ENABLE ROW LEVEL SECURITY;

-- Training Blocks: coaches CRUD own, admins all
CREATE POLICY training_blocks_coach_select ON training_blocks
    FOR SELECT USING (coach_id = auth.uid());
CREATE POLICY training_blocks_coach_insert ON training_blocks
    FOR INSERT WITH CHECK (coach_id = auth.uid());
CREATE POLICY training_blocks_coach_update ON training_blocks
    FOR UPDATE USING (coach_id = auth.uid());
CREATE POLICY training_blocks_coach_delete ON training_blocks
    FOR DELETE USING (coach_id = auth.uid());

-- Block Sessions: via block ownership
CREATE POLICY block_sessions_select ON block_sessions
    FOR SELECT USING (
        block_id IN (SELECT id FROM training_blocks WHERE coach_id = auth.uid())
    );
CREATE POLICY block_sessions_insert ON block_sessions
    FOR INSERT WITH CHECK (
        block_id IN (SELECT id FROM training_blocks WHERE coach_id = auth.uid())
    );
CREATE POLICY block_sessions_update ON block_sessions
    FOR UPDATE USING (
        block_id IN (SELECT id FROM training_blocks WHERE coach_id = auth.uid())
    );
CREATE POLICY block_sessions_delete ON block_sessions
    FOR DELETE USING (
        block_id IN (SELECT id FROM training_blocks WHERE coach_id = auth.uid())
    );

-- Athlete Maxes: coach via athlete ownership, athlete SELECT own
CREATE POLICY athlete_maxes_coach_all ON athlete_maxes
    FOR ALL USING (
        athlete_id IN (SELECT id FROM athletes WHERE coach_id = auth.uid())
    );
CREATE POLICY athlete_maxes_athlete_select ON athlete_maxes
    FOR SELECT USING (
        athlete_id IN (SELECT id FROM athletes WHERE user_id = auth.uid())
    );

-- Block Applications: coach own
CREATE POLICY block_applications_coach_all ON block_applications
    FOR ALL USING (coach_id = auth.uid());
