# Changelog

All notable changes to BSAMS (Boxing Science Athlete Management System).

## [Unreleased]
### Security
- **Login no longer runs on the shared service-role client.** `login`, `signup` and `signup_athlete`
  authenticate on a throwaway `create_client(...)`. The `supabase` library swaps a client's
  `Authorization` header to the signed-in user's token, so every later query on that worker ran as
  the last person to log in, under their RLS
- `combine_upsert_event_metrics` gets `SET search_path = public` and is revoked from `anon` and
  `authenticated` (migration 034) — Supabase grants EXECUTE on new functions to both by default
- Public combine board: a hidden club can no longer be used as a filter, so hidden club membership
  of named minors cannot be enumerated one club at a time. Only rank-1 rows carry a benchmark band,
  because a band beside every raw value brackets the Boxing Science mean and SD
- The board page is `noindex, nofollow, noarchive` with `Referrer-Policy: no-referrer`

### Added
- **The Combine Score basis is selectable per event** (migration 035). The overall stays the
  T-score `50 + 10 × mean(z)`, or scores on the mean of each boxer's per-station percentiles —
  switched in the console's Event settings card, and safe to change mid-event because scores are
  worked out fresh on every board refresh. **The default is `z`, and a missing column, a NULL or
  an unrecognised value all read as `z`, so every existing event — and one created today — scores
  exactly as it did**; two frozen fingerprints in `test_combine_engine.py` guard a default board
  byte-for-byte. Percentiles are immune to the skew one freak value puts into a z (contact time
  clears z >= 1.0 for only 1.7% of athletes, where normal theory expects 15.9%) and are far easier
  to explain to a 15-year-old; across 119 athletes of the project's own historical data the two
  agree at Spearman 0.982, 8 of the top 10 shared. The cost is honest: percentiles discard margin,
  so dominating a station scores the same as edging it, and at ~40 boxers each place is worth
  roughly 2.5 points, so ties get more common. Ranking, tie order, the eligibility gate and
  `mean_z` are untouched, and the board captions itself to match
- **RFD unit per combine event** (N/s or kg/s). Stored canonically in N/s; kg/s is converted at the
  API boundary and what was typed is kept alongside it (migration 034)
- **Landmine punch is logged per arm.** The board ranks the best of either and shows `L`/`R`;
  promotion writes a VBT profile per side, `… (Left)` / `… (Right)`
- **Strict weight categories** — the 20 England Boxing divisions, shared between backend and
  frontend, with a normaliser accepting `57`, `57 kg`, `91+` and `91kg+`
- **Refresh Boxing Science bands** button in the console, with per-gender coverage counts
- Event settings card: landmine ladder, reference load, tolerance, RFD unit and event date
- Station entry: two-tap void, "Next boxer", a stable `client_attempt_id` across retries, 15 s
  timeouts on station calls, and per-field ranges mirroring the schemas

### Changed
- **Boxing Science bands are gender-matched.** A strong 16-year-old girl previously read
  DEVELOPING, in red, on the public wall against a mostly-male pool. Bands need n ≥ 20 for that
  gender and never fall back to the pooled norm; pre-fix snapshots show no bands until refreshed
- `airbike_score_basis` is `w_per_kg` only — `absolute_w` ranked raw watts against a W/kg norm,
  putting every boxer in the top band and labelling watts "W/kg"
- `/auth/login` raised to 30/min: every user reaches the API from one proxy address, so a room of
  iPads shared one 5/min bucket. Public combine routes raised to 1200/min per share token
- Combine attempt cap per station widened from 20 to 40 (both landmine sides)
- Ties render as `=2nd` and stack on the dot panels; tied rows are ordered by bib so they hold one
  order across every poll
- Rehearsal seed runs under a dedicated non-admin coach and tears down only records carrying its
  own marker
- Docs: COMBINE.md rewritten around the four settled decisions and the event-day working rules,
  technical decisions 117-124, migration 034 and a session-lifetime check in
  `.claude/rules/deployment.md`

