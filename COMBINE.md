# Boxing Science Combine

A one-day testing event: a cohort of boxers rotates through six stations, staff enter
results on iPads, and a public big screen in the gym updates within seconds.

Built September 2026. Technical decisions 112-124 in `.claude/rules/technical-decisions.md`
record the rationale; this document is the working reference.

---

## Running an event

**Before the day**

1. `/combine` → name, location, date → **New combine**.
2. Add the roster: **+ Add boxer** one at a time, or **Paste a list** for a roster sent
   ahead. The paste import has a mandatory preview showing which rows would create a new
   athlete and which would link to one already on the account — that preview is the guard
   against creating forty duplicates.
3. **Event settings**: the landmine load ladder, reference load and tolerance, and the **RFD unit**
   your dynamometers read (N/s or kg/s — kg/s is converted on the way in, never stored raw). Set the
   RFD unit before the grip and rotation stations start. The **event date** is not in this card — it
   sits beside the location at the top of the console. It can be moved until the first attempt is
   logged, and moving it moves the share link's expiry with it; after that it is refused, because
   promoted rows are keyed on it.
4. As an admin, press **Refresh Boxing Science bands** once the landmine settings are final — and
   again if they change. Bands are gender-matched and need n ≥ 20 for that gender, so any key below
   that is named in the console and simply shows no band.

**On the day**

5. Weigh-in: tap each boxer on the roster and fill in body mass. The header counts how many
   are still missing it — the air bike cannot compute W/kg without it.
6. Confirm the public-display consent, then **Go live**. The board will not serve until
   consent is confirmed, because these are usually minors on an unauthenticated URL.
7. Open the board on the gym TV (**Open board**, or copy the link). Two screens: pin the
   summary to one with `?panel=summary`, leave the other rotating. The console shows
   **Link valid until …** beside the share link, in amber once it has expired; **New link**
   and **Turn off** both ask to confirm, because either one blanks a TV that is already up.
8. Each station opens `/combine/{eventId}/station/{station}` on an iPad.

**After**

9. **Re-sync results** rebuilds every athlete's promoted record from the attempt log. It is
   idempotent, so it is safe to press whenever something looks out of step — and it is the
   repair button if a save ever fails mid-event. It needs no confirm.
10. **Turn off** revokes the public link. A board already on the TV clears itself and shows
    "Board unavailable" — it takes about half a minute, because the three 404s it waits for are
    spaced by the poller's 10s and 20s backoff. The link also expires on its own two days after
    the event date.

### Working rules for the day

These are not preferences. Each one is a way the day can go wrong.

- **Open each station in an ordinary Safari tab, not Add to Home Screen.** The web-app
  manifest reopens on `/testing`, so a home-screen icon does not come back to the station.
- **Sign the iPads in one at a time**, and check each one saves before moving on. A 401 on a
  station page returns to *that station* after sign-in, not `/training`.
- **Nobody taps Logout on any device.** Logout calls `admin.sign_out(user_id)`, which is
  global: one tap signs out every iPad and the console.
- **The session ends at JWT expiry.** The cookie holds only an access token and nothing
  refreshes it yet (a refresh cookie is in "Still open" below). Confirm before the event that
  the Supabase access-token lifetime covers the whole day — see `.claude/rules/deployment.md`.
- **If the account locks out**, five failed sign-ins in fifteen minutes return 429 and the
  *correct* password is refused too. Clear it in the Supabase SQL editor:
  `DELETE FROM login_attempts WHERE email = '<the account email>';`
- **Refresh the bands again if the landmine settings change.** The snapshot does not record
  which reference load it was built with, so a stale landmine band is only caught by doing this.
- **Weigh in until the console's missing-body-mass count reads 0.** The air bike cannot rank a
  boxer without mass; a late weigh-in does create the bike test, but only for attempts already
  logged.

---

## The six stations

| Station | Captured | Ranked on |
|---|---|---|
| **CMJ** | jump height (cm) | best jump |
| **10-5 Pogo** | flight time, contact time (ms); RSI derived server-side, or entered directly | best RSI |
| **Landmine Punch** | velocity at each load on the ladder, per arm (**Left / Right**) | best velocity of **either arm** at the **reference load** (default 20 kg ± 1 kg), on the event's configured metric |
| **Grip** | peak force left/right (kg), optional RFD in the event's unit | better side |
| **Trunk Rotation** | peak force left/right (kg), optional RFD in the event's unit | better side |
| **Air Bike** | 2 × 30s sprint, power at **7 / 17 / 27 s** | peak 7s power in **W/kg** |

