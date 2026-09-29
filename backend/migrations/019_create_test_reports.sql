-- Migration 019: Create test_reports table
-- Test reports allow coaches to build, save, and export consolidated athlete testing reports

CREATE TABLE test_reports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
  coach_id UUID NOT NULL REFERENCES profiles(id),
  report_date DATE NOT NULL DEFAULT CURRENT_DATE,
  date_range_start DATE,
  date_range_end DATE,
  sections JSONB NOT NULL DEFAULT '{}',
  notes JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS policies
ALTER TABLE test_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Coach sees own reports"
  ON test_reports FOR SELECT
  USING (coach_id = auth.uid());

CREATE POLICY "Coach inserts own reports"
  ON test_reports FOR INSERT
  WITH CHECK (coach_id = auth.uid());

CREATE POLICY "Coach updates own reports"
  ON test_reports FOR UPDATE
  USING (coach_id = auth.uid());

CREATE POLICY "Coach deletes own reports"
  ON test_reports FOR DELETE
  USING (coach_id = auth.uid());