### Fixed
- **Combine promotion overwrote same-day manual records.** `_promote_air_bike` and
  `_promote_landmine` matched on athlete + date, so any combine save or void could overwrite or
  delete a manual air bike test or VBT profile dated the event day. Both are now scoped to
  `combine_event_id`
- A station save now merges only its own station's keys, so two iPads cannot roll a best back
- A withdrawn boxer keeps their promoted results through a re-sync
- Attempt saves survive a worker race: a repeated `client_attempt_id` returns the original row
  instead of a 500, and an attempt-number collision retries
- Unpaginated reads no longer stop at PostgREST's 1000-row cap — 40 boxers with both landmine
  sides can exceed it, and the board silently dropped results
- Moving an event's date after results are logged returns 409; otherwise the share link's expiry
  moves with it
- A weigh-in edit no longer rewrites athlete names ("Ana Maria Lopez" became first name "Ana")
- Deleting a participant with logged attempts, and merging away an athlete on a combine roster,
  both return 409 instead of cascading a day's results
- Turning the board off now clears an open TV: three consecutive 404s blank it, while network
  errors, 429s and 5xx keep the last good board
- The offline page recovers on its own via the `online` event and a HEAD probe, instead of sitting
  there until someone presses Try Again
- One failed `/auth/me` no longer signs a station iPad out mid-event; network errors and 5xx retry
- A 401 on a combine page returns to that page after sign-in rather than `/training`
- Kiosk URL parameters are read forgivingly: an unrecognised `?panel=` rotates instead of showing
  nothing, and `?rotate=` is clamped to 5-300s. The dot-panel baselines used `bg-white/8`, for
  which Tailwind 3.4 emits no CSS at all, so they were invisible

---

## [1.23.0] - 2026-09-03
### Added
- **Boxing Science Combine** — one-day testing events with a live big-screen board
  - `combine_events` + `combine_participants` + `combine_attempts` (migration 033). Every attempt is
    logged and soft-voidable; the best is promoted into `performance_events` / `vbt_profiles` /
    `air_bike_tests` tagged `combine_event_id`, so combine data appears in athlete history, reports,
    benchmarks and the GDPR export with no special-casing
  - Six stations: CMJ, 10-5 pogo, landmine punch, grip strength, trunk rotation, air bike
  - Public read-only board at `/combine/live/[token]` — no login, polls every 5s with ETag/304,
    auto-rotating panels, `?panel=` to pin one station to one screen, `?wc=` to filter a weight category
  - Per-station iPad entry screens with a decimal keypad, live RSI and asymmetry feedback, tappable
    attempt chips for corrections, and a confirm step on implausible values
  - Roster import from a pasted list, with a mandatory dry-run preview showing which athletes would be
    created and which linked to existing records
  - Combine Score: mean within-cohort z across the stations each boxer has completed
  - New metric keys: `pogo_flight_time_ms`, `pogo_contact_time_ms`, `pogo_rsi`, and optional
    `grip_rfd_left/right_n_s`, `iso_trunk_rotation_rfd_left/right_n_s`
- **Air bike 7/17/27 split protocol** — `split_scheme` on `air_bike_tests`, nullable `power_17s` on
  `air_bike_sprints`; the original 7/14/27 test is unchanged and still the default

### Changed
- Root layout chrome extracted into `AppChrome`, which hides the header, gutters, footer and cookie
  banner on the kiosk route
- `useWakeLock` re-acquires the lock on `visibilitychange` and releases on unmount — a board left on a
  gym TV all day previously went dark after the first tab switch
- GDPR athlete export now includes combine roster entries and attempts
- Gzip compression enabled on API responses (the board is ~26 KB raw, ~5 KB gzipped)

### Fixed
- `GET /air-bike/tests/athlete/{id}` would raise `TypeError` on a sprint with no 14s split
- Public combine board: hiding club names left the club list exposed in the filter options. The
  `?club=` parameter itself still narrowed the board until the hardening pass above — hiding a
  field has to hide everything derived from it

