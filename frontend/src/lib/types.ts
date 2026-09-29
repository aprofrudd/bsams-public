// Athlete types
export interface Athlete {
  id: string;
  coach_id: string;
  name: string;
  gender: 'male' | 'female';
  date_of_birth: string | null;
  first_name: string | null;
  surname: string | null;
  body_mass_kg: number | null;
  stature_cm: number | null;
  status: 'amateur' | 'professional' | null;
  notes: string | null;
  user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AthleteCreate {
  name: string;
  gender: 'male' | 'female';
  date_of_birth?: string;
  first_name?: string;
  surname?: string;
  body_mass_kg?: number;
  stature_cm?: number;
  status?: 'amateur' | 'professional';
  notes?: string;
}

export interface AthleteUpdate {
  name?: string;
  gender?: 'male' | 'female';
  date_of_birth?: string | null;
  first_name?: string;
  surname?: string;
  body_mass_kg?: number | null;
  stature_cm?: number | null;
  status?: 'amateur' | 'professional' | null;
  notes?: string | null;
}

// Performance Event types
export interface PerformanceEvent {
  id: string;
  athlete_id: string;
  event_date: string;
  metrics: EventMetrics;
  created_at: string;
  updated_at: string;
}

export interface EventMetrics {
  test_type?: string;
  height_cm?: number;
  rsi?: number;
  flight_time_ms?: number;
  contraction_time_ms?: number;
  body_mass_kg?: number;
  [key: string]: string | number | undefined;
}

export interface PerformanceEventCreate {
  athlete_id: string;
  event_date: string;
  metrics: EventMetrics;
}

export interface PerformanceEventUpdate {
  event_date?: string;
  metrics?: EventMetrics;
}

// Analysis types
export type ReferenceGroup = 'cohort' | 'gender' | 'mass_band';

export interface Benchmarks {
  mean: number | null;
  std_dev: number | null;
  mode: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
  count: number;
  reference_group: string;
  metric: string;
}

export interface ZScoreResult {
  value: number;
  z_score: number;
  mean: number;
  std_dev: number;
  percentile_rank: number | null;
  reference_group: string;
  metric: string;
}

// Benchmark source types
export type BenchmarkSource = 'own' | 'boxing_science' | 'shared_pool';

// Database Analysis types
export type AnalysisDomain = 'performance' | 'training' | 'wellness' | 'vbt' | 'lactate' | 'air_bike' | 'assessments';
export type AnalysisDataSource = 'boxing_science' | 'shared_pool';

export interface AthleteFilter {
  gender?: 'male' | 'female';
  status?: 'amateur' | 'professional';
  age_min?: number;
  age_max?: number;
  mass_band?: string;
  stature_min_cm?: number;
  stature_max_cm?: number;
}

export interface DateFilter {
  start_date?: string;
  end_date?: string;
}

export type AggregationMode = 'all_records' | 'mean_per_athlete' | 'median_per_athlete' | 'peak_per_athlete';

export interface AnalysisRequest {
  domain: AnalysisDomain;
  data_source?: AnalysisDataSource;
  aggregation_mode?: AggregationMode;
  athlete_filter?: AthleteFilter;
  date_filter?: DateFilter;
  performance_filters?: { metric_keys?: string[] };
  training_filters?: { training_type?: string };
  vbt_filters?: { exercise_name?: string };
  lactate_filters?: { test_type?: string };
  assessment_filters?: { assessment_type?: string };
}

export interface DescriptiveStats {
  metric: string;
  label: string;
  count: number;
  mean: number | null;
  std_dev: number | null;
  median: number | null;
  min_val: number | null;
  max_val: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
}

export interface DysfunctionPrevalence {
  region: string;
  dysfunction: string;
  count: number;
  total_assessed: number;
  prevalence_pct: number;
}

export interface AnalysisResponse {
  domain: string;
  athlete_count: number;
  record_count: number;
  aggregation_mode: string;
  filters_applied: Record<string, string>;
  statistics: DescriptiveStats[];
  dysfunction_prevalence: DysfunctionPrevalence[];
  distributions: Record<string, number[]>;
}

export interface DomainInfo {
  key: string;
  label: string;
}

export interface DomainMetric {
  key: string;
  label: string;
  unit: string;
}

export interface DomainMetricsResponse {
  domain: string;
  metrics: DomainMetric[];
}

// UI types
export type ViewMode = 'table' | 'graph';

// Table row with calculated Z-score
export interface PerformanceRow {
  id: string;
  date: string;
  bodyMass: number | null;
  value: number | null;
  zScore: number | null;
  groupMean: number | null;
  percentileRank: number | null;
  groupStdDev: number | null;
}

// Training Session types
export interface TrainingSession {
  id: string;
  athlete_id: string;
  session_date: string;
  training_type: string;
  duration_minutes: number | null;
  rpe: number | null;
  srpe: number | null;
  description: string | null;
  notes: string | null;
  metrics: Record<string, string | number | undefined>;
  status: 'assigned' | 'completed' | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrainingSessionCreate {
  athlete_id: string;
  session_date: string;
  training_type: string;
  duration_minutes?: number;
  rpe?: number;
  description?: string;
  notes?: string;
  metrics?: Record<string, string | number | undefined>;
  status?: 'assigned';
}

export interface TrainingSessionUpdate {
  session_date?: string;
  training_type?: string;
  duration_minutes?: number;
  rpe?: number;
  description?: string;
  notes?: string;
  metrics?: Record<string, string | number | undefined>;
  status?: 'completed';
}

export interface BatchSessionAssign {
  template_id: string;
  athlete_ids: string[];
  session_date: string;
  notes?: string;
}

export interface BatchSessionResponse {
  created_count: number;
  sessions: TrainingSession[];
}

// Exercise Prescription types
export interface ExercisePrescription {
  id: string;
  session_id: string;
  exercise_name: string;
  exercise_category: string | null;
  set_number: number;
  reps: number | null;
  weight_kg: number | null;
  tempo: string | null;
  rest_seconds: number | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  intensity_type: string | null;
  intensity_value: number | null;
  intensity_min: number | null;
  intensity_max: number | null;
  rest_between_reps_seconds: number | null;
  rep_durations: number[] | null;
  rest_between_reps: number[] | null;
  rep_intensity_values: number[] | null;
  section_type?: string;
  reps_text?: string;
  recommended_weight_kg?: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExercisePrescriptionCreate {
  exercise_name: string;
  exercise_category?: string;
  set_number: number;
  reps?: number;
  weight_kg?: number;
  tempo?: string;
  rest_seconds?: number;
  duration_seconds?: number;
  distance_meters?: number;
  intensity_type?: string;
  intensity_value?: number;
  intensity_min?: number;
  intensity_max?: number;
  rest_between_reps_seconds?: number;
  rep_durations?: number[];
  rest_between_reps?: number[];
  rep_intensity_values?: number[];
  notes?: string;
}

export interface ExercisePrescriptionUpdate {
  exercise_name?: string;
  exercise_category?: string;
  set_number?: number;
  reps?: number;
  weight_kg?: number;
  tempo?: string;
  rest_seconds?: number;
  duration_seconds?: number;
  distance_meters?: number;
  intensity_type?: string;
  intensity_value?: number;
  rest_between_reps_seconds?: number;
  rep_durations?: number[];
  rep_intensity_values?: number[];
  notes?: string;
}

// Training Load Analysis types
export interface DailyLoadData {
  date: string;
  total_srpe: number;
  session_count: number;
}

export interface TrainingLoadAnalysis {
  daily_loads: DailyLoadData[];
  weekly_load: number | null;
  monotony: number | null;
  strain: number | null;
  acwr: number | null;
  acute_load: number | null;
  chronic_load: number | null;
}

// Wellness types (Validated Hooper Index)
export interface WellnessEntry {
  id: string;
  athlete_id: string;
  entry_date: string;
  sleep: number;
  fatigue: number;
  stress: number;
  doms: number;
  hooper_index: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface WellnessEntryCreate {
  athlete_id: string;
  entry_date: string;
  sleep: number;
  fatigue: number;
  stress: number;
  doms: number;
  notes?: string;
}

export interface WellnessEntryUpdate {
  entry_date?: string;
  sleep?: number;
  fatigue?: number;
  stress?: number;
  doms?: number;
  notes?: string;
}

// Exercise Library types
export interface ExerciseLibraryItem {
  id: string;
  coach_id: string;
  exercise_name: string;
  exercise_category: string | null;
  default_reps: number | null;
  default_weight_kg: number | null;
  default_tempo: string | null;
  default_rest_seconds: number | null;
  default_duration_seconds: number | null;
  default_distance_meters: number | null;
  default_intensity_type: string | null;
  default_intensity_value: number | null;
  default_rest_between_reps_seconds: number | null;
  default_rep_durations: number[] | null;
  default_rest_between_reps: number[] | null;
  default_rep_intensity_values: number[] | null;
  default_set_configs: { reps?: number; weight_kg?: number }[] | null;
  video_url: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExerciseLibraryCreate {
  exercise_name: string;
  exercise_category?: string;
  default_reps?: number;
  default_weight_kg?: number;
  default_tempo?: string;
  default_rest_seconds?: number;
  default_duration_seconds?: number;
  default_distance_meters?: number;
  default_intensity_type?: string;
  default_intensity_value?: number;
  default_rest_between_reps_seconds?: number;
  default_rep_intensity_values?: number[];
  default_set_configs?: { reps?: number; weight_kg?: number }[];
  notes?: string;
}

export interface ExerciseLibraryUpdate {
  exercise_name?: string;
  exercise_category?: string;
  default_reps?: number;
  default_weight_kg?: number;
  default_tempo?: string;
  default_rest_seconds?: number;
  default_duration_seconds?: number;
  default_distance_meters?: number;
  default_intensity_type?: string;
  default_intensity_value?: number;
  default_rest_between_reps_seconds?: number;
  default_rep_intensity_values?: number[];
  default_set_configs?: { reps?: number; weight_kg?: number }[];
  notes?: string;
}

// Session Template types
export interface TemplateExercise {
  id: string;
  template_id: string;
  exercise_library_id: string | null;
  exercise_name: string;
  exercise_category: string | null;
  order_index: number;
  sets: number;
  reps: number | null;
  weight_kg: number | null;
  tempo: string | null;
  rest_seconds: number | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  intensity_type: string | null;
  intensity_value: number | null;
  rest_between_reps_seconds: number | null;
  rest_between_reps: number[] | null;
  rep_intensity_values: number[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateExerciseCreate {
  exercise_library_id?: string;
  exercise_name: string;
  exercise_category?: string;
  order_index?: number;
  sets?: number;
  reps?: number;
  weight_kg?: number;
  tempo?: string;
  rest_seconds?: number;
  duration_seconds?: number;
  distance_meters?: number;
  intensity_type?: string;
  intensity_value?: number;
  rest_between_reps_seconds?: number;
  rep_intensity_values?: number[];
  notes?: string;
}

export interface SessionTemplate {
  id: string;
  coach_id: string;
  template_name: string;
  training_type: string;
  description: string | null;
  notes: string | null;
  template_category: string | null;
  tier: string | null;
  exercises: TemplateExercise[];
  created_at: string;
  updated_at: string;
}

export interface SessionTemplateCreate {
  template_name: string;
  training_type: string;
  description?: string;
  notes?: string;
  template_category?: string;
  tier?: string;
  exercises?: TemplateExerciseCreate[];
}

export interface SessionTemplateUpdate {
  template_name?: string;
  training_type?: string;
  description?: string;
  notes?: string;
  template_category?: string;
  tier?: string;
  exercises?: TemplateExerciseCreate[];
}

// VBT Profile types
export interface VbtSet {
  id: string;
  profile_id: string;
  set_number: number;
  load_kg: number;
  mean_velocity_ms: number | null;
  peak_velocity_ms: number | null;
  reps: number | null;
  created_at: string;
}

export interface VbtSetCreate {
  load_kg: number;
  mean_velocity_ms?: number;
  peak_velocity_ms?: number;
  reps?: number;
}

export interface VbtAnalysis {
  slope: number;
  intercept: number;
  r_squared: number;
  estimated_1rm_kg: number | null;
  v0_ms: number | null;
  mvt_used_ms: number;
}

export interface VbtProfile {
  id: string;
  athlete_id: string;
  exercise_name: string;
  profile_date: string;
  mvt_ms: number | null;
  notes: string | null;
  sets: VbtSet[];
  analysis: VbtAnalysis | null;
  created_at: string;
  updated_at: string;
}

export interface VbtProfileListItem {
  id: string;
  athlete_id: string;
  exercise_name: string;
  profile_date: string;
  mvt_ms: number | null;
  notes: string | null;
  set_count: number;
  analysis: VbtAnalysis | null;
  created_at: string;
  updated_at: string;
}

export interface VbtProfileCreate {
  exercise_name: string;
  profile_date: string;
  mvt_ms?: number;
  notes?: string;
  sets: VbtSetCreate[];
}

export interface VbtProfileUpdate {
  exercise_name?: string;
  profile_date?: string;
  mvt_ms?: number;
  notes?: string;
  sets?: VbtSetCreate[];
}

export interface VbtPredictionRequest {
  velocity_ms?: number;
  percent_1rm?: number;
}

export interface VbtPredictionResponse {
  predicted_load_kg: number | null;
  predicted_velocity_ms: number | null;
  percent_1rm: number | null;
}

// Movement Assessment types
export interface AssessmentPhoto {
  id: string;
  assessment_id: string;
  view_type: string;
  storage_path: string;
  photo_url: string | null;
  created_at: string;
}

export interface MovementAssessment {
  id: string;
  athlete_id: string;
  assessment_date: string;
  assessment_type: string;
  findings: Record<string, any>;
  notes: string | null;
  summary: string | null;
  photos: AssessmentPhoto[];
  created_at: string;
  updated_at: string;
}

export interface MovementAssessmentListItem {
  id: string;
  athlete_id: string;
  assessment_date: string;
  assessment_type: string;
  findings: Record<string, any>;
  notes: string | null;
  summary: string | null;
  photo_count: number;
  created_at: string;
  updated_at: string;
}

export interface MovementAssessmentCreate {
  athlete_id: string;
  assessment_date: string;
  assessment_type: string;
  findings: Record<string, any>;
  notes?: string;
  summary?: string;
}

export interface MovementAssessmentUpdate {
  assessment_date?: string;
  assessment_type?: string;
  findings?: Record<string, any>;
  notes?: string;
  summary?: string;
}

// Lactate Test types
export interface LactateStage {
  id: string;
  test_id: string;
  stage_number: number;
  intensity_value: number;
  heart_rate_bpm: number | null;
  blood_lactate_mmol: number;
  rpe: number | null;
  created_at: string;
}

export interface LactateStageCreate {
  intensity_value: number;
  heart_rate_bpm?: number;
  blood_lactate_mmol: number;
  rpe?: number;
}

export interface PiecewiseSegment {
  start_x: number;
  end_x: number;
  slope: number;
  intercept: number;
}

export interface LactateAnalysis {
  suggested_lt1_value: number | null;
  suggested_lt1_lactate: number | null;
  suggested_lt2_value: number | null;
  suggested_lt2_lactate: number | null;
  segments: PiecewiseSegment[];
  total_sse: number | null;
  r_squared: number | null;
}

export interface GasSummary {
  max_fat_oxidation_gh: number | null;
  fat_max_intensity: number | null;
}

export interface LactateTest {
  id: string;
  athlete_id: string;
  test_date: string;
  test_type: 'running' | 'cycling';
  lt1_value: number | null;
  lt1_lactate: number | null;
  lt1_hr: number | null;
  lt2_value: number | null;
  lt2_lactate: number | null;
  lt2_hr: number | null;
  notes: string | null;
  stages: LactateStage[];
  analysis: LactateAnalysis | null;
  has_gas_analysis: boolean;
  gas_summary: GasSummary | null;
  created_at: string;
  updated_at: string;
}

export interface LactateTestListItem {
  id: string;
  athlete_id: string;
  test_date: string;
  test_type: 'running' | 'cycling';
  lt1_value: number | null;
  lt1_lactate: number | null;
  lt1_hr: number | null;
  lt2_value: number | null;
  lt2_lactate: number | null;
  lt2_hr: number | null;
  notes: string | null;
  stage_count: number;
  analysis: LactateAnalysis | null;
  has_gas_analysis: boolean;
  gas_summary: GasSummary | null;
  created_at: string;
  updated_at: string;
}

export interface LactateTestCreate {
  test_date: string;
  test_type: 'running' | 'cycling';
  lt1_value?: number;
  lt1_lactate?: number;
  lt1_hr?: number;
  lt2_value?: number;
  lt2_lactate?: number;
  lt2_hr?: number;
  notes?: string;
  stages: LactateStageCreate[];
}

export interface LactateTestUpdate {
  test_date?: string;
  test_type?: 'running' | 'cycling';
  lt1_value?: number | null;
  lt1_lactate?: number | null;
  lt1_hr?: number | null;
  lt2_value?: number | null;
  lt2_lactate?: number | null;
  lt2_hr?: number | null;
  notes?: string;
  stages?: LactateStageCreate[];
}

export interface LactateAutoDetectResponse {
  analysis: LactateAnalysis;
}

// Gas Analysis (CPET) types
export interface GasAnalysisStageSummary {
  stage_number: number;
  intensity_value: number | null;
  avg_vo2_l_min: number | null;
  avg_vo2_ml_kg_min: number | null;
  avg_vco2_l_min: number | null;
  avg_rer: number | null;
  avg_ve_l_min: number | null;
  avg_bf_per_min: number | null;
  avg_vt_l: number | null;
  avg_hr_bpm: number | null;
  avg_fat_gh: number | null;
  avg_cho_gh: number | null;
  avg_ee_kcal_h: number | null;
  avg_cho_ee_kcal_h: number | null;
  avg_fat_ee_kcal_h: number | null;
  data_point_count: number;
}

export interface GasAnalysisPreview {
  interval_seconds: number;
  stage_count: number;
  sample_count: number;
  columns_detected: string[];
  column_mapping: Record<string, string>;
  stage_averages: GasAnalysisStageSummary[];
  fat_max: {
    max_fat_oxidation_gh: number;
    fat_max_stage_number: number;
    fat_max_intensity: number | null;
    fat_max_hr: number | null;
  } | null;
}

export interface GasAnalysisData {
  id: string;
  test_id: string;
  interval_seconds: number;
  rest_start_seconds: number | null;
  stage_duration_seconds: number | null;
  rest_duration_seconds: number | null;
  averaging_method: string | null;
  samples: Record<string, number | null>[];
  stage_averages: GasAnalysisStageSummary[];
  column_mapping: Record<string, string> | null;
  max_fat_oxidation_gh: number | null;
  fat_max_stage_number: number | null;
  fat_max_intensity: number | null;
  fat_max_hr: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// Air Bike Sprint Test types
/** Which mid split a 30s sprint test recorded: 14s (original) or 17s (combine protocol). */
export type AirBikeSplitScheme = '7_14_27' | '7_17_27';

export interface AirBikeSprint {
  id: string;
  test_id: string;
  sprint_number: number;
  power_7s: number;
  /** Populated for '7_14_27' tests only. */
  power_14s: number | null;
  /** Populated for '7_17_27' tests only. */
  power_17s: number | null;
  power_27s: number;
  blood_lactate_mmol: number | null;
  created_at: string;
}

export interface AirBikeSprintCreate {
  sprint_number: number;
  power_7s: number;
  /** Send exactly one of power_14s / power_17s — it selects the protocol. */
  power_14s?: number;
  power_17s?: number;
  power_27s: number;
  blood_lactate_mmol?: number;
}

export interface AirBikeTest {
  id: string;
  athlete_id: string;
  test_date: string;
  body_mass_kg: number;
  split_scheme: AirBikeSplitScheme;
  notes: string | null;
  sprints: AirBikeSprint[];
  created_at: string;
  updated_at: string;
}

export interface AirBikeTestListItem {
  id: string;
  athlete_id: string;
  test_date: string;
  body_mass_kg: number;
  split_scheme: AirBikeSplitScheme;
  notes: string | null;
  sprint_count: number;
  max_power_w: number | null;
  created_at: string;
  updated_at: string;
}

export interface AirBikeTestCreate {
  test_date: string;
  body_mass_kg: number;
  notes?: string;
  sprints: AirBikeSprintCreate[];
}

export interface AirBikeTestUpdate {
  test_date?: string;
  body_mass_kg?: number;
  notes?: string;
  sprints?: AirBikeSprintCreate[];
}

// Invitation types
export interface InvitationResponse {
  id: string;
  athlete_id: string;
  coach_id: string;
  invite_code: string;
  expires_at: string;
  used_at: string | null;
  used_by: string | null;
  created_at: string;
}

export interface InvitationValidateResponse {
  valid: boolean;
  athlete_first_name?: string;
  expires_at?: string;
}

// Test Report types
export interface TestReport {
  id: string;
  athlete_id: string;
  coach_id: string;
  report_date: string;
  date_range_start: string | null;
  date_range_end: string | null;
  sections: Record<string, boolean>;
  notes: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export interface TestReportListItem {
  id: string;
  athlete_id: string;
  report_date: string;
  created_at: string;
}

export interface TestReportCreate {
  athlete_id: string;
  report_date?: string;
  date_range_start?: string;
  date_range_end?: string;
  sections?: Record<string, boolean>;
  notes?: Record<string, string>;
}

export interface TestReportUpdate {
  report_date?: string;
  date_range_start?: string;
  date_range_end?: string;
  sections?: Record<string, boolean>;
  notes?: Record<string, string>;
}

// Upload types
export interface UploadResult {
  processed: number;
  errors: UploadError[];
  athlete_id: string | null;
}

export interface UploadError {
  row: number;
  reason: string;
}

// Program Marketplace types
export interface ProgramExercise {
  exercise_name: string;
  exercise_category: string | null;
  order_index: number;
  sets: number;
  reps: number | null;
  weight_kg: number | null;
  tempo: string | null;
  rest_seconds: number | null;
  duration_seconds: number | null;
  distance_meters: number | null;
  notes: string | null;
  intensity_type: string | null;
  intensity_value: number | null;
  rest_between_reps_seconds: number | null;
  rep_intensity_values: number[] | null;
}

export interface ProgramTemplate {
  id: string;
  program_id: string;
  template_name: string;
  training_type: string;
  order_index: number;
  notes: string | null;
  exercises: ProgramExercise[];
  created_at: string;
  updated_at: string;
}

export interface ProgramPackage {
  id: string;
  created_by: string;
  program_name: string;
  description: string | null;
  category: string;
  cover_image_url: string | null;
  is_published: boolean;
  template_count: number;
  is_installed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProgramPackageDetail extends ProgramPackage {
  templates: ProgramTemplate[];
}

export interface ProgramPackageCreate {
  program_name: string;
  description?: string;
  category?: string;
  cover_image_url?: string;
  is_published?: boolean;
}

export interface ProgramPackageUpdate {
  program_name?: string;
  description?: string;
  category?: string;
  cover_image_url?: string;
  is_published?: boolean;
}

export interface ProgramTemplateCreate {
  template_name: string;
  training_type: string;
  order_index?: number;
  notes?: string;
  exercises?: ProgramExercise[];
}

export interface ProgramTemplateUpdate {
  template_name?: string;
  training_type?: string;
  order_index?: number;
  notes?: string;
  exercises?: ProgramExercise[];
}

export interface InstalledProgramTemplate {
  id: string;
  program_id: string;
  program_name: string;
  template_name: string;
  training_type: string;
  order_index: number;
  notes: string | null;
  exercises: ProgramExercise[];
}

// Air Bike BLE Recording types
export interface BleSample {
  elapsed_ms: number;
  watts: number;
  speed_kmh: number | null;
  cadence_rpm: number | null;
  distance_m: number | null;
  calories_kcal: number | null;
}

export interface AirBikeRecordingCreate {
  test_date: string;
  duration_s: number;
  samples: BleSample[];
  notes?: string | null;
}

export interface AirBikeRecording {
  id: string;
  athlete_id: string;
  test_date: string;
  duration_s: number;
  avg_power_w: number | null;
  peak_power_w: number | null;
  total_work_j: number | null;
  avg_cadence_rpm: number | null;
  peak_cadence_rpm: number | null;
  avg_speed_kmh: number | null;
  total_distance_m: number | null;
  total_calories_kcal: number | null;
  samples: BleSample[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface AirBikeRecordingListItem {
  id: string;
  athlete_id: string;
  test_date: string;
  duration_s: number;
  avg_power_w: number | null;
  peak_power_w: number | null;
  total_work_j: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// Metabolic Profile types
export interface PowerSample {
  elapsed_ms: number;
  watts: number;
}

export interface MetabolicProfileCreate {
  test_date: string;
  body_mass_kg: number;
  data_source: 'ble' | 'manual';
  resting_lactate_mmol: number;
  la_peak_1_mmol: number;
  la_peak_2_mmol: number;
  la_peak_3_mmol: number;
  sprint_1_avg_power_w?: number;
  sprint_2_avg_power_w?: number;
  sprint_3_avg_power_w?: number;
  trim_1_s?: number;
  trim_2_s?: number;
  trim_3_s?: number;
  sprint_1_samples?: PowerSample[];
  sprint_2_samples?: PowerSample[];
  sprint_3_samples?: PowerSample[];
  notes?: string;
}

export interface MetabolicProfileUpdate {
  trim_1_s?: number;
  trim_2_s?: number;
  trim_3_s?: number;
  notes?: string;
}

export interface MetabolicProfile {
  id: string;
  athlete_id: string;
  test_date: string;
  body_mass_kg: number;
  data_source: 'ble' | 'manual';
  resting_lactate_mmol: number;
  la_peak_1_mmol: number;
  la_peak_2_mmol: number;
  la_peak_3_mmol: number;
  sprint_1_avg_power_w: number | null;
  sprint_2_avg_power_w: number | null;
  sprint_3_avg_power_w: number | null;
  alactic_capacity_j: number | null;
  max_glycolytic_power_w: number | null;
  anaerobic_cost: number | null;
  fatigue_slope_w: number | null;
  mech_work_sprint_1_j: number | null;
  mech_work_sprint_2_j: number | null;
  mech_work_sprint_3_j: number | null;
  alactic_1_j: number | null;
  alactic_2_j: number | null;
  alactic_3_j: number | null;
  glycolytic_1_j: number | null;
  glycolytic_2_j: number | null;
  glycolytic_3_j: number | null;
  trim_1_s: number;
  trim_2_s: number;
  trim_3_s: number;
  sprint_1_samples: PowerSample[] | null;
  sprint_2_samples: PowerSample[] | null;
  sprint_3_samples: PowerSample[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MetabolicProfileListItem {
  id: string;
  athlete_id: string;
  test_date: string;
  body_mass_kg: number;
  data_source: 'ble' | 'manual';
  alactic_capacity_j: number | null;
  max_glycolytic_power_w: number | null;
  created_at: string;
  updated_at: string;
}

// Training Block types

export interface BlockExercise {
  exercise_name: string;
  exercise_category?: string | null;
  order_index: number;
  sets: number;
  reps?: number | null;
  weight_kg?: number | null;
  percent_1rm?: number | null;
  rest_seconds?: number | null;
  duration_seconds?: number | null;
  distance_meters?: number | null;
  notes?: string | null;
  intensity_type?: string | null;
  intensity_value?: number | null;
  intensity_min?: number | null;
  intensity_max?: number | null;
  rest_between_reps_seconds?: number | null;
  rep_intensity_values?: number[] | null;
  rep_durations?: number[] | null;
  rest_between_reps?: number[] | null;
}

export interface BlockSession {
  id: string;
  block_id: string;
  week_number: number;
  day_of_week: number;
  session_name: string;
  training_type: string;
  notes: string | null;
  exercises: BlockExercise[];
  created_at: string;
  updated_at: string;
}

export interface BlockSessionCreate {
  week_number: number;
  day_of_week: number;
  session_name: string;
  training_type: string;
  notes?: string | null;
  exercises?: BlockExercise[];
}

export interface BlockSessionUpdate {
  week_number?: number;
  day_of_week?: number;
  session_name?: string;
  training_type?: string;
  notes?: string | null;
  exercises?: BlockExercise[];
}

export interface TrainingBlock {
  id: string;
  coach_id: string;
  block_name: string;
  description: string | null;
  num_weeks: number;
  category: string;
  created_at: string;
  updated_at: string;
}

export interface TrainingBlockDetail extends TrainingBlock {
  sessions: BlockSession[];
}

export interface TrainingBlockCreate {
  block_name: string;
  description?: string | null;
  num_weeks?: number;
  category?: string;
}

export interface TrainingBlockUpdate {
  block_name?: string;
  description?: string | null;
  num_weeks?: number;
  category?: string;
}

export interface UnresolvedExercise {
  athlete_id: string;
  athlete_name: string;
  exercise_name: string;
}

export interface BlockApplyRequest {
  athlete_ids: string[];
  start_date: string;
}

export interface BlockApplyResponse {
  created_count: number;
  sessions_per_athlete: number;
  unresolved_exercises: UnresolvedExercise[];
  application_id: string;
}

export interface WeightResolution {
  athlete_id: string;
  athlete_name: string;
  exercise_name: string;
  percent_1rm: number;
  max_1rm_kg: number | null;
  resolved_weight_kg: number | null;
  source: 'vbt' | 'manual' | 'missing';
}

export interface BlockPreviewResponse {
  resolutions: WeightResolution[];
  total_sessions: number;
  sessions_per_athlete: number;
}

export interface AthleteMax {
  id: string;
  athlete_id: string;
  exercise_name: string;
  max_kg: number;
  source: string;
  updated_at: string;
}

export interface AthleteMaxUpsert {
  exercise_name: string;
  max_kg: number;
  source?: string;
}

// Programme Form types
export interface ProgrammeFormWeek {
  week_number: number;
  reps_text: string;
  sets: number;
  recommended_weight_kg: number | null;
}

export interface ProgrammeFormExercise {
  exercise_name: string;
  order_index: number;
  description?: string;
  slot?: string;
  progressive?: boolean;
  notes?: string;
  weeks?: ProgrammeFormWeek[];
}

export interface ProgrammeFormSection {
  section_type: string;
  circuit_sets?: number;
  exercises: ProgrammeFormExercise[];
}

export interface ProgrammeFormSession {
  session_number: number;
  session_name: string;
  sections: ProgrammeFormSection[];
}

export interface ProgrammeFormData {
  sessions: ProgrammeFormSession[];
}

export interface ProgrammeForm {
  id: string;
  coach_id: string;
  form_name: string;
  description: string | null;
  num_weeks: number;
  sessions_per_week: number;
  form_data: ProgrammeFormData;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// Boxing Science Combine
// ============================================================================

export type CombineStation =
  | 'cmj'
  | 'pogo'
  | 'landmine'
  | 'grip'
  | 'trunk_rotation'
  | 'air_bike';

export type CombineEventStatus = 'draft' | 'live' | 'closed';
export type CombineNameStyle = 'full' | 'first_initial' | 'first_only' | 'bib';
/** What the dynamometers on the day report. Stored canonically in N/s. */
export type CombineRfdUnit = 'n_s' | 'kg_s';
/**
 * Which scale the Combine Score is expressed on.
 *
 * 'z' is the original T-score. 'percentile' ranks within the room instead, which a
 * skewed metric like contact time cannot inflate. Defaults to 'z' everywhere.
 */
export type CombineOverallScoreBasis = 'z' | 'percentile';

export interface CombineEvent {
  id: string;
  coach_id: string;
  event_name: string;
  event_date: string;
  venue: string | null;
  status: CombineEventStatus;
  share_token: string;
  share_url_path: string;
  share_token_expires_at: string;
  share_revoked_at: string | null;
  public_display_consent_confirmed_at: string | null;
  public_name_style: CombineNameStyle;
  show_bs_benchmark: boolean;
  show_club: boolean;
  landmine_exercise_name: string;
  landmine_loads_kg: number[];
  landmine_reference_load_kg: number;
  landmine_reference_tolerance_kg: number;
  landmine_velocity_metric: 'peak' | 'mean';
  /** W/kg only — watts scored against a W/kg norm made every boxer elite. */
  airbike_score_basis: 'w_per_kg';
  rfd_unit: CombineRfdUnit;
  min_stations_for_overall: number;
  /** Set by the operator; the board labels the number according to it. */
  overall_score_basis: CombineOverallScoreBasis;
  bs_norms_updated_at: string | null;
  /** How many Boxing Science athletes back each band, per score key per gender. Never means or SDs. */
  bs_norms_coverage: Record<string, Record<string, number>>;
  results_updated_at: string;
  participant_count: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CombineEventListItem {
  id: string;
  event_name: string;
  event_date: string;
  venue: string | null;
  status: CombineEventStatus;
  participant_count: number;
  attempt_count: number;
  results_updated_at: string;
  created_at: string;
}

export interface CombineEventCreate {
  event_name: string;
  event_date: string;
  venue?: string;
  landmine_reference_load_kg?: number;
  landmine_loads_kg?: number[];
}

export interface CombineEventUpdate {
  event_name?: string;
  event_date?: string;
  venue?: string;
  status?: CombineEventStatus;
  public_name_style?: CombineNameStyle;
  show_bs_benchmark?: boolean;
  show_club?: boolean;
  landmine_exercise_name?: string;
  landmine_loads_kg?: number[];
  landmine_reference_load_kg?: number;
  landmine_reference_tolerance_kg?: number;
  landmine_velocity_metric?: 'peak' | 'mean';
  airbike_score_basis?: 'w_per_kg';
  rfd_unit?: CombineRfdUnit;
  min_stations_for_overall?: number;
  overall_score_basis?: CombineOverallScoreBasis;
  notes?: string;
  public_display_consent_confirmed?: boolean;
}

export interface CombineShareToken {
  share_token: string;
  share_url_path: string;
  share_token_expires_at: string;
  share_revoked_at: string | null;
}

export interface CombineRosterRow {
  athlete_id?: string;
  first_name: string;
  surname?: string;
  gender: 'male' | 'female';
  date_of_birth?: string;
  body_mass_kg?: number;
  club?: string;
  weight_category?: string;
  age_group?: string;
  squad?: string;
  bib?: number;
}

export interface CombineRosterRowResult {
  index: number;
  action: 'linked' | 'created' | 'skipped' | 'error';
  athlete_id: string | null;
  participant_id: string | null;
  matched_name: string | null;
  bib: number | null;
  reason: string | null;
}

export interface CombineRosterResult {
  dry_run: boolean;
  created_athletes: number;
  linked_athletes: number;
  participants_added: number;
  results: CombineRosterRowResult[];
}

export interface CombineParticipant {
  id: string;
  combine_event_id: string;
  athlete_id: string;
  name: string;
  /** The athlete's stored name parts, so a weigh-in edit cannot re-split "Ana Maria Lopez". */
  first_name: string | null;
  surname: string | null;
  gender: 'male' | 'female' | null;
  bib: number;
  club: string | null;
  weight_category: string | null;
  age_group: string | null;
  body_mass_kg: number | null;
  squad: string | null;
  withdrawn_at: string | null;
  created_at: string;
}

/** Station-specific measure payloads. `station` is the discriminator. */
export type CombineMeasures =
  | { station: 'cmj'; height_cm: number }
  | { station: 'pogo'; flight_time_ms?: number; contact_time_ms?: number; rsi?: number }
  | {
      station: 'landmine';
      load_kg: number;
      peak_velocity_ms?: number;
      mean_velocity_ms?: number;
      side?: 'left' | 'right';
    }
  | {
      station: 'grip';
      left_kg?: number;
      right_kg?: number;
      rfd_left_n_s?: number;
      rfd_right_n_s?: number;
      /** The unit the numbers above were typed in; the backend converts to N/s. */
      rfd_unit?: CombineRfdUnit;
    }
  | {
      station: 'trunk_rotation';
      left_kg?: number;
      right_kg?: number;
      rfd_left_n_s?: number;
      rfd_right_n_s?: number;
      /** The unit the numbers above were typed in; the backend converts to N/s. */
      rfd_unit?: CombineRfdUnit;
    }
  | {
      station: 'air_bike';
      sprint_number: number;
      power_7s: number;
      power_17s: number;
      power_27s: number;
      blood_lactate_mmol?: number;
    };

export interface CombineAttemptSubmit {
  participant_id: string;
  measures: CombineMeasures;
  client_attempt_id?: string;
  notes?: string;
}

export interface CombineAttempt {
  id: string;
  combine_event_id: string;
  participant_id: string;
  station: CombineStation;
  attempt_number: number;
  measures: Record<string, number | string | null>;
  value: number | null;
  display_value: string | null;
  voided_at: string | null;
  notes: string | null;
  created_at: string;
}

export interface CombineStationRosterEntry {
  participant_id: string;
  bib: number;
  name: string;
  club: string | null;
  weight_category: string | null;
  body_mass_kg: number | null;
  squad: string | null;
  attempt_count: number;
  best_value: number | null;
  best_display: string | null;
  last_attempt_at: string | null;
  status: 'todo' | 'done';
}

export interface CombineStationRoster {
  station: CombineStation;
  label: string;
  unit: string;
  total: number;
  done: number;
  entries: CombineStationRosterEntry[];
}

export interface CombineCohortStats {
  n: number;
  mean: number | null;
  median: number | null;
  sd: number | null;
  min: number | null;
  max: number | null;
}

export type CombineBsBand = 'elite' | 'above_average' | 'average' | 'developing';

export interface CombineResultRow {
  bib: number | null;
  display_name: string;
  club?: string | null;
  weight_category: string | null;
  age_group: string | null;
  value: number | null;
  display_value: string | null;
  rank: number | null;
  attempts: number;
  z_cohort: number | null;
  bs_band: CombineBsBand | null;
  asymmetry_pct: number | null;
  dominant_side: string | null;
  /** Landmine only — which side the best throw came from. */
  side?: string | null;
  /** Authenticated board only. */
  participant_id?: string;
  athlete_id?: string;
  z_bs?: number | null;
}

export interface CombineStationPanel {
  station: CombineStation;
  label: string;
  short_label: string;
  unit: string;
  decimals: number;
  higher_is_better: boolean;
  cohort_basis: 'event' | 'filtered';
  completed: number;
  stats: CombineCohortStats;
  results: CombineResultRow[];
}

export interface CombineOverallEntry {
  bib: number | null;
  display_name: string;
  club?: string | null;
  weight_category: string | null;
  combine_score: number;
  stations_completed: number;
  eligible: boolean;
  rank: number | null;
  participant_id?: string;
}

export interface CombineLeaderboard {
  event_name: string;
  event_date: string;
  venue: string | null;
  results_updated_at: string;
  participant_count: number;
  filters: Partial<Record<'weight_category' | 'age_group' | 'club' | 'squad', string[]>>;
  stations: CombineStationPanel[];
  overall: CombineOverallEntry[];
  /**
   * Which scale `combine_score` is on. The number alone cannot say whether 59 means
   * a T-score or "beat 59% of the room", so the board reads this to caption itself.
   */
  score_basis: CombineOverallScoreBasis;
  /**
   * Boxers with at least one result that would not write to their athlete record.
   * Only POST /sync reports a real figure — the coach GET hardcodes 0 and the
   * public board omits the field entirely, hence optional.
   */
  unsynced_count?: number;
}

export interface CombineFilterQuery {
  weight_category?: string;
  age_group?: string;
  club?: string;
  squad?: string;
}
