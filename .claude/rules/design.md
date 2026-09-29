# Design System

## Color Palette

| Purpose | Hex |
|---------|-----|
| Primary Background | #090A3D |
| Secondary Background | #07083D |
| Accent (buttons, active states) | #33CBF4 |
| Medium Blue | #2074AA |
| Muted Blue (borders, inactive) | #2D5585 |

## Principles

- Dark mode default with high-contrast white text
- Mobile-first (iPad priority)
- All modals use `useFocusTrap` hook for accessibility (Tab/Shift+Tab cycling, Escape to close, focus restore)

## Frontend Structure

```
frontend/
├── app/
│   ├── testing/       # Testing dashboard (CMJ/SJ/EUR/RSI, VBT, Mobility, Isometrics, Lactate, Air Bike)
│   ├── training/      # Training sessions, wellness, load analysis
│   ├── library/       # Exercise database + session templates
│   ├── upload/        # CSV upload
│   ├── login/         # Authentication (login/signup/forgot-password)
│   ├── signup/athlete/ # Athlete signup with invitation code
│   ├── dashboard/     # Athlete-only home page
│   ├── test-report/   # Test report builder (config + preview + PDF export)
│   ├── athlete-info/  # Athlete profile page
│   ├── programs/      # Training program marketplace (browse, install, manage)
│   ├── combine/       # Combine events: console, station entry, public live board
│   ├── settings/      # Account settings (change password, change email)
│   ├── cookies/       # Cookie policy page (PECR/ePrivacy)
│   ├── privacy/       # Privacy policy page (GDPR)
│   └── terms/         # Terms of service page
├── components/
│   ├── testing/       # VBT, Mobility, Lactate, Air Bike, BLE Recordings, Metabolic Profiling views and forms
│   ├── training/      # Session, Wellness, Load, Exercise, Timer, TemplateSessionModal components
│   ├── library/       # Exercise library and template management
│   ├── programs/      # ProgramCard, ProgramDetailModal, ProgramFormModal, ProgramTemplateFormModal
│   ├── blocks/        # BlockCard, BlockListView, BlockBuilderModal, BlockSessionEditor, BlockApplyModal, AthleteMaxesPanel
│   ├── report/        # Report preview and per-section components
│   ├── CookieBanner.tsx # Informational cookie notice (localStorage dismiss)
│   └── ...            # Shared components (AppHeader, AthleteSelector, charts, etc.)
└── lib/
    ├── contexts/      # AthleteContext
    ├── metricRegistry.ts   # Central metric definitions (mirrors backend)
    ├── lactateAnalysis.ts  # Client-side LT1/LT2 breakpoint detection
    ├── metabolicEngine.ts  # Client-side Ferretti/di Prampero metabolic calculations
    ├── bleProtocol.ts      # FTMS Indoor Bike Data BLE parser
    ├── hooks/              # useBleConnection, useBleRecorder, useMetabolicProtocol, useWakeLock
    └── ...            # API client, auth context, hooks, utils
```

## Route Structure

- `/` -> landing page (unauth), athlete->`/dashboard`, coach/admin->`/training`
- `/dashboard` — Athlete-only home page
- `/testing` — Testing dashboard (6 assessment types)
- `/training` — Sessions, wellness, load analysis, exercises
- `/library` — Exercise database + session templates
- `/programs` — Training program marketplace (browse + admin manage) + My Blocks tab (coach/admin)
- `/combine` — Combine events (coach/admin): event list and creation
- `/combine/[eventId]` — Combine console (coach/admin): roster, weigh-in, station progress, event settings, share link, sync
- `/combine/[eventId]/station/[station]` — iPad fast entry for one station
- `/combine/live/[token]` — **public** big-screen board, no login (chrome hidden by `AppChrome`)
- `/test-report` — Report builder (coach/admin only)
- `/athlete-info` — Athlete profile page
- `/upload` — CSV upload (admin + coach)
- `/login` — Authentication
- `/signup/athlete` — Athlete signup with invitation code
- `/reset-password` — Token-based password reset
- `/settings` — Account settings (gear icon in AppHeader)
- `/help` — User manual (? icon in AppHeader + mobile nav)
- `/cookies` — Cookie policy (PECR/ePrivacy compliance)
- `/privacy` — Privacy policy
- `/terms` — Terms of service
