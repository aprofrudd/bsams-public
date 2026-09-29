# CLAUDE.md

## Project Overview

Boxing Science Athlete Management System (BSAMS) - A commercial SaaS for high-performance athlete management. Multi-tenant: external coaches manage own athletes, benchmark against Boxing Science data, and optionally share anonymised data. Production deployed.

## Tech Stack

- **Frontend:** Next.js with TypeScript
- **Backend:** Python FastAPI with Pydantic
- **Database:** Supabase (PostgreSQL with Row-Level Security)
- **Auth:** Supabase Auth (JWT via HttpOnly cookies)

## Build & Run Commands

### Backend
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload  # Dev server
pytest -v                                 # Run all tests (~1430)
pytest tests/test_stat_engine.py -v      # Run specific test file
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # Dev server
npm run build    # Production build
npm test         # Run tests
```

## Critical Security Rules

- JWT in HttpOnly/Secure/SameSite=Lax cookies (NOT localStorage) — auth response returns only `user_id` and `email`, no token in body
- Cookie policy: informational banner (PECR Regulation 6(4) exemption — strictly necessary only). `bsams-cookie-consent` localStorage key for dismiss. `/cookies` page documents all cookies/storage
- `get_current_user()` returns `AuthenticatedUser` (id, role). All routers use `current_user.id` / `current_user.role`
- Access control: `verify_athlete_access()` checks coach_id or user_id; `require_coach_or_admin()` guard; `require_admin()` guard
- Account lockout: 5 failed logins in 15 min -> 429. DB-backed (`login_attempts` table) with IP tracking
- Rate limiting: slowapi (5/min most auth routes, **30/min `/auth/login`**, 10/min uploads, 30/min admin, 60/min general, **1200/min public combine board**). Login is 30/min because every user reaches the API from one proxy address, so a room of station iPads would otherwise share one 5/min bucket with the rest of the product — per-account guessing is caught by the email-keyed lockout instead. The public board limit is keyed on the share token, not the client address. Never set `FORWARDED_ALLOW_IPS=*`
- CORS: dev allows localhost:3000, production only FRONTEND_URL
- Security headers: HSTS (prod only), X-Content-Type-Options, X-Frame-Options, CSP
- Error sanitization: generic 500 in production, detailed in dev. `ENVIRONMENT` config var
- Backend MUST use Supabase service_role key (not anon) to bypass RLS

## CSV Column Defaults

- Date: `Test Date` | Name: `First Name` + `Surname` (or `Athlete`) | Gender: `Gender` | Mass: `Body Mass (kg)`
- Metrics: `CMJ Height (cm)`, `SJ Height (cm)`, `EUR (cm)`, `RSI`, `RSI Flight (ms)`, `RSI Contact (ms)`

## Metric Key -> Display Label

| DB Key | Display Label |
|--------|--------------|
| `height_cm` | CMJ Height (cm) |
| `sj_height_cm` | SJ Height (cm) |
| `eur_cm` | Eccentric Utilisation Ratio (cm) |
| `rsi` | Reactive Strength Index |
| `flight_time_ms` | Flight Time (ms) |
| `contraction_time_ms` | Contact Time (ms) |
| `pogo_rsi` | 10-5 Pogo RSI |
| `pogo_flight_time_ms` | 10-5 Pogo Flight Time (ms) |
| `pogo_contact_time_ms` | 10-5 Pogo Contact Time (ms) |

## Database Tables (Summary)

- `performance_events` — JSONB `metrics` column, GIN indexed, metric-agnostic
- `profiles` — auto-created on signup/login (select+insert, never upsert)
- `athletes` — coach_id FK to profiles, optional user_id for athlete accounts
- `coach_consents` — data sharing opt-in per coach
- `training_sessions` — sRPE generated column, status (assigned/completed/null), created_by
- `wellness_entries` — 5 scores (1-5), UNIQUE(athlete_id, entry_date)
- `exercise_prescriptions` — FK training_sessions CASCADE, conditioning fields, intensity_min/intensity_max range
- `exercise_library` — UNIQUE(coach_id, exercise_name), defaults for autocomplete. Pre-seeded with 361 exercises (admin-owned) from programme spreadsheets
- `session_templates` + `template_exercises` — reusable plans, soft FK to library. Gold-standard conditioning templates: template_category, tier, description
- `vbt_profiles` + `vbt_sets` — load-velocity profiling, regression on-read
- `movement_assessments` + `assessment_photos` — NASM screening, Supabase Storage
- `lactate_tests` + `lactate_stages` — piecewise regression for LT1/LT2
- `gas_analysis_data` — CPET gas analysis (1:1 with lactate_tests), JSONB samples + stage_averages, fat max, VO2max
- `air_bike_tests` + `air_bike_sprints` — 7s/14s/27s power decay
- `air_bike_recordings` — BLE standard mode captures with JSONB samples + computed summary stats
- `metabolic_profiles` — Ferretti/di Prampero 3-sprint protocol with energy system breakdown, trim support
- `program_packages` + `program_templates` + `program_installations` — marketplace programs with JSONB exercises, install=access model
- `training_blocks` + `block_sessions` — coach-owned multi-week program definitions with JSONB exercises, percent_1rm support
- `athlete_maxes` — per-athlete 1RM records (manual or VBT), used for percentage-based loading
- `block_applications` — audit trail of block deployments to athletes
- `athlete_invitations` — 8-char codes, 7-day expiry
- `test_reports` — JSONB sections/notes, coach/admin only
- `user_consents` — GDPR (data_processing/data_sharing/marketing)
- `deletion_log` + `audit_log` — audit trail
- `login_attempts` — DB-backed account lockout (email, ip_address, attempted_at)
- `combine_events` + `combine_participants` + `combine_attempts` — one-day testing events. Attempts are the log; the best is promoted into the real tables tagged `combine_event_id`. Public share token drives the big screen. Per-event `rfd_unit` (N/s or kg/s, always stored as N/s), landmine logged per arm, weight categories restricted to the 20 England Boxing divisions

## API Endpoint Groups

- **Auth:** signup, login, logout, me, forgot-password, reset-password, change-password, change-email, signup/athlete
- **Athletes:** CRUD with pagination, PATCH for profile updates
- **Events:** CRUD with pagination, PATCH for event updates
- **Uploads:** CSV upload (batch insert, auto-creates athletes), CSV preview
- **Analysis:** benchmarks, z-score (single/bulk), available metrics (all accept benchmark_source)
- **Training:** session CRUD, exercise prescriptions (nested), training load analysis
- **Wellness:** entry CRUD, list by athlete
- **Library:** exercise library CRUD (?search=, ?category=), session template CRUD, template apply
- **VBT:** profile CRUD with nested sets + analysis, bidirectional predict
- **Assessments:** movement assessment CRUD, photo upload/delete, signed URLs
- **Lactate:** test CRUD with stages + analysis, auto-detect LT1/LT2, gas analysis upload/preview/get/delete (CPET)
- **Air Bike:** test CRUD with nested sprints, BLE recording CRUD (create/list/get/delete)
- **Metabolic:** profile CRUD with engine computation, PATCH for trim recalculation (BLE only)
- **Reports:** test report CRUD (coach/admin only)
- **Combine:** event CRUD, share token rotate/revoke, roster bulk import (dry-run first), attempt submit/correct/void, station roster, leaderboard, admin-only norms refresh, idempotent sync, and an unauthenticated `GET /combine/public/{token}` board
- **Admin:** shared-athletes (anonymised), shared-athletes events
- **Consent:** GDPR consent CRUD, data sharing consent
- **Export:** athlete data as JSON or ZIP of CSVs (GDPR portability)
- **Programs:** marketplace browse, install/uninstall, installed-templates, admin CRUD (packages + templates), template apply
- **Training Blocks:** block CRUD, session CRUD (add/update/delete/duplicate), apply to athletes with % resolution, preview weight resolution, athlete maxes CRUD

## Backend Structure

```
backend/app/
├── routers/     # auth, athletes, events, uploads, analysis, consent, consent_tracking, admin, combine, training, exercises, wellness, exercise_library, session_templates, programs, training_blocks, vbt, assessments, lactate, air_bike, metabolic, reports, invitations, data_export
├── services/    # csv_ingestion, stat_engine, benchmarks, admin_pool, training_load, vbt_engine, block_engine, lactate_engine, metabolic_engine, conditioning_engine, combine_engine, combine_promotion, combine_norms, cpet_parser, cpet_engine, audit
├── schemas/     # Pydantic models per domain
└── core/        # Config, Supabase client, security (JWT validation)
```

## Key Services

- **StatEngine:** Z-score calculation, benchmarks (Mean, Mode, SD, 95% CI)
- **Ingestion:** CSV parsing (DD/MM/YYYY, BOM handling, auto-create athletes)
- **TrainingLoadEngine:** sRPE, Monotony, Strain, ACWR (optimal 0.8-1.3, danger >1.5)
- **VbtEngine:** Linear regression, 1RM prediction via MVT, bidirectional prediction
- **LactateEngine:** Piecewise 3-segment regression for LT1/LT2 breakpoint detection
- **MetabolicEngine:** Ferretti/di Prampero 3-sprint protocol — sum_watts, alactic capacity, max glycolytic power, energy system breakdown, insights
- **CombineEngine:** per-station bests, cohort stats, competition ranking, within-cohort z, Boxing Science bands, Combine Score. Pure functions — no DB I/O, so the ranking maths is unit-testable
- **ConditioningEngine:** Tier-based intensity resolution for conditioning templates. Resolves target power ranges from metabolic profiles > BLE recordings > sprint tests
- **CpetParser:** Excel/CSV parsing for metabolic cart data (MetaSoft, COSMED, Cortex). Flexible column aliases, stage detection (cycling by power, running by time-boundaries), configurable averaging (last_60s/full_stage)
- **CpetEngine:** Fat max detection, threshold metric interpolation, CHO/FAT crossover, VO2max. TypeScript mirror in `cpetAnalysis.ts`

## Multi-Tenant System

- **Roles:** admin (Boxing Science), coach (external), athlete (linked via invitation)
- **Benchmark Source:** `own` | `boxing_science`. Coaches default to `boxing_science`, admins to `own`
- **Athlete permissions:** Read own data, self-log sessions/wellness (RPE/duration shown on log form), complete assigned sessions, edit exercise reps/weight on assigned sessions. Own sessions: full exercise CRUD + add sets. Cannot upload CSV, manage library/templates

## Development Rules

### Bug Fixing Process
1. Write a test first that reproduces the bug
2. Verify the test fails
3. Implement the fix
4. Verify the test passes
5. Document in BUG_LOG.md

### Code Changes
- If changes require more than 3 files, break into smaller tasks
- List what could break after writing code
- Write tests to cover potential breakages

### Testing Requirements
- All bug fixes must have a corresponding test
- Run full test suite before committing: `python -m pytest tests/ -v`
- Tests in `backend/tests/` use dependency override in conftest.py (not DEV_MODE)
- All statistical calculations require pytest unit tests
- Test edge cases: SD=0, division by zero, mass outside known bands
- Test CSV fixtures use `Test Date` as default date column (not `Date`)

## Combine Events

See `COMBINE.md` for the Boxing Science Combine — one-day testing events with iPad station
entry and a public big-screen board. Covers how to run an event, the attempts-plus-promotion
data model (and why every attempt must NOT go straight into `performance_events`), the public
token endpoint's sanitisation rules, and the decisions still open.

## Extended Reference

See `.claude/rules/` for detailed context (loaded on-demand, not every prompt):
- `technical-decisions.md` — 116 numbered technical decisions and rationale
- `design.md` — color palette, frontend structure, route structure
