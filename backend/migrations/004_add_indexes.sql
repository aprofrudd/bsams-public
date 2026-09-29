-- Performance indexes for common query patterns

-- Speed up event queries filtered by athlete + date (used in event listings and time-series)
CREATE INDEX IF NOT EXISTS idx_events_athlete_date
  ON performance_events(athlete_id, event_date);

-- Speed up athlete lookups by coach + name (used in CSV upload athlete resolution)
CREATE INDEX IF NOT EXISTS idx_athletes_coach_name
  ON athletes(coach_id, name);