Every attempt is logged, not just the best. Attempts are soft-voided rather than deleted, so
what was actually recorded on the day survives a correction.

Landmine attempts away from the reference load are stored and kept in the athlete's
load-velocity profile, but do not appear on the board — the board compares like with like.

Left/right asymmetry is a **station screen** reading: it appears as the second side is typed,
so the operator can retest on the spot. The board ranks and shows the better side only — an
asymmetry percentage on a public wall is a clinical finding about a named minor.

---

## Where the data goes

This is the one design decision worth understanding before changing anything.

```
station iPad  →  combine_attempts  →  promotion  →  performance_events
                 (every attempt)       (the best)    vbt_profiles
                                                     air_bike_tests
```

**Attempts are the log.** `combine_attempts` holds every jump, throw and sprint, tagged to the
event, soft-voidable.

**Promotion writes the best into the real tables**, tagged `combine_event_id`, so combine
results appear in athlete history, test reports, benchmarks and the GDPR export with no
special-casing anywhere else in BSAMS.

**Exactly one `performance_events` row exists per athlete per combine**, enforced by a partial
unique index. This matters: `analysis.py` builds cohort benchmarks from *all* events for the
reference athletes, so writing one row per attempt would weight the squad mean by however many
jumps each boxer happened to take. The four JSONB stations (CMJ, pogo, grip, trunk rotation)
merge into that single row; landmine becomes a VBT profile, air bike an air bike test.

Concurrency: the station-save path merges one station's keys through the
`combine_upsert_event_metrics` RPC, which is atomic across both uvicorn workers. A void or a
manual sync rebuilds the whole row instead — the only way to clear a station whose every
attempt has been voided.

### Tables (migration `033_boxing_science_combine.sql`)

- `combine_events` — the event, its share token, display policy, scoring config, and a
  `bs_norms_snapshot` of Boxing Science aggregates
- `combine_participants` — the roster: bib, club, weight category, age group, weigh-in mass
- `combine_attempts` — every attempt; JSONB column is `measures` (`values` is reserved SQL)
- nullable `combine_event_id` on `performance_events`, `vbt_profiles`, `air_bike_tests`
- `air_bike_tests.split_scheme` (`7_14_27` | `7_17_27`) and a nullable
  `air_bike_sprints.power_17s`; `power_14s` dropped `NOT NULL` with a check that one mid split
  is present

### Metric keys added

10-5 pogo gets its own keys because there was exactly one `rsi` key and it is CSV-tagged as
CMJ — reusing it would silently merge two different tests.

`pogo_flight_time_ms` · `pogo_contact_time_ms` · `pogo_rsi` · `grip_rfd_left_n_s` ·
`grip_rfd_right_n_s` · `iso_trunk_rotation_rfd_left_n_s` · `iso_trunk_rotation_rfd_right_n_s`

Peak force reuses the existing `grip_strength_*_kg` and `iso_trunk_rotation_*_kg` keys, so the
benchmark comparison worked from day one.

**New isometric keys must be appended, never inserted** — `testing/page.tsx` defaults the
Isometrics tab to `ISOMETRIC_METRIC_KEYS[0]`. A Jest test guards this.

---

## Scoring

**Per station** — within-cohort z-score against the boxers on the board. Lower-is-better
metrics invert, so a fast contact time scores positively.

**Combine Score** — the overall number sits on one of two scales, chosen per event by
`overall_score_basis`. **The default is `z`, and it stays `z`: an event created today scores
exactly as it did before this option existed.** A row written before the column, a NULL, and an
unrecognised value all read as `z` as well — switching is something the operator does
deliberately, never something that happens to them. Two frozen fingerprints in
`test_combine_engine.py`, taken from the engine before the option existed, assert that a default
event's authenticated and public boards are byte-identical to what they were.

- **`z` (default)** — `50 + 10 × mean(z across the stations that boxer has completed)`, clamped
  0-100. A T-score: 50 is the room's average, 10 points is one SD.
