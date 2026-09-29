-- Migration: 017_athlete_role_invitations
-- Description: Adds athlete role, user_id to athletes, and athlete_invitations table
-- Run this in Supabase SQL Editor

-- 1. Update profiles.role CHECK to include 'athlete'
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE profiles ADD CONSTRAINT profiles_role_check CHECK (role IN ('admin', 'coach', 'athlete'));

-- 2. Add user_id column to athletes (links athlete record to auth user)
ALTER TABLE athletes ADD COLUMN IF NOT EXISTS user_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_athletes_user_id ON athletes(user_id) WHERE user_id IS NOT NULL;

-- 3. Create athlete_invitations table
CREATE TABLE IF NOT EXISTS athlete_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    invite_code TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    used_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitations_code ON athlete_invitations(invite_code);
CREATE INDEX IF NOT EXISTS idx_invitations_athlete ON athlete_invitations(athlete_id);

-- 4. RLS for athlete_invitations (coaches manage own)
ALTER TABLE athlete_invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Coaches manage own invitations" ON athlete_invitations
    FOR ALL USING (coach_id = auth.uid());

-- 5. Athlete role SELECT-only RLS policies
-- Athletes can read their own athlete record
CREATE POLICY "Athletes read own record" ON athletes
    FOR SELECT USING (user_id = auth.uid());

-- Athletes can read their own performance events
CREATE POLICY "Athletes read own performance events" ON performance_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = performance_events.athlete_id
            AND a.user_id = auth.uid()
        )
    );

-- Athletes can read their own training sessions
CREATE POLICY "Athletes read own training sessions" ON training_sessions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = training_sessions.athlete_id
            AND a.user_id = auth.uid()
        )
    );

-- Athletes can read their own wellness entries
CREATE POLICY "Athletes read own wellness entries" ON wellness_entries
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = wellness_entries.athlete_id
            AND a.user_id = auth.uid()
        )
    );

-- Athletes can read their own VBT profiles
CREATE POLICY "Athletes read own vbt profiles" ON vbt_profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = vbt_profiles.athlete_id
            AND a.user_id = auth.uid()
        )
    );

-- Athletes can read their own movement assessments
CREATE POLICY "Athletes read own movement assessments" ON movement_assessments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = movement_assessments.athlete_id
            AND a.user_id = auth.uid()
        )
    );

-- Athletes can read their own lactate tests
CREATE POLICY "Athletes read own lactate tests" ON lactate_tests
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = lactate_tests.athlete_id
            AND a.user_id = auth.uid()
        )
    );

-- Athletes can read their own air bike tests
CREATE POLICY "Athletes read own air bike tests" ON air_bike_tests
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM athletes a
            WHERE a.id = air_bike_tests.athlete_id
            AND a.user_id = auth.uid()
        )
    );

-- Double-chain: Athletes read exercise prescriptions (via training_sessions -> athletes)
CREATE POLICY "Athletes read own exercise prescriptions" ON exercise_prescriptions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM training_sessions ts
            JOIN athletes a ON a.id = ts.athlete_id
            WHERE ts.id = exercise_prescriptions.session_id
            AND a.user_id = auth.uid()
        )
    );

-- Double-chain: Athletes read VBT sets (via vbt_profiles -> athletes)
CREATE POLICY "Athletes read own vbt sets" ON vbt_sets
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM vbt_profiles vp
            JOIN athletes a ON a.id = vp.athlete_id
            WHERE vp.id = vbt_sets.profile_id
            AND a.user_id = auth.uid()
        )
    );

-- Double-chain: Athletes read assessment photos (via movement_assessments -> athletes)
CREATE POLICY "Athletes read own assessment photos" ON assessment_photos
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM movement_assessments ma
            JOIN athletes a ON a.id = ma.athlete_id
            WHERE ma.id = assessment_photos.assessment_id
            AND a.user_id = auth.uid()
        )
    );

-- Double-chain: Athletes read lactate stages (via lactate_tests -> athletes)
CREATE POLICY "Athletes read own lactate stages" ON lactate_stages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM lactate_tests lt
            JOIN athletes a ON a.id = lt.athlete_id
            WHERE lt.id = lactate_stages.test_id
            AND a.user_id = auth.uid()
        )
    );

-- Double-chain: Athletes read air bike sprints (via air_bike_tests -> athletes)
CREATE POLICY "Athletes read own air bike sprints" ON air_bike_sprints
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM air_bike_tests abt
            JOIN athletes a ON a.id = abt.athlete_id
            WHERE abt.id = air_bike_sprints.test_id
            AND a.user_id = auth.uid()
        )
    );
