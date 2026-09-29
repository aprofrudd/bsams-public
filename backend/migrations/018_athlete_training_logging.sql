-- Migration 018: Athlete Training Logging & Session Completion
-- Adds status/created_by to training_sessions, makes rpe/duration nullable,
-- and adds RLS policies for athlete role on training/wellness/exercises.

-- 1. Add status column (NULL = regular session, 'assigned' = coach-created, 'completed' = athlete-finished)
ALTER TABLE training_sessions
ADD COLUMN IF NOT EXISTS status TEXT CHECK(status IN ('assigned', 'completed')) DEFAULT NULL;

-- 2. Add created_by column (tracks who created the session)
ALTER TABLE training_sessions
ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES profiles(id) ON DELETE SET NULL;

-- 3. Make rpe and duration_minutes nullable (for assigned sessions without athlete input yet)
ALTER TABLE training_sessions ALTER COLUMN rpe DROP NOT NULL;
ALTER TABLE training_sessions ALTER COLUMN duration_minutes DROP NOT NULL;

-- Note: The srpe generated column (rpe * duration_minutes) naturally returns NULL when either input is NULL.

-- 4. RLS policies for athlete role on training_sessions
CREATE POLICY "athlete_insert_own_training_sessions"
ON training_sessions FOR INSERT
TO authenticated
WITH CHECK (
  athlete_id IN (
    SELECT id FROM athletes WHERE user_id = auth.uid()
  )
);

CREATE POLICY "athlete_update_own_training_sessions"
ON training_sessions FOR UPDATE
TO authenticated
USING (
  athlete_id IN (
    SELECT id FROM athletes WHERE user_id = auth.uid()
  )
);

CREATE POLICY "athlete_delete_own_training_sessions"
ON training_sessions FOR DELETE
TO authenticated
USING (
  athlete_id IN (
    SELECT id FROM athletes WHERE user_id = auth.uid()
  )
  AND status IS NULL
);

-- 5. RLS policies for athlete role on wellness_entries
CREATE POLICY "athlete_insert_own_wellness"
ON wellness_entries FOR INSERT
TO authenticated
WITH CHECK (
  athlete_id IN (
    SELECT id FROM athletes WHERE user_id = auth.uid()
  )
);

CREATE POLICY "athlete_update_own_wellness"
ON wellness_entries FOR UPDATE
TO authenticated
USING (
  athlete_id IN (
    SELECT id FROM athletes WHERE user_id = auth.uid()
  )
);

CREATE POLICY "athlete_delete_own_wellness"
ON wellness_entries FOR DELETE
TO authenticated
USING (
  athlete_id IN (
    SELECT id FROM athletes WHERE user_id = auth.uid()
  )
);

-- 6. RLS policy for athlete role on exercise_prescriptions (UPDATE only, for completing exercises)
CREATE POLICY "athlete_update_exercises_via_session"
ON exercise_prescriptions FOR UPDATE
TO authenticated
USING (
  session_id IN (
    SELECT ts.id FROM training_sessions ts
    JOIN athletes a ON ts.athlete_id = a.id
    WHERE a.user_id = auth.uid()
  )
);