## [1.22.1] - 2026-02-16
### Fixed
- **Conditioning Save Error: Missing Migrations 022-024**
  - Root cause revealed via new error surfacing: `rep_durations` column did not exist (PGRST204)
  - Migrations 022 (rep_durations), 023 (rest_between_reps), 024 (rep_intensity_values) applied to production Supabase
  - Added try/except with logging around all Supabase INSERT calls in exercises, exercise_library, session_templates
  - INSERT errors now return actual DB error message instead of opaque "Internal server error"
  - Logged data dict + error at ERROR level for Railway log visibility

---

## [1.22.0] - 2026-02-16
### Fixed
- **Conditioning Save Error (Internal Server Error)**
  - Saving conditioning exercises in production returned 500 because migrations 023/024 hadn't been applied
  - Backend `model_dump(exclude_unset=False)` included new JSONB fields as `None` — Supabase rejected unknown columns
  - Fix: filter `None` values from INSERT dicts in exercises, exercise_library, session_templates (create + apply)
  - Defensive fix works both before and after migrations are applied
  - Migrations 023 + 024 now applied to production Supabase

### Changed
- ExerciseTable hides Reps/Weight columns for conditioning sessions (not relevant for timed exercises)

---

## [1.21.0] - 2026-02-16
### Added
- **Per-Rep Intensity Values**
  - `rep_intensity_values` JSONB column on exercise_prescriptions, exercise_library, template_exercises (migration 024)
  - Per-rep intensity inputs inline in ConditioningExerciseForm (e.g., RPE 6/7/8/9 across reps)
  - Auto-select on focus for quick editing of intensity inputs
  - Pydantic validators: non-empty array, length must match reps
  - PATCH consistency guard: changing reps auto-clears stale rep_intensity_values
  - ExerciseTable formatIntensity shows per-rep values as "RPE 6/7/8/9" format
  - 9 new backend tests (684 total)

---

## [1.20.0] - 2026-02-16
### Fixed
- **Conditioning Workflow Fixes**
  - DELETE endpoint 204 response handling (empty body no longer triggers JSON parse error)
  - Category auto-selects to "Conditioning" when training type is Conditioning
  - Per-rep rest stored as JSONB array (migration 023: `rest_between_reps` column)
  - Button labels corrected for add/save actions
  - 12 new backend tests (675 total)

---

## [1.19.0] - 2026-02-15
### Added
- **Conditioning Form Enhancements: Copy Set, Per-Set Rest, Per-Rep Durations**
  - "Copy Set" button on each set card — duplicates config (reps, durations, rest) and inserts rest gap
  - Per-set rest between sets: inline rest inputs between set cards (replaces global rest value)
  - Per-rep durations: variable duration per rep within a set (e.g., pyramid intervals: 15s, 30s, 45s, 60s)
  - `rep_durations` JSONB column on exercise_prescriptions, exercise_library, template_exercises (migration 022)
  - Pydantic validators: non-empty array, values 1-3600, length must match reps
  - PATCH consistency guard: changing reps without rep_durations auto-clears stale array
  - Per-rep UI: single input for 1 rep, compact R1/R2/R3... row for multiple reps
  - Exercise table shows per-rep durations as "15/30/45/60s" format
  - Timer rework: `TimerExercise.sets` changed from flat number to `TimerSetConfig[]` with per-set config
  - Timer supports per-rep duration lookup via `getRepDuration()` helper with scalar fallback
  - Exercise library `default_rep_durations` pre-fills form via autocomplete
  - 9 new backend tests (663 total)

### Changed
- Timer `handleLaunchTimer` builds per-set config arrays preserving individual set durations/rest
- IntervalTimer display uses `sets.length` and per-set reps lookup
- ExerciseTable integrated with remote grouped exercises refactor (collapsible summary rows)

---

