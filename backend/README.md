# BSAMS Backend

Boxing Science Athlete Management System - FastAPI Backend

## Setup

### Prerequisites

- Python 3.10+
- Supabase account and project

### Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

Required environment variables:
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — **Must be service_role (secret) key** (not anon key — anon key causes RLS to block server-side queries)
- `ENVIRONMENT` — `development` or `production` (default: `production`)
- `LOG_LEVEL` — Logging level (default: `INFO`)
- `FRONTEND_URL` — Frontend URL for CORS (e.g., `https://your-frontend.vercel.app`)
- `COOKIE_SECURE` — Set to `true` in production for HttpOnly secure cookies

4. Run database migrations in Supabase SQL Editor (see `migrations/README.md`)

5. Create `assessment-photos` private bucket in Supabase Storage dashboard (for mobility photo uploads)

### Running the Server

Development server with hot reload:
```bash
python -m uvicorn app.main:app --reload
```

Production (multi-worker):
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2}
```

## API Documentation

Once the server is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## API Endpoints

### Health Check
- `GET /health` — Pings database, returns `{"status": "healthy"}` or 503 if unreachable

### Authentication
- `POST /api/v1/auth/signup` — User signup (sets HttpOnly cookie, auto-creates profile)
- `POST /api/v1/auth/login` — User login (sets HttpOnly cookie, ensures profile exists)
- `POST /api/v1/auth/logout` — User logout (clears cookie)
- `GET /api/v1/auth/me` — Current user info (returns user_id and role)

### Athletes (requires authentication)
- `GET /api/v1/athletes/` — List all athletes (paginated: skip/limit)
- `GET /api/v1/athletes/{id}` — Get single athlete
- `POST /api/v1/athletes/` — Create athlete
- `PATCH /api/v1/athletes/{id}` — Update athlete
- `DELETE /api/v1/athletes/{id}` — Delete athlete
- `DELETE /api/v1/athletes/` — Delete all athletes
- `POST /api/v1/athletes/merge` — Merge duplicate athletes

### Performance Events (requires authentication)
- `GET /api/v1/events/athlete/{athlete_id}` — List events for athlete (date filters)
- `GET /api/v1/events/{id}` — Get single event
- `POST /api/v1/events/` — Create event
- `PATCH /api/v1/events/{id}` — Update event
- `DELETE /api/v1/events/{id}` — Delete event

### CSV Upload (requires authentication)
- `POST /api/v1/uploads/csv` — Upload and process CSV file (10MB limit, 10K rows max)
- `POST /api/v1/uploads/csv/preview` — Preview CSV without saving

### Analysis (requires authentication)
- `GET /api/v1/analysis/benchmarks` — Benchmark statistics (accepts benchmark_source)
- `GET /api/v1/analysis/athlete/{id}/zscore` — Z-score for single event
- `GET /api/v1/analysis/athlete/{id}/zscores` — Bulk Z-scores for all events
- `GET /api/v1/analysis/athlete/{id}/metrics` — Available metric keys

### Training Sessions (requires authentication)
- `POST /api/v1/training/sessions/` — Create training session
- `GET /api/v1/training/sessions/athlete/{id}` — List sessions for athlete
- `GET /api/v1/training/sessions/{id}` — Get single session
- `PATCH /api/v1/training/sessions/{id}` — Update session
- `DELETE /api/v1/training/sessions/{id}` — Delete session
- `GET /api/v1/training/analysis/load/{id}` — Training load analysis (sRPE, Monotony, Strain, ACWR)

### Exercise Prescriptions (requires authentication)
- `POST /api/v1/training/sessions/{id}/exercises/` — Create exercise prescription
- `GET /api/v1/training/sessions/{id}/exercises/` — List exercises for session
- `PATCH /api/v1/training/sessions/{id}/exercises/{eid}` — Update exercise
- `DELETE /api/v1/training/sessions/{id}/exercises/{eid}` — Delete exercise

### Wellness (requires authentication)
- `POST /api/v1/wellness/` — Create wellness entry (Validated Hooper Index)
- `GET /api/v1/wellness/athlete/{id}` — List wellness entries for athlete
- `GET /api/v1/wellness/{id}` — Get single entry
- `PATCH /api/v1/wellness/{id}` — Update entry
- `DELETE /api/v1/wellness/{id}` — Delete entry

### Exercise Library (requires authentication)
- `GET /api/v1/exercise-library/` — List exercises (supports ?search= and ?category=)
- `POST /api/v1/exercise-library/` — Create library exercise
- `PATCH /api/v1/exercise-library/{id}` — Update library exercise
- `DELETE /api/v1/exercise-library/{id}` — Delete library exercise

### Session Templates (requires authentication)
- `GET /api/v1/session-templates/` — List all templates
- `GET /api/v1/session-templates/{id}` — Get template with exercises
- `POST /api/v1/session-templates/` — Create template
- `PATCH /api/v1/session-templates/{id}` — Update template
- `DELETE /api/v1/session-templates/{id}` — Delete template
- `POST /api/v1/session-templates/{id}/apply` — Apply template to session

### VBT Profiles (requires authentication)
- `POST /api/v1/vbt/profiles` — Create VBT profile with sets
- `GET /api/v1/vbt/profiles/athlete/{id}` — List profiles for athlete
- `GET /api/v1/vbt/profiles/{id}` — Get profile with sets + analysis
- `PATCH /api/v1/vbt/profiles/{id}` — Update profile
- `DELETE /api/v1/vbt/profiles/{id}` — Delete profile
- `POST /api/v1/vbt/profiles/{id}/predict` — Bidirectional prediction (velocity/load)

### Movement Assessments (requires authentication)
- `POST /api/v1/assessments/` — Create movement assessment (NASM checklist)
- `GET /api/v1/assessments/athlete/{id}` — List assessments for athlete
- `GET /api/v1/assessments/{id}` — Get assessment with photos + signed URLs
- `PATCH /api/v1/assessments/{id}` — Update assessment
- `DELETE /api/v1/assessments/{id}` — Delete assessment (CASCADE deletes photos)
- `POST /api/v1/assessments/{id}/photos` — Upload assessment photo (multipart/form-data)
- `DELETE /api/v1/assessments/photos/{id}` — Delete single photo

### Lactate Tests (requires authentication)
- `POST /api/v1/lactate/tests` — Create lactate test with stages
- `GET /api/v1/lactate/tests/athlete/{id}` — List tests for athlete
- `GET /api/v1/lactate/tests/{id}` — Get test with stages + analysis
- `PATCH /api/v1/lactate/tests/{id}` — Update test
- `DELETE /api/v1/lactate/tests/{id}` — Delete test
- `POST /api/v1/lactate/tests/{id}/detect` — Auto-detect LT1/LT2 breakpoints

### Air Bike Tests (requires authentication)
- `POST /api/v1/air-bike/tests` — Create air bike test with sprints
- `GET /api/v1/air-bike/tests/athlete/{id}` — List tests for athlete
- `GET /api/v1/air-bike/tests/{id}` — Get test with sprints
- `PATCH /api/v1/air-bike/tests/{id}` — Update test
- `DELETE /api/v1/air-bike/tests/{id}` — Delete test

### Test Reports (coach/admin only)
- `POST /api/v1/reports/` — Create test report
- `GET /api/v1/reports/athlete/{id}` — List reports for athlete
- `GET /api/v1/reports/{id}` — Get single report
- `PATCH /api/v1/reports/{id}` — Update report
- `DELETE /api/v1/reports/{id}` — Delete report

### Invitations (coach/admin only)
- `POST /api/v1/athletes/{id}/invitations` — Generate invitation code

### Data Sharing / Consent (requires authentication)
- `GET /api/v1/consent/` — Get current consent status
- `PUT /api/v1/consent/` — Update data sharing consent

### GDPR Consent Tracking (requires authentication)
- `GET /api/v1/user-consents/` — Get all consents for current user
- `PUT /api/v1/user-consents/{type}` — Grant/revoke consent

### Data Export (requires authentication)
- `GET /api/v1/export/athlete/{id}` — Export athlete data as JSON
- `GET /api/v1/export/athlete/{id}/csv` — Export athlete data as ZIP of CSVs

### Admin (admin role only)
- `GET /api/v1/admin/shared-athletes` — Anonymised athletes from opted-in coaches
- `GET /api/v1/admin/shared-athletes/{id}/events` — Events for shared athlete

## Testing

Run all tests (about 1,430):
```bash
python -m pytest tests/ -v
```

Run with coverage:
```bash
python -m pytest tests/ -v --cov=app --cov-report=html
```

Run specific test file:
```bash
python -m pytest tests/test_assessments.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application, middleware, CORS, error handling
│   ├── core/
│   │   ├── config.py              # Settings (env vars, API prefix)
│   │   ├── security.py            # JWT validation, AuthenticatedUser dataclass
│   │   └── supabase_client.py     # Supabase client singleton
│   ├── routers/
│   │   ├── auth.py                # Authentication (signup, login, logout, me)
│   │   ├── athletes.py            # Athlete CRUD
│   │   ├── events.py              # Performance event CRUD
│   │   ├── uploads.py             # CSV upload and preview
│   │   ├── analysis.py            # Benchmarks, Z-scores, metrics
│   │   ├── training.py            # Training session CRUD + load analysis
│   │   ├── exercises.py           # Exercise prescription CRUD (nested under sessions)
│   │   ├── wellness.py            # Wellness entry CRUD (Hooper Index)
│   │   ├── exercise_library.py    # Exercise library CRUD
│   │   ├── session_templates.py   # Session template CRUD + apply
│   │   ├── vbt.py                 # VBT profile CRUD + predict
│   │   ├── assessments.py         # Movement assessment CRUD + photo upload
│   │   ├── lactate.py             # Lactate test CRUD + LT1/LT2 detect
│   │   ├── air_bike.py            # Air bike test CRUD + sprint management
│   │   ├── consent.py             # Data sharing consent
│   │   ├── consent_tracking.py    # GDPR user consent
│   │   ├── admin.py               # Admin shared data views
│   │   ├── reports.py             # Test reports
│   │   ├── invitations.py         # Athlete invitation codes
│   │   └── data_export.py         # GDPR data export (JSON + CSV/ZIP)
│   ├── services/
│   │   ├── csv_ingestion.py       # CSV parsing, date/column mapping
│   │   ├── stat_engine.py         # Z-scores, benchmarks (Mean, Mode, SD, CI)
│   │   ├── benchmarks.py          # Mass banding, reference group logic
│   │   ├── admin_pool.py          # Admin/shared athlete queries
│   │   ├── training_load.py       # sRPE, Monotony, Strain, ACWR calculation
│   │   ├── vbt_engine.py          # Linear regression, 1RM prediction, MVT
│   │   ├── lactate_engine.py      # Piecewise regression, LT1/LT2 detection
│   │   └── audit.py               # Audit logging (log_event, log_deletion)
│   └── schemas/
│       ├── athlete.py             # Athlete models
│       ├── performance_event.py   # Event models with metrics validation
│       ├── auth.py                # Auth request/response models
│       ├── upload.py              # CSV upload schemas
│       ├── enums.py               # Gender, UserRole, BenchmarkSource
│       ├── consent.py             # Consent models
│       ├── training_session.py    # Training session models
│       ├── wellness.py            # Wellness entry models (Hooper Index)
│       ├── exercise_prescription.py # Exercise prescription models
│       ├── exercise_library.py    # Exercise library models
│       ├── session_template.py    # Session template models
│       ├── vbt_profile.py         # VBT profile + set models
│       ├── assessment.py          # Movement assessment + photo models
│       ├── lactate_test.py        # Lactate test + stage models
│       ├── air_bike.py            # Air bike test + sprint models
│       ├── metric_registry.py     # Central metric definitions
│       └── invitation.py          # Athlete invitation models
├── migrations/                    # SQL migrations (001-021)
├── tests/                         # Test suite (654 tests)
├── Procfile                       # Railway deployment (multi-worker)
├── start.sh                       # Alternative startup script
├── runtime.txt                    # Python version
├── .env.example
└── requirements.txt               # Pinned dependencies
```

## Data Model

### Core Tables
- **profiles** — Links to Supabase Auth, stores role (admin/coach)
- **athletes** — FK to profiles.coach_id, stores name/gender/DOB
- **performance_events** — JSONB `metrics` column for flexible metric storage

### Training Tables
- **training_sessions** — Session logging with `srpe` generated column (rpe * duration)
- **exercise_prescriptions** — FK to training_sessions (CASCADE), sets/reps/weight + conditioning fields (intensity_type, intensity_value, rest_between_reps_seconds)
- **wellness_entries** — Validated Hooper Index (4 scores 1-7), UNIQUE per athlete per day

### Library Tables
- **exercise_library** — Coach-level reusable exercises, UNIQUE(coach_id, exercise_name)
- **session_templates** — Reusable session plans, UNIQUE(coach_id, template_name)
- **template_exercises** — FK to templates (CASCADE), soft FK to library (SET NULL)

### VBT Tables
- **vbt_profiles** — Load-velocity profiles, UNIQUE(athlete_id, exercise_name, profile_date)
- **vbt_sets** — Individual load-velocity data points, FK to profiles (CASCADE)

### Assessment Tables
- **movement_assessments** — NASM movement screening, JSONB findings, UNIQUE(athlete_id, date, type)
- **assessment_photos** — Photo records, FK to assessments (CASCADE). Files in Supabase Storage

### Lactate Tables
- **lactate_tests** — Lactate threshold tests, UNIQUE(athlete_id, test_type, test_date)
- **lactate_stages** — Stage data points, FK to lactate_tests (CASCADE)

### Air Bike Tables
- **air_bike_tests** — 30s sprint tests, UNIQUE(athlete_id, test_date)
- **air_bike_sprints** — Sprint data (7s/14s/27s power), FK to air_bike_tests (CASCADE)

### Relationship Tables
- **athlete_invitations** — Invitation codes linking coaches to athletes
- **test_reports** — Consolidated athlete test reports (JSONB sections/notes)

### GDPR & Audit Tables
- **user_consents** — GDPR consent tracking (data_processing/sharing/marketing)
- **deletion_log** — Entity summaries recorded before deletion
- **audit_log** — General security event logging

### Multi-Tenant Tables
- **coach_consents** — Data sharing opt-in per coach, UNIQUE(coach_id)

### Rate Limits
- Auth endpoints: 5/min
- CSV uploads: 10/min
- Admin endpoints: 30/min
- General endpoints: 60/min
