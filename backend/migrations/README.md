# Database Migrations

SQL migration scripts for Supabase.

## Running Migrations

1. Log into your Supabase project dashboard
2. Navigate to SQL Editor
3. Run each migration file in order:
   - `001_create_profiles_table.sql`
   - `002_create_athletes_table.sql`
   - `003_create_performance_events_table.sql`
   - `004_add_profiles_insert_policy.sql`
   - `005_create_coach_consents_table.sql`
   - `006_create_training_sessions.sql`
   - `007_create_wellness_entries.sql`
   - `008_create_exercise_prescriptions.sql`
   - `009_wellness_hooper_index.sql`
   - `010_create_exercise_library.sql`
   - `011_create_session_templates.sql`
   - `012_create_vbt_tables.sql`
   - `013_create_movement_assessments.sql`

4. After running migration 013, create an `assessment-photos` **private** bucket in Supabase Storage dashboard (Dashboard > Storage > New Bucket)

## Migration Order

Migrations must be run in numerical order due to foreign key dependencies:

1. **001_create_profiles_table.sql**
   - Creates the `profiles` table (linked to Supabase Auth)
   - Sets up trigger for auto-profile creation on signup
   - Enables RLS with user-only access

2. **002_create_athletes_table.sql**
   - Creates the `athletes` table
   - Foreign key to `profiles.id`
   - RLS policies: coaches only access their own athletes

3. **003_create_performance_events_table.sql**
   - Creates the `performance_events` table
   - JSONB `metrics` column for flexible data storage
   - GIN index for fast JSONB queries
   - RLS policies via athlete ownership check

4. **004_add_profiles_insert_policy.sql**
   - Adds RLS INSERT policy on profiles table

5. **005_create_coach_consents_table.sql**
   - Creates `coach_consents` table for data sharing opt-in

6. **006_create_training_sessions.sql**
   - Creates `training_sessions` table with `srpe` generated column (rpe * duration_minutes)
   - RLS policies via athlete ownership chain

7. **007_create_wellness_entries.sql**
   - Creates `wellness_entries` table (5 scores, 1-5 scale)
   - UNIQUE(athlete_id, entry_date)

8. **008_create_exercise_prescriptions.sql**
   - Creates `exercise_prescriptions` table (FK to training_sessions CASCADE)
   - RLS policies via session -> athlete ownership chain

9. **009_wellness_hooper_index.sql**
   - Migrates wellness to Validated Hooper Index (4 scores, 1-7 scale)
   - `hooper_index` generated column (sum of 4 scores, range 4-28)

10. **010_create_exercise_library.sql**
    - Creates `exercise_library` table (coach-level reusable exercises)
    - UNIQUE(coach_id, exercise_name), default fields for pre-filling
    - RLS policies: coaches access own exercises only

11. **011_create_session_templates.sql**
    - Creates `session_templates` table (reusable session plans)
    - Creates `template_exercises` table (FK CASCADE to templates, SET NULL to library)
    - UNIQUE(coach_id, template_name)
    - RLS policies via template ownership chain

12. **012_create_vbt_tables.sql**
    - Creates `vbt_profiles` table (load-velocity profiling per athlete + exercise)
    - Creates `vbt_sets` table (FK CASCADE to profiles, individual load-velocity data points)
    - UNIQUE(athlete_id, exercise_name, profile_date)
    - RLS policies via athlete -> coach ownership chain

13. **013_create_movement_assessments.sql**
    - Creates `movement_assessments` table (NASM movement screening)
    - Creates `assessment_photos` table (FK CASCADE to assessments)
    - UNIQUE(athlete_id, assessment_date, assessment_type)
    - JSONB `findings` column for structured checklist data
    - RLS policies via athlete -> coach ownership chain
    - **Requires**: `assessment-photos` private bucket in Supabase Storage

## Row Level Security (RLS)

All tables have RLS enabled. Policies ensure:

- **Profiles**: Users can only read/update their own profile
- **Athletes**: Coaches can only CRUD their own athletes (`coach_id = auth.uid()`)
- **Performance Events**: Access granted via athlete ownership chain
- **Coach Consents**: Coaches access own consent records only
- **Training Sessions**: Access via athlete ownership chain
- **Wellness Entries**: Access via athlete ownership chain
- **Exercise Prescriptions**: Access via session -> athlete ownership chain
- **Exercise Library**: Coaches access own library exercises only (`coach_id = auth.uid()`)
- **Session Templates**: Coaches access own templates only (`coach_id = auth.uid()`)
- **Template Exercises**: Access via template ownership chain
- **VBT Profiles**: Access via athlete -> coach ownership chain
- **VBT Sets**: Access via profile -> athlete -> coach ownership chain
- **Movement Assessments**: Access via athlete -> coach ownership chain
- **Assessment Photos**: Access via assessment -> athlete -> coach ownership chain

**Note:** The backend uses the Supabase **service_role key** to bypass RLS for server-side queries. RLS policies primarily protect against direct Supabase client access.

## Key Features

### JSONB Metrics Column

The `performance_events.metrics` column uses JSONB for flexible storage:

```sql
-- Example data
INSERT INTO performance_events (athlete_id, event_date, metrics)
VALUES (
  'athlete-uuid',
  '2024-01-15',
  '{"test_type": "CMJ", "height_cm": 45.5, "mass_kg": 75.0}'::jsonb
);

-- Query by metric
SELECT * FROM performance_events
WHERE metrics->>'test_type' = 'CMJ';

-- Query numeric values
SELECT * FROM performance_events
WHERE (metrics->>'height_cm')::numeric > 40;
```

### GIN Index

The GIN index on `metrics` enables fast querying:

```sql
-- This query uses the GIN index
SELECT * FROM performance_events
WHERE metrics @> '{"test_type": "CMJ"}'::jsonb;
```

### Generated Columns

- `training_sessions.srpe` = `rpe * duration_minutes` (GENERATED ALWAYS AS ... STORED)
- `wellness_entries.hooper_index` = `sleep + fatigue + stress + doms` (GENERATED ALWAYS AS ... STORED)

### Assessment Findings JSONB Structure

```json
{
  "feet_ankles": {
    "turn_out": {"observed": true, "severity": "moderate", "side": "bilateral"},
    "heels_rise": {"observed": false}
  },
  "knees": {
    "valgus": {"observed": true, "severity": "mild", "side": "left"}
  },
  "lphc": {
    "forward_lean": {"observed": true, "severity": "significant"}
  }
}
```

## Verification

After running all migrations, verify in Supabase Dashboard:

1. **Tables** (15 total): `profiles`, `athletes`, `performance_events`, `coach_consents`, `training_sessions`, `wellness_entries`, `exercise_prescriptions`, `exercise_library`, `session_templates`, `template_exercises`, `vbt_profiles`, `vbt_sets`, `movement_assessments`, `assessment_photos`
2. **RLS**: Verify RLS is enabled on all tables (shield icon)
3. **Policies**: Check policies in Authentication > Policies
4. **Indexes**: Verify indexes in Table Editor > Indexes
5. **Storage**: Verify `assessment-photos` private bucket exists in Storage

## Rollback

To rollback (use with caution):

```sql
-- Drop in reverse order
DROP TABLE IF EXISTS assessment_photos CASCADE;
DROP TABLE IF EXISTS movement_assessments CASCADE;
DROP TABLE IF EXISTS vbt_sets CASCADE;
DROP TABLE IF EXISTS vbt_profiles CASCADE;
DROP TABLE IF EXISTS template_exercises CASCADE;
DROP TABLE IF EXISTS session_templates CASCADE;
DROP TABLE IF EXISTS exercise_library CASCADE;
DROP TABLE IF EXISTS exercise_prescriptions CASCADE;
DROP TABLE IF EXISTS wellness_entries CASCADE;
DROP TABLE IF EXISTS training_sessions CASCADE;
DROP TABLE IF EXISTS coach_consents CASCADE;
DROP TABLE IF EXISTS performance_events CASCADE;
DROP TABLE IF EXISTS athletes CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```
