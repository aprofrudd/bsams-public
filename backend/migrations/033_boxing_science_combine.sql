-- Migration: 033_boxing_science_combine
-- Description: Combine events — roster, attempt log, result tagging, and the 7/17/27 air bike split
-- Run this in Supabase SQL Editor

-- ===========================================================================
-- 1. combine_events — one testing day
-- ===========================================================================
CREATE TABLE IF NOT EXISTS combine_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coach_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    event_date DATE NOT NULL,
    venue TEXT,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'live', 'closed')),

    -- Public read-only share link for the big screen
    share_token TEXT NOT NULL UNIQUE,
    share_token_expires_at TIMESTAMPTZ NOT NULL,
    share_revoked_at TIMESTAMPTZ,
    -- Participants are usually minors: publishing requires an explicit confirmation
    public_display_consent_confirmed_at TIMESTAMPTZ,

    -- Public display policy
    public_name_style TEXT NOT NULL DEFAULT 'full'
        CHECK (public_name_style IN ('full', 'first_initial', 'first_only', 'bib')),
    show_bs_benchmark BOOLEAN NOT NULL DEFAULT TRUE,
    show_club BOOLEAN NOT NULL DEFAULT TRUE,

    -- Scoring configuration
    landmine_exercise_name TEXT NOT NULL DEFAULT 'Landmine Punch Throw',
    landmine_loads_kg JSONB NOT NULL DEFAULT '[10,15,20,25]'::jsonb,
    landmine_reference_load_kg NUMERIC(6,2) NOT NULL DEFAULT 20
        CHECK (landmine_reference_load_kg > 0),
    landmine_reference_tolerance_kg NUMERIC(4,2) NOT NULL DEFAULT 1.0
        CHECK (landmine_reference_tolerance_kg >= 0),
    landmine_velocity_metric TEXT NOT NULL DEFAULT 'peak'
        CHECK (landmine_velocity_metric IN ('peak', 'mean')),
    airbike_score_basis TEXT NOT NULL DEFAULT 'w_per_kg'
        CHECK (airbike_score_basis IN ('absolute_w', 'w_per_kg')),
    min_stations_for_overall SMALLINT NOT NULL DEFAULT 3
        CHECK (min_stations_for_overall BETWEEN 1 AND 6),

    -- Cached Boxing Science norms: {score_key: {mean, sd, n}}. AGGREGATES ONLY —
    -- this is what the public endpoint reads, so it must never hold athlete rows.
    bs_norms_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    bs_norms_updated_at TIMESTAMPTZ,

    -- Change probe for polling clients; drives the ETag
    results_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (coach_id, event_name, event_date)
);

-- ===========================================================================
-- 2. combine_participants — the roster, with event-scoped grouping data
-- ===========================================================================
CREATE TABLE IF NOT EXISTS combine_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    combine_event_id UUID NOT NULL REFERENCES combine_events(id) ON DELETE CASCADE,
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    bib INTEGER NOT NULL CHECK (bib > 0 AND bib < 10000),
    club TEXT,
    weight_category TEXT,
    age_group TEXT,
    body_mass_kg NUMERIC(5,1) CHECK (body_mass_kg > 0 AND body_mass_kg <= 300),
    squad TEXT,
    withdrawn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (combine_event_id, athlete_id),
    UNIQUE (combine_event_id, bib)
);

-- ===========================================================================
-- 3. combine_attempts — every attempt at every station
--    NB: the JSONB column is `measures`; `values` is a reserved SQL word.
-- ===========================================================================
CREATE TABLE IF NOT EXISTS combine_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    combine_event_id UUID NOT NULL REFERENCES combine_events(id) ON DELETE CASCADE,
    participant_id UUID NOT NULL REFERENCES combine_participants(id) ON DELETE CASCADE,
    station TEXT NOT NULL CHECK (station IN
        ('cmj', 'pogo', 'landmine', 'grip', 'trunk_rotation', 'air_bike')),
    attempt_number SMALLINT NOT NULL CHECK (attempt_number BETWEEN 1 AND 20),
    measures JSONB NOT NULL,
    -- Client-generated: makes a retry or a double-tapped SAVE idempotent
    client_attempt_id UUID,
    entered_by UUID REFERENCES profiles(id) ON DELETE SET NULL,
    voided_at TIMESTAMPTZ,
    void_reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (participant_id, station, attempt_number)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_combine_attempts_client_id
    ON combine_attempts(combine_event_id, client_attempt_id)
    WHERE client_attempt_id IS NOT NULL;

-- ===========================================================================
-- 4. Indexes
-- ===========================================================================
CREATE INDEX IF NOT EXISTS idx_combine_events_coach ON combine_events(coach_id);
CREATE INDEX IF NOT EXISTS idx_combine_participants_event ON combine_participants(combine_event_id);
CREATE INDEX IF NOT EXISTS idx_combine_participants_athlete ON combine_participants(athlete_id);
CREATE INDEX IF NOT EXISTS idx_combine_attempts_event_live
    ON combine_attempts(combine_event_id) WHERE voided_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_combine_attempts_participant_station
    ON combine_attempts(participant_id, station);

-- ===========================================================================
-- 5. updated_at triggers (update_updated_at_column() is defined in 001)
-- ===========================================================================
DROP TRIGGER IF EXISTS update_combine_events_updated_at ON combine_events;
CREATE TRIGGER update_combine_events_updated_at
    BEFORE UPDATE ON combine_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_combine_participants_updated_at ON combine_participants;
