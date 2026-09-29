-- Migration: 035_combine_overall_score_basis
-- Description: Per-event choice of Combine Score basis — the z composite (today's
--              behaviour) or a percentile composite
-- Run this in Supabase SQL Editor, after 034. Additive and safe to re-run.

-- ===========================================================================
-- 1. How the Combine Score is composed.
--      'z'          — 50 + 10 * mean(z), the T-score every event has used so far
--      'percentile' — the mean of the boxer's per-station percentiles
--
--    Measured on the project's own 119 athletes the two composites agree almost
--    perfectly (Spearman 0.982, 8 of the top 10 shared) and part company exactly
--    where one freakish value on a skewed metric inflates a z: on contact time only
--    1.7% of athletes clear z >= 1.0 where normal theory expects 15.9%. Percentiles
--    are immune to that and are far easier to explain to a 15-year-old.
--
--    The coach chooses, so the default is today's behaviour and every event already
--    in the table keeps it. An event created after this migration behaves exactly as
--    one created before it until somebody switches this column.
-- ===========================================================================
ALTER TABLE combine_events
    ADD COLUMN IF NOT EXISTS overall_score_basis TEXT NOT NULL DEFAULT 'z';
ALTER TABLE combine_events DROP CONSTRAINT IF EXISTS combine_events_overall_score_basis_check;
ALTER TABLE combine_events ADD CONSTRAINT combine_events_overall_score_basis_check
    CHECK (overall_score_basis IN ('z', 'percentile'));

-- Verify (expect every existing event on 'z'):
--   SELECT overall_score_basis, COUNT(*) FROM combine_events GROUP BY 1;