- **`percentile`** — the mean of that boxer's per-station percentiles, to 1 dp. A station
  percentile is the share of the displayed cohort they beat: a clean spread of three runs
  0 / 50 / 100, ties take the midpoint of the positions they span (10, 20, 20 gives 0, 75, 75),
  everyone tied sits at 50, and the first boxer through a station scores 50 — they have beaten
  nobody and lost to nobody.

Missing stations are ignored under either basis, rather than counted as zero, so nobody is
punished for the timetable. A boxer below `min_stations_for_overall` (default 3) is scored but
not ranked: the console's leaderboard still lists them, while the big screen's Combine Score
panel shows the ranked ten only, so they reach the wall at their third station. Listing them
there as "not yet ranked" is in **Still open** below.

Switching the basis changes that one number and nothing else. Competition ranking, the
`(rank, bib, display_name)` tie order, the eligibility gate, the per-station z-scores and the
Boxing Science bands are all untouched, and `mean_z` stays authenticated-only and keeps meaning
mean z — it is the coach's diagnostic, not the displayed score. `build_leaderboard` returns
`score_basis` at the top level so the board captions itself: the Combine Score panel reads "50
is the room average" on `z` and "100 beats the whole room" on `percentile`, because the first is
a claim about a T-score and is simply false beside a percentile.

**Where to switch it** — the console's **Event settings** card, "Combine Score basis": *T-score,
50 is the room average* / *Percentile, share of the room beaten*. Safe to change mid-event;
scores are worked out fresh on every board refresh and nothing is stored.

**Why percentiles are offered at all** — on 119 athletes of the project's own historical data the
two composites agree almost perfectly: Spearman 0.982, and 8 of the top 10 are the same boxers.
They part company exactly where one freakish value on a skewed metric inflates a z. Contact time
is the worst case: only 1.7% of athletes clear z >= 1.0, where normal theory expects 15.9%. A
percentile cannot be inflated that way — one outlier changes the order, never the spacing — and
"you beat 75% of the room" explains itself to a 15-year-old.

**What percentiles cost** — they throw away margin: dominating a station scores exactly the same
as edging it. And the scale is coarser the smaller the room; with about 40 boxers each place is
worth roughly 2.5 points, so ties get more common and the tie rules below do more work.

**Boxing Science bands** — `elite` ≥ 1.0, `above_average` ≥ 0.25, `average` ≥ −0.75,
`developing` below. Emitted only where the norm has n ≥ 20.

Ranking is competition-style: equal values share a rank and the next rank skips.

Filtering to a weight category with fewer than 5 boxers falls back to whole-event statistics
and says so — z-scores over three people are noise.

---

## Screens

| Route | Who | What |
|---|---|---|
| `/combine` | coach/admin | event list and creation |
| `/combine/{id}` | coach/admin | console: roster, station progress, share link, display policy, sync |
| `/combine/{id}/station/{station}` | coach/admin | iPad fast entry |
| `/combine/live/{token}` | **public** | the big screen |

**Big screen URL parameters**

- `?panel=` — pin one panel: `summary`, `cmj`, `pogo`, `landmine`, `grip`, `trunk_rotation`,
  `air_bike`, `overall`
- `?rotate=15` — seconds per panel (default 20)
- `?wc=` / `?age=` / `?club=` — filter the room

Parameters are read forgivingly, because these are typed onto a TV by hand: an unrecognised
`?panel=` rotates rather than showing nothing, and `?rotate=` is clamped to 5-300s.

The rotation opens with the summary, then cycles the stations that have results and the
Combine Score. Panels nobody has reached yet are skipped.

**Panels use dots, not bars.** A bar's length is its encoding so it must start at zero, which
for a cohort jumping 45-51 cm rendered ten near-identical bars. A dot encodes position, so the
scale zooms to the top ten and the range is labelled at both ends.

`AppChrome` hides the app header, gutters, footer and cookie banner on `/combine/live/*` so the
board fills the screen. Type is vh-relative throughout — `text-[5vh]` headings, `text-[7vh]` for
the leading value — so one board suits a 55" TV and a 27" monitor without a breakpoint.

