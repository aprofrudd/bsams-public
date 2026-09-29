-- Migration: Create coach_consents table for data sharing consent tracking
-- Run on Supabase SQL editor

CREATE TABLE coach_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE UNIQUE,
    data_sharing_enabled BOOLEAN NOT NULL DEFAULT false,
    consented_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS policies
ALTER TABLE coach_consents ENABLE ROW LEVEL SECURITY;

-- Coaches can read their own consent
CREATE POLICY "coach_consents_select_own" ON coach_consents
    FOR SELECT USING (coach_id = auth.uid());

-- Coaches can insert their own consent
CREATE POLICY "coach_consents_insert_own" ON coach_consents
    FOR INSERT WITH CHECK (coach_id = auth.uid());

-- Coaches can update their own consent
CREATE POLICY "coach_consents_update_own" ON coach_consents
    FOR UPDATE USING (coach_id = auth.uid());

-- Admins can read all consents (for viewing opted-in coaches)
CREATE POLICY "coach_consents_select_admin" ON coach_consents
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE profiles.id = auth.uid()
            AND profiles.role = 'admin'
        )
    );

-- Index for quick lookup by coach
CREATE INDEX idx_coach_consents_coach_id ON coach_consents(coach_id);

-- Index for finding opted-in coaches
CREATE INDEX idx_coach_consents_sharing_enabled ON coach_consents(data_sharing_enabled) WHERE data_sharing_enabled = true;
