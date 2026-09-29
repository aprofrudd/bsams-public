-- Migration 028: Air Bike BLE Recordings + Metabolic Profiles

-- Air Bike Recordings (standard BLE captures)
CREATE TABLE IF NOT EXISTS air_bike_recordings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    test_date DATE NOT NULL,
    duration_s INTEGER NOT NULL,
    avg_power_w NUMERIC(7,1),
    peak_power_w NUMERIC(7,1),
    total_work_j NUMERIC(10,1),
    avg_cadence_rpm NUMERIC(5,1),
    peak_cadence_rpm NUMERIC(5,1),
    avg_speed_kmh NUMERIC(5,2),
    total_distance_m NUMERIC(8,1),
    total_calories_kcal NUMERIC(7,1),
    samples JSONB NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_air_bike_recordings_athlete_id ON air_bike_recordings(athlete_id);

CREATE TRIGGER update_air_bike_recordings_updated_at
    BEFORE UPDATE ON air_bike_recordings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE air_bike_recordings ENABLE ROW LEVEL SECURITY;
CREATE POLICY air_bike_recordings_select ON air_bike_recordings FOR SELECT USING (true);
CREATE POLICY air_bike_recordings_insert ON air_bike_recordings FOR INSERT WITH CHECK (true);
CREATE POLICY air_bike_recordings_update ON air_bike_recordings FOR UPDATE USING (true);
CREATE POLICY air_bike_recordings_delete ON air_bike_recordings FOR DELETE USING (true);

-- Metabolic Profiles (Ferretti/di Prampero 3-sprint protocol)
CREATE TABLE IF NOT EXISTS metabolic_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    athlete_id UUID NOT NULL REFERENCES athletes(id) ON DELETE CASCADE,
    test_date DATE NOT NULL,
    body_mass_kg NUMERIC(5,1) NOT NULL,
    data_source VARCHAR(10) NOT NULL DEFAULT 'ble' CHECK (data_source IN ('ble', 'manual')),
    resting_lactate_mmol NUMERIC(5,2) NOT NULL,
    la_peak_1_mmol NUMERIC(5,2) NOT NULL,
    la_peak_2_mmol NUMERIC(5,2) NOT NULL,
    la_peak_3_mmol NUMERIC(5,2) NOT NULL,
    sprint_1_avg_power_w NUMERIC(7,1),
    sprint_2_avg_power_w NUMERIC(7,1),
    sprint_3_avg_power_w NUMERIC(7,1),
    alactic_capacity_j NUMERIC(10,1),
    max_glycolytic_power_w NUMERIC(7,1),
    anaerobic_cost NUMERIC(7,4),
    fatigue_slope_w NUMERIC(7,1),
    mech_work_sprint_1_j NUMERIC(10,1),
    mech_work_sprint_2_j NUMERIC(10,1),
    mech_work_sprint_3_j NUMERIC(10,1),
    alactic_1_j NUMERIC(10,1),
    alactic_2_j NUMERIC(10,1),
    alactic_3_j NUMERIC(10,1),
    glycolytic_1_j NUMERIC(10,1),
    glycolytic_2_j NUMERIC(10,1),
    glycolytic_3_j NUMERIC(10,1),
    trim_1_s NUMERIC(4,1) DEFAULT 0,
    trim_2_s NUMERIC(4,1) DEFAULT 0,
    trim_3_s NUMERIC(4,1) DEFAULT 0,
    sprint_1_samples JSONB,
    sprint_2_samples JSONB,
    sprint_3_samples JSONB,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(athlete_id, test_date)
);

CREATE INDEX idx_metabolic_profiles_athlete_id ON metabolic_profiles(athlete_id);

CREATE TRIGGER update_metabolic_profiles_updated_at
    BEFORE UPDATE ON metabolic_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE metabolic_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY metabolic_profiles_select ON metabolic_profiles FOR SELECT USING (true);
CREATE POLICY metabolic_profiles_insert ON metabolic_profiles FOR INSERT WITH CHECK (true);
CREATE POLICY metabolic_profiles_update ON metabolic_profiles FOR UPDATE USING (true);
CREATE POLICY metabolic_profiles_delete ON metabolic_profiles FOR DELETE USING (true);