## [1.18.0] - 2026-02-13
### Added
- **Conditioning & Interval Training**
  - Conditioning fields on 3 tables: `intensity_type` (rpe/speed_kmh/power_watts), `intensity_value`, `rest_between_reps_seconds` (migration 021)
  - Exercise prescriptions, exercise library, and template exercises all support conditioning data
  - Category-aware forms: Conditioning exercises show intensity type/value/rest-between-reps; others show weight
  - Tempo field removed from all frontend forms (DB column preserved for backward compat)
  - Template apply passes conditioning fields through to prescriptions
  - Pydantic `@field_validator` for intensity_type validation
  - Full-screen interval timer (`IntervalTimer.tsx`) with SVG circular countdown
  - Timer state machine hook (`useIntervalTimer.ts`): idle→warmup→countdown→work→rest→complete
  - Wall-clock `Date.now()` + `requestAnimationFrame` for drift-free timing
  - Auto-pause on tab visibility change
  - Web Audio API beeps (`useTimerAudio.ts`): countdown 3-2-1, phase transitions (zero npm deps)
  - Timer save flow: RPE slider + auto-calculated duration, PATCH session on complete
  - "Timer" button on session rows (coach-only, sessions with timed exercises)
  - `duration_seconds` / `default_duration_seconds` input on all exercise forms (ExerciseTable, TemplateFormModal, ExerciseLibraryFormModal) — required for timer to function
  - Duration column in exercise table display
  - 18 new backend tests (654 total)

### Changed
- Exercise forms no longer show tempo field (replaced by conditioning intensity fields)
- ExerciseAutocomplete pre-fills intensity defaults from library (instead of tempo)
- ExerciseTable intensity column replaces tempo column in table display

---

## [1.17.0] - 2026-02-09
### Added
- **Air Bike 30s Sprint Test**
  - `air_bike_tests` + `air_bike_sprints` database tables (migration 016)
  - Flat column design for fixed 7s/14s/27s time points with 2 sprints max
  - Body mass recording per test, optional blood lactate per sprint
  - Full CRUD API: `/air-bike/tests` endpoints with nested sprint management
  - Replace-all semantics for sprint updates (delete all, re-insert)
  - 409 on duplicate athlete+date
  - Frontend: AirBikeView (expandable cards with results table), AirBikeTestForm (modal)
  - AirBikeChart: power decay comparison (Sprint 1 cyan, Sprint 2 amber) with Line + Scatter
  - Results table: W/kg calculations, % relative to Sprint 1 peak power
  - Decay analysis: within-sprint decay (7s→14s, 14s→27s, 7s→27s) and between-sprint comparison
  - 13 new backend tests (484 total)

### Changed
- Testing page now has 6 tabs: Jump Assessments, VBT Assessments, Mobility Assessments, Isometrics, Lactate Profile, Air Bike
- Tab container uses flex-wrap to prevent overflow with 6 tabs

## [1.16.0] - 2026-02-09
### Added
- **Lactate UX Improvements**
  - Chart uses line graphs connecting scatter dots for lactate (cyan) and HR (amber)
  - Threshold editing moved from form to expanded view (Auto-Detect + Save Thresholds)
  - Chart axis formatting: whole-number X ticks, HR Y-axis in 10s, LT1/LT2 labels insideTopRight
  - R² badge removed from lactate profile cards

### Changed
- Testing tabs renamed: Jump Assessments, VBT Assessments, Mobility Assessments

## [1.15.0] - 2026-02-09
### Added
- **Lactate Profile Tab**
  - `lactate_tests` + `lactate_stages` database tables (migration 015)
  - Piecewise 3-segment regression engine for LT1/LT2 breakpoint auto-detection
  - Client-side TypeScript port of lactate analysis (`lactateAnalysis.ts`)
  - Full CRUD API: `/lactate/tests` endpoints + `/detect` for server-side breakpoint detection
  - Frontend: LactateProfilesView, LactateTestForm, LactateChart (dual-axis: lactate + HR)
  - 32 new backend tests (lactate engine: 19, lactate router: 13)

