# BSAMS: Boxing Science Athlete Management System

A multi-tenant web app for recording, analysing and sharing athlete testing and training data, built for Boxing Science in 2026. Coaches manage their own athletes, compare them with a Boxing Science benchmark pool, and run one-day testing combines with a live leaderboard.

This repository is a **cleaned public edition** of a private codebase. Athlete data, screenshots, business documents and several physiology analysis modules have been removed; see [What's not included](#whats-not-included).

## What it does

- **Testing:** jump tests (CMJ, SJ, eccentric utilisation ratio, reactive strength index, 10-5 pogo), mobility screening, isometrics and air bike sprint tests, with live power capture from Bluetooth fitness machines. Results are shown as z-scores against the coach's own squad or the Boxing Science benchmark pool.
- **Combine events:** a cohort rotates through six stations, staff enter results on tablets, and a public big-screen board updates within seconds. Results are then promoted into each athlete's record. See [COMBINE.md](COMBINE.md).
- **Training:** session planning and exercise prescription, multi-week training blocks with percentage-based loading from recorded maxes, tiered conditioning templates, and training-load monitoring (session RPE, monotony, strain, acute:chronic workload ratio).
- **Everything around it:** wellness logging, test reports, CSV import, invitation-based athlete accounts, opt-in sharing of anonymised data into a pooled benchmark, GDPR consent tracking and full personal data export.

## Built to a standard

- **Security:** sign-in tokens live in HttpOnly cookies, not browser storage; the database has row-level security policies and the API checks ownership of every athlete record; accounts lock after 5 failed logins in 15 minutes; routes are rate limited; production errors are sanitised.
- **Tests:** about 1,270 backend tests (pytest) and 317 frontend tests (Jest). CI runs both suites and a production build on every push.
- **Decisions and bugs on the record:** [`.claude/rules/technical-decisions.md`](.claude/rules/technical-decisions.md) holds 112 numbered technical decisions with their reasons, [BUG_LOG.md](BUG_LOG.md) records each bug's symptom, root cause and fix, and [CHANGELOG.md](CHANGELOG.md) covers each release.
- **Testable maths:** the combine ranking and scoring engine is pure functions with no database access, and fingerprint tests fail if a change alters the board a default event produces.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI, Pydantic, Python 3.12 |
| Database and auth | Supabase (PostgreSQL with row-level security) |
| Hosting | Vercel (frontend), Railway (backend) |

## Run it

You need a Supabase project. Apply the SQL files in `backend/migrations/` in order (see its README).

```bash
# Backend
cd backend
cp .env.example .env        # add your Supabase URL and service role key
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
python -m pytest             # tests use a fake Supabase client, no database needed

# Frontend
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
npm test
```

## What's not included

- **Data and documents:** athlete data, screenshots, and business, marketing and deployment documents.
- **Analysis modules:** the lactate threshold, CPET gas analysis, metabolic profiling and velocity-based training engines, with their pages, API routes and tests. Their database tables remain in the migrations because the combine, conditioning templates and data export use them.
- **Identifying details:** live deployment addresses, staff names and contact details are replaced with placeholders.

## How it was built

Built by Alan Ruddock, exercise physiologist ([alanruddock.com](https://alanruddock.com)), with Claude Code. [CLAUDE.md](CLAUDE.md) holds the project notes the assistant works from.

## Licence

No licence is granted. The code is shared to show the work, not for reuse.