**Station entry** — pick a boxer from the to-do list, type on a decimal keypad, save. Live RSI
as flight and contact are typed; live asymmetry as left and right are typed; Left/Right chips on
landmine, which reset on a new boxer. Logged attempts are tappable chips that void in two taps —
the first tap arms the chip ("Tap again to remove") and disarms after four seconds.

The screen is built around a tired operator on gym Wi-Fi:

- Every field carries the `min`/`max` from `schemas/combine.py`, and SAVE stays disabled with a
  hint while a value is out of range, rather than bouncing a 422 back from the server.
- A value more than 50% above anything logged so far turns SAVE amber and asks for a second tap —
  the missed-decimal catch. It compares like with like: RSI against RSI, W/kg against W/kg, the
  better side on grip and trunk, and landmine only at the reference load.
- Station calls time out at 15s with "Timed out — check the connection and tap SAVE again". The
  `client_attempt_id` is kept across that failure and only re-minted when the payload actually
  changes, so tapping SAVE again resolves to the same single attempt.
- Saving keeps the boxer on screen. **Next boxer →** moves on deliberately, to the first boxer
  with something still to do.

---

## The public board

Unauthenticated. The share token in the URL is the only credential, and the backend holds the
Supabase service_role key, so **RLS protects nothing on this path — the Python field projection
is the security boundary.**

- Token is `secrets.token_urlsafe(24)` — 24 random bytes, **192 bits** — expires at event date
  + 2 days, and can be rotated or revoked from the console
- Unknown, expired, revoked, draft and consent-not-confirmed all return a **byte-identical
  404**, so the endpoint never discloses whether a token exists
- Rate limited 1200/min **keyed on the token, not the client address** — every device in the gym
  reaches the API through the same proxy, so an IP bucket would throttle the whole venue as one
  client, and the bucket is shared by every screen showing the link (304s count too)
- Polled every 5s with `If-None-Match`; an unchanged board costs a ~200 byte 304, which carries
  `Cache-Control: no-cache` alongside the `ETag` so no proxy answers the next poll from its own copy
- Three consecutive 404s blank an open board. Network errors, 429 and 5xx keep the last good one —
  a blip must not wipe the wall — but a 404 is the one response that means *deliberately gone*,
  and until this existed **Turn off never took names off a TV that was already on**

**Never leaves the server on this path:** athlete or participant ids, date of birth, gender,
body mass, email, notes, the norms snapshot, or a numeric benchmark z.

Two of those need saying out loud:

- **A band, not a z-score, and only on the leader.** A numeric z published beside the raw value
  for a whole cohort lets anyone solve for the Boxing Science mean and SD. A band is not
  invertible on its own — but a band on *every* row brackets the same mean and SD between the
  fixed thresholds, so the public payload bands rank 1 and nothing else. That is also the only
  row the kiosk draws a band for. ("ELITE" reads better on a wall than "z = +0.87" anyway.)
- **W/kg only on the bike.** Publishing absolute watts *and* W/kg makes body mass derivable.

Names default to full, switchable to `Jack R.`, first name, or bib number from the console.
Club can be hidden — which withholds the club list from the filter options *and* makes `?club=`
a no-op, dropped before the filters, the ETag and the cache key. A hidden field has to hide
everything derived from it: a club filter that still worked would let anyone enumerate the
hidden club membership of named minors, one club at a time.

---

## Files

**Backend** — `routers/combine.py`, `schemas/combine.py`, `services/combine_engine.py`
(pure ranking maths, no I/O), `services/combine_promotion.py`, `services/combine_norms.py`,
`migrations/033_boxing_science_combine.sql`

**Frontend** — `app/combine/`, `components/combine/`, `lib/combineDisplay.ts`,
`lib/combineParticipantForm.ts`, `lib/hooks/useCombinePolling.ts`, `useCombineRotation.ts`,
`components/ui/NumericKeypad.tsx`, `components/AppChrome.tsx`, `lib/airBikeSplits.ts`

**Rehearsal** — `scripts/seed_combine.py` creates an event with ~38 fake boxers and results
across all six stations and prints the board URL. `--partial` leaves stations incomplete, as
the room looks mid-morning. `--teardown` removes only what carries the seed's own marker, and
prints how many roster athletes it skipped — that count must be 0.