## [1.14.0] - 2026-02-08
### Added
- **Athlete Information Page**
  - `first_name`, `surname`, `body_mass_kg`, `stature_cm`, `status`, `notes` columns on athletes table (migration 014)
  - Database trigger syncs `name` from `first_name || ' ' || surname`
  - `/athlete-info` page with full profile form
  - Navigation item + "View Full Profile" link in AthleteEditModal
  - 8 new backend tests

## [1.13.1] - 2026-02-08
### Added
- **Isometrics + Per-Category Radar**
  - 6 isometric metrics added to metric registry (IMTP peak force, DSI, etc.)
  - 12 CSV column mappings for isometric metrics
  - 4th Isometrics tab on Testing page
  - `metricFilter` prop on ZScoreRadar for per-tab filtering
  - VbtRadar component with placeholder benchmarks
  - Conditional empty states for tabs with no metrics data
  - 7 new backend tests

## [1.13.0] - 2026-02-08
### Added
- **Mobility Assessment Module** (NASM Movement Screening)
  - `movement_assessments` + `assessment_photos` database tables (migration 013)
  - NASM structured checklist: overhead squat, single leg squat (left/right)
  - 5 kinetic chain checkpoints: feet/ankles, knees, LPHC, shoulders, head
  - Severity grading: mild, moderate, significant
  - Side tracking: left, right, bilateral
  - Photo upload to Supabase Storage (private bucket, signed URLs)
  - Auto-generated summary from observed compensations
  - Full CRUD API: `/assessments/` endpoints + `/assessments/{id}/photos`
  - Frontend: MobilityView (expandable cards), AssessmentForm (NASM checklist modal)
  - 19 new backend tests

### Changed
- Testing page "Metrics" tab renamed to "Jump Analysis"
- Testing page now has 3 tabs: Jump Analysis, VBT Profiles, Mobility

## [1.12.0] - 2026-02-06
### Fixed
- VBT chart Y-axis now scales to actual data point velocities (not regression intercept)
- VBT analysis uses peak velocity as fallback when mean velocity absent

## [1.11.0] - 2026-02-05
### Added
- **VBT Load-Velocity Profiling System**
  - `vbt_profiles` + `vbt_sets` database tables (migration 012)
  - VBT engine: linear regression, 1RM prediction via MVT, bidirectional prediction
  - Default MVTs per exercise (Trap Bar Deadlift 0.30, Bench Press 0.17, etc.)
  - Full CRUD API: `/vbt/profiles` endpoints + predict endpoint
  - Frontend: VbtProfilesView, VbtProfileForm, VbtChart, VbtCalculator
  - Testing page split into Metrics / VBT Profiles toggle
  - 32 new backend tests

## [1.10.0] - 2026-02-04
### Added
- Tabbed event form with separate sections for jump metrics
- Trend lines on performance graphs
- Mobile-responsive template picker fixes

## [1.9.0] - 2026-02-03
### Added
- Mobile responsive navigation
- Redesigned training page with sessions-first layout and expandable cards

## [1.8.0] - 2026-02-02
### Added
- **Exercise Database & Session Templates**
  - `exercise_library` table (migration 010): coach-level reusable exercises with defaults
  - `session_templates` + `template_exercises` tables (migration 011)
  - Library page with Exercises/Templates tabs
  - ExerciseAutocomplete: client-side combobox with keyboard nav, pre-fills defaults
  - TemplatePickerModal: import template exercises into sessions
  - Template apply endpoint with set expansion (sets:3 -> 3 prescription rows)
  - 34 new backend tests (exercise library: 17, session templates: 17)

## [1.7.0] - 2026-01-31
### Changed
- **UX Redesign Phase 1**
  - Chakra Petch (headings) + Roboto (body) font system
  - Athlete selector moved from sidebar to header dropdown
  - Full-width page layouts (no sidebar)
  - `.section-title` utility class for consistent heading styles

### Fixed
- Training load/readiness not updating after session or wellness changes
- Y-axis labels and grid lines on training load chart

