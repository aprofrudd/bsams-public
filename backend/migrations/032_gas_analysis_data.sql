-- Migration 032: Gas Analysis Data (CPET integration with lactate tests)
-- One gas analysis per lactate test (1:1 FK with UNIQUE constraint)

CREATE TABLE IF NOT EXISTS gas_analysis_data (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  test_id UUID NOT NULL UNIQUE REFERENCES lactate_tests(id) ON DELETE CASCADE,
  interval_seconds INTEGER NOT NULL CHECK (interval_seconds IN (30, 60)),
  rest_start_seconds INTEGER DEFAULT 60,
  stage_duration_seconds INTEGER DEFAULT 180,
  rest_duration_seconds INTEGER DEFAULT 60,
  averaging_method TEXT DEFAULT 'last_60s' CHECK (averaging_method IN ('last_60s', 'full_stage')),
  samples JSONB NOT NULL,
  stage_averages JSONB NOT NULL,
  column_mapping JSONB,
  max_fat_oxidation_gh NUMERIC(7,1),
  fat_max_stage_number INTEGER,
  fat_max_intensity NUMERIC(7,2),
  fat_max_hr INTEGER,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gas_analysis_test_id ON gas_analysis_data(test_id);

-- Updated_at trigger
CREATE TRIGGER update_gas_analysis_data_updated_at
  BEFORE UPDATE ON gas_analysis_data
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- RLS policies (mirror lactate_tests access via athletes chain)
ALTER TABLE gas_analysis_data ENABLE ROW LEVEL SECURITY;

-- Coach SELECT
CREATE POLICY gas_analysis_coach_select ON gas_analysis_data
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM lactate_tests lt
      JOIN athletes a ON a.id = lt.athlete_id
      WHERE lt.id = gas_analysis_data.test_id
        AND a.coach_id = auth.uid()
    )
  );

-- Coach INSERT
CREATE POLICY gas_analysis_coach_insert ON gas_analysis_data
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM lactate_tests lt
      JOIN athletes a ON a.id = lt.athlete_id
      WHERE lt.id = gas_analysis_data.test_id
        AND a.coach_id = auth.uid()
    )
  );

-- Coach UPDATE
CREATE POLICY gas_analysis_coach_update ON gas_analysis_data
  FOR UPDATE USING (
    EXISTS (
      SELECT 1 FROM lactate_tests lt
      JOIN athletes a ON a.id = lt.athlete_id
      WHERE lt.id = gas_analysis_data.test_id
        AND a.coach_id = auth.uid()
    )
  );

-- Coach DELETE
CREATE POLICY gas_analysis_coach_delete ON gas_analysis_data
  FOR DELETE USING (
    EXISTS (
      SELECT 1 FROM lactate_tests lt
      JOIN athletes a ON a.id = lt.athlete_id
      WHERE lt.id = gas_analysis_data.test_id
        AND a.coach_id = auth.uid()
    )
  );

-- Athlete SELECT (read-only via user_id)
CREATE POLICY gas_analysis_athlete_select ON gas_analysis_data
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM lactate_tests lt
      JOIN athletes a ON a.id = lt.athlete_id
      WHERE lt.id = gas_analysis_data.test_id
        AND a.user_id = auth.uid()
    )
  );