It runs under a dedicated non-admin coach (`BSAMS_REHEARSAL_EMAIL`) and refuses to run as an
admin: every admin-owned athlete is a Boxing Science reference athlete for every coach in the
product, so rehearsing under the admin account would publish 38 invented boxers into everyone's
benchmarks.

**Tests** — `test_combine_engine.py` (the ranking maths, no mocks), `test_combine_public.py`
(the security file), `test_combine_router.py`, plus `tests/fake_supabase.py`, an in-memory
stand-in that lets the router tests assert on what ended up in the database rather than on mock
plumbing.

---

## Deployment

Run `backend/migrations/033_boxing_science_combine.sql`, then `034_combine_event_day.sql`, then
`035_combine_overall_score_basis.sql` in the Supabase SQL editor **before** deploying the code. The
reverse order breaks air bike saves, because the new code writes a `power_17s` column that would not
exist yet, and it takes the public board down: the board's lookup names `overall_score_basis` in an
explicit PostgREST projection, so against a database without that column every poll fails and every
screen sits on RECONNECTING until the migration runs.

All three are additive on live data: new tables, nullable columns, and one change to an
existing column that *loosens* a constraint (`power_14s` stops being required). Existing rows
all satisfy the new check. 034 adds `rfd_unit`, narrows `airbike_score_basis` to `w_per_kg`,
widens the attempt cap to 1–40, and locks `combine_upsert_event_metrics` down — Supabase grants
EXECUTE on every new function to `anon` and `authenticated`, and 033's `REVOKE ... FROM PUBLIC`
does not remove those role grants. 035 adds `overall_score_basis` ('z' | 'percentile', defaulting to 'z'), so every existing event keeps the scoring it had. Confirm the grants afterwards with:

```sql
SELECT grantee, privilege_type FROM information_schema.routine_privileges
 WHERE routine_name = 'combine_upsert_event_metrics';
```

---

## Decisions settled before the first event

1. **RFD units.** Selectable per event (`rfd_unit`). Stored canonically in N/s whatever the
   station types, so the registry, engine, promotion and norms never carry a unit; kg/s is
   converted at the API boundary and what was typed is kept alongside it.
2. **Landmine per side.** Both arms are thrown. The board ranks the best of either and shows
   `L` / `R`; the load-velocity profile splits into `… (Left)` / `… (Right)`, with the bare
   name kept only for legacy attempts logged without a side.
3. **Weight-category vocabulary.** The 20 England Boxing categories, strict. `57`, `57 kg`,
   `91+` and `91kg+` all normalise; anything else is a rejected row on import and a 422 on a
   participant edit.
4. **Ties.** Shared ranks render as `=2nd`, and equal values stack rather than overprinting on
   the dot panels. Tied rows are ordered by bib, so they hold one order across every poll.

## Still open

Tracked for after the event: a refresh-token cookie and `/auth/refresh` (a session currently ends
at JWT expiry and one Logout signs out every device), an event-scoped station credential instead of
shared admin login, guards on combine-tagged rows elsewhere in BSAMS (Testing edits, CSV upload
collisions), body mass on promoted rows, recording the landmine settings a norms snapshot was
built with so a stale band can be withheld rather than relying on the runbook, and showing
"not yet ranked" boxers on the Combine Score panel instead of dropping them.

---

## Notes for whoever picks this up

- `combine_engine.build_leaderboard` is pure — all I/O happens in the router. Keep it that way;
  it is why the ranking maths is testable without a Supabase mock.
- A **public** board build is three DB round-trips regardless of cohort size — token → event,
  roster, attempts — cached 5s per worker. A poll that changes nothing costs one round-trip (the
  token lookup, which resolves revoke and expiry and so is never cached) and answers 304. The
  attempt read pages in 1000-row chunks, so a very large event costs one more round-trip per
  extra 1000 attempts. BS norms cost zero extra queries because they are a snapshot on the
  event row.
- Handlers are sync `def`. An `async def` calling the sync Supabase client blocks the event
  loop (BUG-007) and this endpoint is polled.
- Any new router limiter must be registered in `tests/conftest.py::_reset_rate_limiters` or
  unrelated tests start bleeding 429s. The combine has two.
- The service worker now registers in production only. It serves `/_next/static/`
  stale-while-revalidate, which in development pins the browser to a previous build's
  JavaScript and makes code changes silently never appear.