## [1.6.0] - 2026-01-28
### Added
- **Testing & Training Restructure** (8 phases)
  - Route restructure: Dashboard renamed to Testing, new Training section
  - Shared athlete context (AthleteContext) across Testing and Training pages
  - Training sessions: session logging with RPE, duration, computed sRPE
  - Training frontend: SessionLogForm, SessionTable, LoadChart, ReadinessIndicator
  - Wellness system: Validated Hooper Index (4 scores, 1-7 scale), UNIQUE per day
  - Training load analysis: daily load, weekly load, monotony, strain, ACWR
  - Exercise prescriptions: nested under sessions, sets/reps/weight/tempo/rest
  - Metric registry: central source of truth (backend + frontend mirror)
  - Migrations 006-009 (training sessions, wellness, exercise prescriptions, hooper index)
  - 75 new backend tests

## [1.5.0] - 2026-01-24
### Added
- **Production Hardening** (Tier 1-3)
  - access_token removed from auth response body (HttpOnly cookie only)
  - 401 interceptor: auto-redirect to login on expired session
  - Pinned dependencies in requirements.txt
  - Metrics validation on create/update only (not response)
  - Error sanitization: generic 500 in production, detailed in development
  - Request logging middleware (method, path, status, duration)
  - DB health check endpoint (/health)
  - Admin N+1 fix: single `.in_()` query
  - Focus trapping in all modals (useFocusTrap hook)
  - Sync endpoints (def not async def) to avoid event loop blocking
  - Multi-worker support via Procfile
  - Admin rate limits (30/min)
  - Shared pool benchmarks, boolean filter fix

## [1.4.0] - 2026-01-20
### Added
- **Multi-Tenant External Coach Support**
  - Admin (Boxing Science) and coach (external) roles
  - BenchmarkSource enum: own, boxing_science, shared_pool
  - Data sharing consent system (coach_consents table, migration 005)
  - Admin shared data view (anonymised athletes from opted-in coaches)
  - Manual athlete add (AthleteCreateModal)
  - Profile auto-creation on signup/login (select+insert, never upsert)
  - Frontend role awareness, admin tab toggle

## [1.3.0] - 2026-01-16
### Added
- **ZScoreRadar Redesign**
  - Date selection dropdown for primary event
  - Composite metric picker (fills missing metrics from other dates)
  - Zone bands (green/cyan/yellow/red at Z=3/1/0/-1)
  - Dot color-coding by Z-score
  - Dashed ring on override-sourced dots

## [1.2.0] - 2026-01-14
### Added
- **Inline CRUD**
  - Add/edit/delete events via modal from PerformanceTable
  - Edit athlete profile (name/gender/DOB) from AthleteSelector
  - Auto-calculated EUR and RSI (computed on save)

## [1.1.0] - 2026-01-10
### Added
- **Multi-Metric Dashboard**
  - MetricSelector reads available metrics dynamically from backend
  - MetricBarChart visualization
  - Dynamic benchmarks for all reference groups
  - Date filtering and entry toggle pills
  - On-demand radar plot

### Changed
- Line chart replaced with bar chart for performance data
- Y-axis 5cm ticks, improved mean label

## [1.0.0] - 2026-01-04
### Added
- **Core System (Phase 1-4)**
  - Supabase Auth with JWT in HttpOnly cookies
  - Athletes and performance events CRUD
  - CSV upload with preview, batch insert, auto-create athletes
  - Statistical engine: Z-scores, benchmarks (Mean, Mode, SD, 95% CI)
  - Mass banding (5kg increments)
  - Performance graph (Recharts) and table with dynamic Z-scores
  - Reference group switching (cohort, gender, mass band)

- **Security Hardening**
  - DEV_MODE removed, production-only auth
  - Rate limiting (slowapi)
  - CSV limits (10MB, 10K rows)
  - Input validation on all endpoints

- **Performance Optimization**
  - Batch inserts for CSV upload
  - Bulk Z-score calculation
  - Pagination on list endpoints
  - Database indexes

- **Deployment**
  - Backend on Railway
  - Frontend on Vercel
  - GitHub Actions CI (pytest on push to main)
  - Trailing slash proxy fix for Vercel/FastAPI
