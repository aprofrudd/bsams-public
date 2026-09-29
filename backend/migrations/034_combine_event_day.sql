-- Migration: 034_combine_event_day
-- Description: Event-day hardening for the combine — per-event RFD unit, W/kg-only
--              air bike scoring, a wider attempt cap, and explicit function grants
-- Run this in Supabase SQL Editor, after 033. Additive and safe to re-run.

-- ===========================================================================
-- 1. RFD unit per event.
--    Values are always STORED in N/s; this records which unit the station's
--    dynamometer reads so the entry screen can label its fields, and the API
--    converts kg/s on the way in.
-- ===========================================================================
ALTER TABLE combine_events
    ADD COLUMN IF NOT EXISTS rfd_unit TEXT NOT NULL DEFAULT 'n_s';
ALTER TABLE combine_events DROP CONSTRAINT IF EXISTS combine_events_rfd_unit_check;
ALTER TABLE combine_events ADD CONSTRAINT combine_events_rfd_unit_check
    CHECK (rfd_unit IN ('n_s', 'kg_s'));

-- ===========================================================================
-- 2. Air bike scores W/kg only.
--    'absolute_w' ranked raw watts against a W/kg Boxing Science norm, which put
--    every boxer in the top band and labelled watts "W/kg" on the public screen.
-- ===========================================================================
UPDATE combine_events SET airbike_score_basis = 'w_per_kg'
    WHERE airbike_score_basis IS DISTINCT FROM 'w_per_kg';
ALTER TABLE combine_events DROP CONSTRAINT IF EXISTS combine_events_airbike_score_basis_check;
ALTER TABLE combine_events ADD CONSTRAINT combine_events_airbike_score_basis_check
    CHECK (airbike_score_basis IN ('w_per_kg'));

-- ===========================================================================
-- 3. Attempt cap 1–40.
--    Landmine is now logged per side, so one boxer can reach 2 sides x 4 loads
--    plus re-throws at a single station. Keep this in step with
--    MAX_ATTEMPTS_PER_STATION in routers/combine.py.
-- ===========================================================================
ALTER TABLE combine_attempts DROP CONSTRAINT IF EXISTS combine_attempts_attempt_number_check;
ALTER TABLE combine_attempts ADD CONSTRAINT combine_attempts_attempt_number_check
    CHECK (attempt_number BETWEEN 1 AND 40);

-- ===========================================================================
-- 4. Lock the promotion function down.
--    Supabase's default privileges grant EXECUTE on every new function to anon
--    and authenticated, and 033's `REVOKE ... FROM PUBLIC` does not remove those
--    role grants. Only the backend's service_role key may merge promoted metrics.
--    `SET search_path = public` stops a caller-controlled search_path resolving
--    `performance_events` to something else.
-- ===========================================================================
CREATE OR REPLACE FUNCTION combine_upsert_event_metrics(
    p_athlete_id UUID,
    p_event_date DATE,
    p_combine_event_id UUID,
    p_metrics JSONB
) RETURNS UUID
LANGUAGE sql
SET search_path = public
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
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION combine_upsert_event_metrics(UUID, DATE, UUID, JSONB)
    TO service_role;

-- Verify (expect service_role and the function owner only):
--   SELECT grantee, privilege_type FROM information_schema.routine_privileges
--    WHERE routine_name = 'combine_upsert_event_metrics';