CREATE TRIGGER update_combine_participants_updated_at
    BEFORE UPDATE ON combine_participants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_combine_attempts_updated_at ON combine_attempts;
CREATE TRIGGER update_combine_attempts_updated_at
    BEFORE UPDATE ON combine_attempts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===========================================================================
-- 6. Tag the real athlete tables. All additive and nullable, so existing rows
--    and existing endpoints are untouched.
-- ===========================================================================
ALTER TABLE performance_events
    ADD COLUMN IF NOT EXISTS combine_event_id UUID
    REFERENCES combine_events(id) ON DELETE SET NULL;

-- Exactly one performance_events row per athlete per combine. This is what keeps
-- cohort benchmarks in analysis.py from being weighted by repeated attempts.
-- Partial, so non-combine rows keep today's behaviour (no uniqueness at all).
CREATE UNIQUE INDEX IF NOT EXISTS uq_performance_events_combine
    ON performance_events(athlete_id, event_date, combine_event_id)
    WHERE combine_event_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_performance_events_combine
    ON performance_events(combine_event_id) WHERE combine_event_id IS NOT NULL;

ALTER TABLE vbt_profiles
    ADD COLUMN IF NOT EXISTS combine_event_id UUID
    REFERENCES combine_events(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_vbt_profiles_combine
    ON vbt_profiles(combine_event_id) WHERE combine_event_id IS NOT NULL;

ALTER TABLE air_bike_tests
    ADD COLUMN IF NOT EXISTS combine_event_id UUID
    REFERENCES combine_events(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_air_bike_tests_combine
    ON air_bike_tests(combine_event_id) WHERE combine_event_id IS NOT NULL;

-- ===========================================================================
-- 7. Air bike: support 7/17/27 without breaking 7/14/27
-- ===========================================================================
ALTER TABLE air_bike_tests
    ADD COLUMN IF NOT EXISTS split_scheme TEXT NOT NULL DEFAULT '7_14_27';
ALTER TABLE air_bike_tests DROP CONSTRAINT IF EXISTS air_bike_tests_split_scheme_check;
ALTER TABLE air_bike_tests ADD CONSTRAINT air_bike_tests_split_scheme_check
    CHECK (split_scheme IN ('7_14_27', '7_17_27'));

ALTER TABLE air_bike_sprints ADD COLUMN IF NOT EXISTS power_17s NUMERIC(7,1);
ALTER TABLE air_bike_sprints ALTER COLUMN power_14s DROP NOT NULL;
ALTER TABLE air_bike_sprints DROP CONSTRAINT IF EXISTS air_bike_sprints_mid_split_present;
ALTER TABLE air_bike_sprints ADD CONSTRAINT air_bike_sprints_mid_split_present
    CHECK (power_14s IS NOT NULL OR power_17s IS NOT NULL);

-- ===========================================================================
-- 8. Atomic metric merge for promotion.
--    Two stations can promote the same athlete at the same moment across two
--    uvicorn workers; a read-modify-write would lose one station's metrics.
-- ===========================================================================
CREATE OR REPLACE FUNCTION combine_upsert_event_metrics(
    p_athlete_id UUID,
    p_event_date DATE,
    p_combine_event_id UUID,
    p_metrics JSONB
) RETURNS UUID
LANGUAGE sql
AS $$
    INSERT INTO performance_events (athlete_id, event_date, metrics, combine_event_id)
    VALUES (p_athlete_id, p_event_date, p_metrics, p_combine_event_id)
    ON CONFLICT (athlete_id, event_date, combine_event_id)
        WHERE combine_event_id IS NOT NULL
    DO UPDATE SET metrics    = performance_events.metrics || EXCLUDED.metrics,
                  updated_at = NOW()
    RETURNING id;
$$;

REVOKE EXECUTE ON FUNCTION combine_upsert_event_metrics(UUID, DATE, UUID, JSONB)
    FROM PUBLIC;

-- ===========================================================================
-- 9. RLS — defence in depth. The backend uses the service_role key and bypasses
--    this; the public board is served by FastAPI, never PostgREST, so there is
--    deliberately no anon policy.
-- ===========================================================================
ALTER TABLE combine_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE combine_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE combine_attempts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS combine_events_coach_all ON combine_events;
CREATE POLICY combine_events_coach_all ON combine_events
    FOR ALL USING (coach_id = auth.uid()) WITH CHECK (coach_id = auth.uid());

DROP POLICY IF EXISTS combine_participants_coach_all ON combine_participants;
CREATE POLICY combine_participants_coach_all ON combine_participants
    FOR ALL
    USING (EXISTS (SELECT 1 FROM combine_events e
                   WHERE e.id = combine_participants.combine_event_id
                     AND e.coach_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM combine_events e
                        WHERE e.id = combine_participants.combine_event_id
                          AND e.coach_id = auth.uid()));

DROP POLICY IF EXISTS combine_attempts_coach_all ON combine_attempts;
CREATE POLICY combine_attempts_coach_all ON combine_attempts
    FOR ALL
    USING (EXISTS (SELECT 1 FROM combine_events e
                   WHERE e.id = combine_attempts.combine_event_id
                     AND e.coach_id = auth.uid()))
    WITH CHECK (EXISTS (SELECT 1 FROM combine_events e
                        WHERE e.id = combine_attempts.combine_event_id
                          AND e.coach_id = auth.uid()));
