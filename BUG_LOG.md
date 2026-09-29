# Bug Log

Documented bugs, root causes, and fixes for BSAMS.

---

## BUG-001: Supabase service_role key required
**Date:** 2026-01-20
**Severity:** Critical
**Status:** Fixed

**Symptom:** Profile creation failures, empty consent queries, empty shared data views. Backend queries returned no results even with valid data in the database.

**Root Cause:** Backend was configured with Supabase **anon key** instead of **service_role key**. The anon key causes RLS to apply with `auth.uid() = NULL`, which blocks all server-side queries.

**Fix:** Changed `SUPABASE_KEY` environment variable to use the service_role (secret) key on Railway.

**Prevention:** Added to CLAUDE.md deployment section: "SUPABASE_KEY must be the **service_role (secret)** key (not anon)".

---

## BUG-002: Profile upsert overwrites admin role
**Date:** 2026-01-20
**Severity:** Critical
**Status:** Fixed

**Symptom:** Admin user's role was overwritten to "coach" after logging in, causing admin UI to disappear.

**Root Cause:** `_ensure_profile_exists()` used Supabase upsert, which overwrites all columns including `role`. When an admin logged in, their role was reset to the default "coach".

**Fix:** Changed from upsert to select+insert pattern: first SELECT to check if profile exists, then INSERT only if not found. This preserves existing role values.

**Prevention:** Rule added: "Never upsert profiles". All profile creation uses select+insert pattern.

---

## BUG-003: Frontend hardcodes role on login
**Date:** 2026-01-20
**Severity:** Medium
**Status:** Fixed

**Symptom:** Admin UI (shared data view, benchmark source toggle) not visible until page refresh after login.

**Root Cause:** `handleAuthResponse` in the frontend hardcoded `role="coach"` on login. The actual role was only fetched on page refresh via `/auth/me`.

**Fix:** Added explicit `/auth/me` call after login to fetch the actual role from the backend before setting user state.

---

## BUG-004: Boolean filters in Supabase Python
**Date:** 2026-01-22
**Severity:** Medium
**Status:** Fixed

**Symptom:** Shared data view showed empty results even when coaches had opted in to data sharing.

**Root Cause:** Supabase Python client's `.eq("data_sharing_enabled", True)` did not reliably filter boolean columns. The query returned empty results despite matching rows existing.

**Fix:** Changed approach to fetch all consent rows and filter in Python (`if consent["data_sharing_enabled"]`), bypassing the unreliable DB-level boolean filter.

**Prevention:** Rule added: "Safer to fetch all rows and filter in Python" for boolean columns in supabase-py.

---

## BUG-005: MetricSelector not refreshing after data changes
**Date:** 2026-01-21
**Severity:** Medium
**Status:** Fixed

**Symptom:** After adding the first events to a new athlete, the metric dropdown remained empty until page refresh.

**Root Cause:** MetricSelector's useEffect only triggered on `athleteId` change. Adding new events didn't change the athlete ID, so the dropdown didn't re-fetch available metrics.

**Fix:** Added `dataVersion` counter in testing/page.tsx, incremented by PerformanceTable's `onDataChanged` callback. Passed through DataViewControls to MetricSelector as a useEffect dependency.

---

## BUG-006: Metrics validation on Response schema
**Date:** 2026-01-24
**Severity:** Medium
**Status:** Fixed

**Symptom:** API returning 500 errors when retrieving events that contained legacy or non-standard metric keys.

**Root Cause:** `PerformanceEventResponse` schema was validating metric keys against the allowed list. Historical data in the database contained keys that were valid at time of insertion but not in the current allowed list.

**Fix:** Removed metrics validation from `PerformanceEventResponse`. Validation now only runs on `PerformanceEventCreate` and `PerformanceEventUpdate` schemas.

**Prevention:** Rule added: "Only validate metrics on input, not output".

---

## BUG-007: async def blocks event loop with sync Supabase
**Date:** 2026-01-24
**Severity:** High
**Status:** Fixed

**Symptom:** Under concurrent requests, the backend became unresponsive. Requests queued behind long-running database operations.

**Root Cause:** Router endpoints were defined with `async def`, but the Supabase Python client makes synchronous HTTP calls. In FastAPI, `async def` endpoints run on the main event loop — synchronous I/O calls block it, preventing other requests from being processed.

**Fix:** Changed all non-auth router endpoints from `async def` to `def`. FastAPI runs `def` endpoints in a threadpool, allowing concurrent handling. Auth endpoints kept `async` for rate limiter compatibility.

---

## BUG-008: Admin N+1 query on shared athletes
**Date:** 2026-01-24
**Severity:** Low
**Status:** Fixed

**Symptom:** Shared athletes endpoint slow with many opted-in coaches.

**Root Cause:** Original implementation looped per-coach with individual `.eq()` queries to fetch athletes, creating an N+1 query pattern.

**Fix:** Refactored to collect all opted-in coach IDs first, then use a single `.in_()` query to fetch all athletes at once.

---

## BUG-009: Radar Z-scores not updating on reference group change
**Date:** 2026-01-22
**Severity:** Low
**Status:** Fixed

**Symptom:** Changing the reference group dropdown didn't update the Z-score values displayed on the radar chart.

**Root Cause:** ZScoreRadar component didn't include `referenceGroup` in its data-fetching useEffect dependencies.

**Fix:** Added `referenceGroup` and `benchmarkSource` as dependencies to the radar's data fetch effect.

---

## BUG-010: Trailing slash redirect loop
**Date:** 2026-01-05
**Severity:** High
**Status:** Fixed

**Symptom:** API calls from Vercel frontend to Railway backend resulted in infinite redirects (301 loop).

**Root Cause:** Vercel strips trailing slashes by default, but FastAPI expects them. The redirect responses bounced between the two services.

**Fix:** Added `skipTrailingSlashRedirect: true` + regex rewrite in `next.config.js` to preserve trailing slashes in API proxy calls.

---

## BUG-011: Duplicate athlete creation on CSV upload
**Date:** 2026-01-08
**Severity:** Medium
**Status:** Fixed

**Symptom:** Uploading the same CSV file multiple times created duplicate athlete records.

**Root Cause:** Auto-create athlete logic did a case-sensitive exact match. Variations in whitespace or capitalization created duplicates.

**Fix:** Added duplicate detection with normalized name matching. CSV upload now skips events with same athlete_id + event_date combination.

---

## BUG-012: Training load not updating after changes
**Date:** 2026-01-31
**Severity:** Medium
**Status:** Fixed

**Symptom:** After adding a training session or wellness entry, the load chart and readiness indicator didn't reflect the new data.

**Root Cause:** Load analysis data was fetched once on mount but not re-fetched when sessions or wellness entries were created/updated/deleted.

**Fix:** Added callback-driven data refresh — session and wellness mutations trigger load analysis re-fetch.

---

## BUG-015: Login rejects users with legacy passwords after security hardening
**Date:** 2026-02-11
**Severity:** Critical
**Status:** Fixed

**Symptom:** Users with simple pre-existing passwords could not log in after the security hardening deployment. Login returned 422 validation error.

**Root Cause:** Password strength validation (`@field_validator`) was added to `AuthRequest`, which is shared by both the signup and login endpoints. Login should only authenticate against Supabase, not enforce password policy on existing credentials.

**Fix:** Split into separate schemas: `AuthRequest` (login, no validation) and `SignupRequest` (signup only, enforces 8+ chars, uppercase, digit). Added regression test `test_login_accepts_weak_password`.

**Prevention:** Password strength rules should only apply at account creation, never at login. Validation schemas for input (create) vs authentication (verify) must be separate.

## BUG-017: Conditioning save returns Internal Server Error in production
**Date:** 2026-02-16
**Severity:** Critical
**Status:** Fixed

**Symptom:** Saving a conditioning exercise in production returned "Internal Server Error" (500). Worked in local development.

**Root Cause (Phase 1):** Migrations 023 (`rest_between_reps` JSONB) and 024 (`rep_intensity_values` JSONB) hadn't been applied to Supabase yet. Backend used `model_dump(exclude_unset=False)` which included these new fields as `None` in every INSERT. Supabase rejected the unknown columns, causing an unhandled exception.

**Fix (Phase 1):** Filter `None` values from INSERT dicts before sending to Supabase: `{k: v for k, v in data.items() if v is not None}`. Applied to 4 locations: `exercises.py` (create), `exercise_library.py` (create), `session_templates.py` (_save_template_exercises + apply_template).

**Root Cause (Phase 2):** After deploying the None-filter fix, the error persisted because migrations 022 (`rep_durations`), 023, and 024 were never applied to production Supabase. The global exception handler returned an opaque "Internal server error" hiding the real PostgREST error: `PGRST204: Could not find the 'rep_durations' column`.

**Fix (Phase 2):** Added try/except with logging around all Supabase INSERT calls in exercises.py, exercise_library.py, and session_templates.py. This surfaced the actual error, revealing the missing columns. Applied migrations 022-024 to production Supabase.

**Prevention:** (1) Always filter `None` values from INSERT dicts when optional JSONB columns are involved. (2) Wrap Supabase INSERT calls in try/except with logging to surface DB errors instead of relying on the opaque global exception handler. (3) Verify all migrations are applied to production after deploying code that depends on new columns.

---

## BUG-016: Training load crashes on assigned sessions with null RPE/duration
**Date:** 2026-02-13
**Severity:** High
**Status:** Fixed

**Symptom:** "Failed to load training analysis" error on training page even when sessions with sRPE data exist. Training load chart does not render.

**Root Cause:** `TrainingLoadEngine.calculate_daily_loads()` used `session.get("srpe", 0)` which returns `None` (not `0`) when the key exists with a `None` value (assigned sessions). The fallback then tried `rpe * duration` where both are also `None`, causing `TypeError: unsupported operand type(s) for *: 'NoneType' and 'NoneType'`.

**Fix:** Changed to `session.get("srpe") or 0` and `session.get("rpe") or 0` / `session.get("duration_minutes") or 0` to coerce `None` to `0`. Added regression test `test_assigned_session_null_rpe_duration_srpe`.

**Prevention:** When using `.get()` on dicts from Supabase, remember that NULL columns are returned as `None` values (key present), not missing keys. Use `or 0` instead of default parameter for numeric fallbacks.

---

## BUG-018: Login on the shared service-role client leaks RLS to every request
**Date:** 2026-09-16
**Severity:** Critical
**Status:** Fixed

**Symptom:** After any user logged in, unrelated requests on the same uvicorn worker began returning "not found" for rows that exist. On a combine event day this would make station saves fail with "Combine event not found" and 404 the public board, for everyone, until a restart.

**Root Cause:** `login`, `signup` and `signup_athlete` called `sign_in_with_password` / `sign_up` on the shared service-role singleton. The installed `supabase` 2.27.3 swaps that client's `Authorization` header to the returned user token (library `client.py:334-346`), so every later query on that worker ran as the last person to log in, under their row-level security, instead of as service_role.

**Fix:** Authenticate on a throwaway `create_client(...)` with `auto_refresh_token=False, persist_session=False` — the pattern `change_password` already used. The singleton stays for DB work such as `_ensure_profile_exists`. Regression test asserts the singleton's `auth.sign_in_with_password` / `auth.sign_up` are never called and its `Authorization` header still holds the service key.

**Prevention:** Never call an `auth.*` method on the shared client. The Supabase Python client is stateful — signing in mutates the client, not just the returned session.

---

## BUG-019: Combine promotion overwrote same-day manual records
**Date:** 2026-09-16
**Severity:** Critical
**Status:** Fixed

**Symptom:** Saving or voiding a combine air bike or landmine attempt destroyed an athlete's manually entered air bike test or VBT profile dated the same day.

**Root Cause:** `_promote_air_bike` and `_promote_landmine` looked up and deleted rows matching athlete + date only. Any row on the event date was treated as the combine's own, including records the coach had entered by hand.

**Fix:** Every lookup and delete in `combine_promotion.py` is scoped to `.eq("combine_event_id", event_id)`. A `23505` conflict is caught inside each helper, logged as a warning and skipped, so a landmine conflict cannot also skip air bike. `fake_supabase.py` gained the real unique keys so the tests can see a conflict.

**Prevention:** A promoted row is only ever the one carrying this event's tag. Never identify it by athlete + date, which is also the shape of manual data.

---

## BUG-020: Boxing Science bands compared every boxer to one pooled norm
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** A strong 16-year-old girl could read DEVELOPING, in red, on the public wall.

**Root Cause:** `bs_norms_snapshot` held one pooled mean and SD per key, built from a mostly-male admin pool, and every boxer was scored against it.

**Fix:** `norms_from_rows` emits `by_gender` alongside the pooled aggregate. The engine uses the boxer's own gender entry; a missing gender, a missing entry, or n < 20 yields no band, and the pooled norm is never used as a fallback. Pre-fix snapshots have no `by_gender`, so bands stay off until an admin refreshes. Gender never enters any payload. `CombineEventResponse.bs_norms_coverage` reports n per key per gender — counts only, never means or SDs.

**Prevention:** A benchmark band is a comparison; the reference group has to match the athlete. Withholding a band is always safer than showing a wrong one on a public screen.

---

## BUG-021: Hidden clubs were still filterable on the public board
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** With club names hidden, `?club=Repton` still narrowed the board, so the hidden club membership of named minors could be enumerated one club at a time.

**Root Cause:** `public_leaderboard` passed the `club` query parameter into the filters regardless of `show_club`, and `build_leaderboard` applied it.

**Fix:** `public_leaderboard` drops `club` before building `filters` and `filter_key` — so it cannot key the ETag or the cache either — and `build_leaderboard` applies the same guard when `public=True`. The filter chip list withholds clubs too.

**Prevention:** Hiding a field means hiding everything derived from it: the row, the filter, the chip list and the cache key.

---

## BUG-022: Turning the board off never cleared an open TV
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** Pressing "Turn off" revoked the link, but a TV already showing the board kept displaying minors' names indefinitely.

**Root Cause:** The kiosk poller kept its last good payload on any non-200, including the 404 that revoke, rotate and expiry all return. Keeping the last good board is correct for a blip — but a 404 is not a blip.

**Fix:** `useCombinePolling` counts consecutive 404s in a ref, resetting on any 200 or 304. After three it clears `data`, `lastUpdated` and the ETag so "Board unavailable" shows, and keeps polling at the slowest backoff so a restored link recovers by itself. Network errors, 429 and 5xx still keep the last good board, and an abort caused by a newer request is not a failure.

**Prevention:** "Keep the last good value" needs an exception for the response that means the resource is deliberately gone.

---

## BUG-023: Unpaginated reads silently stopped at 1000 rows
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** With a full roster the board could silently drop results, and the roster import's duplicate preview could miss existing athletes.

**Root Cause:** PostgREST caps unpaginated selects at the project's max rows (1000 by default). With both landmine sides, 40 boxers reach roughly 1,080 attempts, and an admin can own more than 1000 athletes.

**Fix:** `fetch_all_rows(build_query, page_size=1000)` in `combine_norms.py` builds a fresh query per page, `.order("id").range(...)`, stopping on a short page. Used by `_load_attempts`, the norms pool inside `_chunked_in`, and the bulk import's athlete name lookup. Tested with a `FakeSupabase(max_rows=1000)` and 2,500 attempts.

**Prevention:** Any select that can exceed 1000 rows must paginate. The cap is silent — a short result looks like the whole result.

---

## BUG-024: A retried attempt save created a duplicate
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** A station iPad that lost the response and tapped SAVE again logged the attempt twice. Two workers inserting at once returned a generic 500.

**Root Cause:** The entry screen minted a new `client_attempt_id` on every SAVE, so the server had nothing to recognise a retry by. The insert also had no handling for a colliding attempt number.

**Fix:** The id is kept in state and minted only when the payload actually changes (keypad input, load, side, sprint chip, or a boxer change), and survives a failed or timed-out save. `submit_attempt` re-selects and returns the original row on a `23505` with a known `client_attempt_id`; otherwise it recomputes the attempt number, re-checks the cap and retries up to 3 times. Station calls carry a 15 s timeout reported as "Timed out — check the connection and tap SAVE again".

**Prevention:** An idempotency key identifies the payload, not the tap. Minting one per attempt to send defeats the point.

---

## BUG-025: A weigh-in edit rewrote the athlete's name
**Date:** 2026-09-16
**Severity:** Medium
**Status:** Fixed

**Symptom:** Entering body mass for "Ana Maria Lopez" changed her first name to "Ana" and surname to "Maria Lopez".

**Root Cause:** The participant modal seeded its name fields by splitting the display name at the first space when the record had no stored parts, then PATCHed the athlete with every field on save — writing the guess back.

**Fix:** `ParticipantResponse` carries `first_name` / `surname` from the athlete record, so the form is seeded with the stored parts. `toAthleteUpdate` compares against what seeded the form and returns null when nothing changed, so an untouched field is never sent. Cleared text fields are sent as explicit `null`, since `JSON.stringify` drops `undefined` and the endpoint patches with `exclude_unset`.

**Prevention:** Never PATCH a field the user did not edit, especially one the form only inferred.

---

## BUG-026: The offline page never recovered by itself
**Date:** 2026-09-16
**Severity:** Medium
**Status:** Fixed

**Symptom:** A TV or iPad that reloaded during a Wi-Fi drop sat on the offline page until someone walked over and pressed Try Again. The copy also claimed "nothing has been lost", which is not true of a half-typed attempt.

**Root Cause:** The page was static, with a manual reload button and reassuring copy.

**Fix:** An inline script reloads on the `online` event and on a `HEAD` probe of `location.href` every ~10 s, covering captive portals where `online` never fires. The copy now says anything typed but not yet saved was not recorded and to check what was logged. `CACHE_NAME` bumped so installed devices pick the new page up.

**Prevention:** A kiosk page has nobody standing next to it. Anything that can recover on its own should.

---

## BUG-027: Air bike `absolute_w` scored watts against a W/kg norm
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** An event configured with `airbike_score_basis = 'absolute_w'` showed every boxer in the ELITE band, with raw watts labelled "W/kg" on the public screen.

**Root Cause:** The basis changed what was ranked and displayed, but the Boxing Science norm for the air bike is built in W/kg. An 800 W value scored against a ~12 W/kg norm is off the top of the scale for everyone.

**Fix:** `AirBikeBasis` is `Literal["w_per_kg"]`; migration 034 rewrites existing rows and narrows the CHECK. Publishing watts was never safe on the public board anyway — watts beside W/kg makes body mass derivable.

**Prevention:** A score and its benchmark must be in the same unit. If a setting can change the unit, the norm has to change with it — or the setting should not exist.

---

## BUG-028: Every station save rewrote all four stations' keys
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** Two iPads saving for the same boxer could roll a just-logged best back. Landmine and air bike saves left a `test_type`-only shell row in `performance_events`, and every CMJ save rebuilt that boxer's `vbt_sets` and `air_bike_sprints`.

**Root Cause:** `submit_attempt` promoted the whole participant: it rebuilt all four JSONB stations' keys from its own read of the attempts and re-sent them, along with the landmine and air bike targets, on every save. Another worker's write between that read and the merge was overwritten with stale values.

**Fix:** The hot path is station-scoped. `submit_attempt` passes `station` down; JSONB stations call the RPC with `build_event_metrics(bests, stations=(station,))`, landmine calls only `_promote_landmine`, air bike only `_promote_air_bike`. Voids, corrections and sync keep the full rebuild — clearing a station whose every attempt has been voided is the one thing that needs it.

**Prevention:** A concurrent merge must send only the keys it owns. Re-sending everything it happens to know turns a read-modify-write race into lost data.

---

## BUG-029: A day's results could be cascaded away
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** Removing a boxer from the roster, or merging their athlete record into another, silently deleted their logged attempts. Re-syncing an event deleted a withdrawn boxer's CMJ, pogo, grip and trunk row while leaving their landmine and bike records behind.

**Root Cause:** `delete_participant` and `merge_athletes` had no combine guard, and `combine_attempts` cascades from the participant. `_promote_participant` passed the participant row through untouched, and `best_per_participant` skips a withdrawn one — so the rebuild wrote nothing for the JSONB stations while the side tables kept what they had.

**Fix:** `delete_participant` returns 409 with "This boxer has logged attempts — mark them withdrawn instead" when any attempt exists, voided included. `merge_athletes` returns 409 before any write when the athlete being merged away is on a combine roster. `_promote_participant` clears `withdrawn_at` on the row it passes to `best_per_participant`, so a withdrawal hides a boxer from the board without erasing what they did.

**Prevention:** Withdrawn is a display state, not a deletion. Anything that can cascade a day of irreplaceable measurements needs a refusal, not a confirm dialog.

---

## BUG-030: Changing the event date orphaned the results and the link
**Date:** 2026-09-16
**Severity:** Medium
**Status:** Fixed

**Symptom:** Moving an event's date after results were logged left the promoted rows on the old date — `performance_events` is unique on (athlete, date, combine event) — and the share link kept expiring two days after the *original* date.

**Root Cause:** `update_event` wrote `event_date` straight through and never recomputed `share_token_expires_at`.

**Fix:** A changed `event_date` returns 409 — "Results are already logged for this event — the date can no longer change" — once the event has attempts. Before that it is free, and the expiry is recomputed with `_default_expiry`. The console shows "Link valid until …", amber once expired.

**Prevention:** A column other rows are keyed on stops being editable the moment those rows exist.

---

## BUG-031: A single failed `/auth/me` signed a station iPad out
**Date:** 2026-09-16
**Severity:** Medium
**Status:** Fixed

**Symptom:** One dropped frame on gym Wi-Fi, or one backend 5xx, sent a station to `/login` mid-event. Signing back in then landed on `/training`, not the station.

**Root Cause:** `AuthProvider` treated any `/auth/me` failure as "not signed in" and cleared the user. The combine pages redirected to a bare `/login` with no return path.

**Fix:** Only a 401 clears the user. Network errors and 5xx retry on a 10/20/30s schedule, capped at three attempts, then show Reconnecting / Retry, and the station page renders that state instead of `null`. The combine pages redirect to `/login?next=<path>`; the login page reads `next` once on mount, accepts only a path starting with a single `/`, and uses it for both its render-time and post-login redirects.

**Prevention:** "No answer" is not "no session". Only the server saying 401 means signed out.

---

## BUG-032: The rehearsal seed deleted real athletes and polluted the benchmark pool
**Date:** 2026-09-16
**Severity:** Critical
**Status:** Fixed

**Symptom:** `seed_combine.py --teardown` hard-deleted every athlete on the rehearsal roster, seed-created or not — and teardown ran at the start of every seed. The seed also created 38 invented boxers under the admin account.

**Root Cause:** Teardown resolved athletes through the roster rather than through the seed's own marker. The script defaulted to the admin account, and every admin-owned athlete is a Boxing Science reference athlete for every coach in the product.

**Fix:** Teardown selects and deletes only `.eq("coach_id", owner).eq("notes", SEED_MARKER)` and prints how many roster athletes it skipped. The event and its athletes belong to a dedicated coach from `BSAMS_REHEARSAL_EMAIL`, and the script exits if that profile is an admin. The seed writes its own synthetic `bs_norms_snapshot` so bands still render without touching the real pool.

**Prevention:** A destructive script identifies what it made by its own marker, never by association. Rehearsal data never lands where production data is read from.

---

## BUG-033: The station entry screen fought the operator
**Date:** 2026-09-16
**Severity:** Medium
**Status:** Fixed

**Symptom:** On pogo and air bike, SAVE turned amber on nearly every attempt after the first boxer. One stray tap on an attempt chip voided a result with no undo. Saving jumped to the next boxer, hiding one with two jumps left. A boxer with no body mass gave no explanation, and a server-side 422 arrived as `[object Object]`.

**Root Cause:** The outlier guard compared whatever number was typed against the best logged value at that station — flight time in ms against an RSI, watts against W/kg. Void fired on first tap. A save reloaded the roster and re-picked the first to-do boxer. `fetchApi` passed FastAPI's `detail` array through unflattened, and fields carried no `min`/`max`.

**Fix:** `guardValue(station, values, entry)` compares like with like — live RSI on pogo, W/kg on the bike (skipped without mass), the better side on grip and trunk, landmine only at the reference load. Void arms on the first tap ("Tap again to remove") and disarms after 4s or on any other touch. Saving keeps the boxer; "Next boxer →" moves on deliberately. Fields carry the `min`/`max` from `schemas/combine.py` and SAVE stays disabled with a hint while a value is out of range. `fetchApi` flattens 422 detail arrays. Air bike shows an amber no-body-mass warning with SAVE still enabled, defaults the sprint number from the loaded attempts, and labels chips `S1`/`S2`.

**Prevention:** A guard that fires on ordinary work gets ignored, which is worse than no guard. The unit being compared has to be the unit being ranked.

---

## BUG-034: Kiosk URL parameters were unvalidated and a panel baseline was invisible
**Date:** 2026-09-16
**Severity:** Low
**Status:** Fixed

**Symptom:** A typo in `?panel=` left the TV on nothing at all, and `?rotate=1` flickered through panels unreadably. The dot panels' baseline rules never appeared.

**Root Cause:** The panel parameter was used as given and the rotate value was parsed without bounds. The baselines used `bg-white/8`, an opacity Tailwind 3.4 does not generate a class for, so no CSS was emitted.

**Fix:** `normalisePanelParam` matches `KIOSK_PANELS` case-insensitively and falls back to rotating; `clampRotateSeconds` clamps to 5-300s; `useCombineRotation` gates its interval on `isPinned`. The baselines use `bg-white/[0.08]`.

**Prevention:** Parameters typed onto a television by hand degrade to the default rather than to a blank screen. Arbitrary Tailwind opacities need bracket syntax — an unsupported one fails silently.

---

## BUG-035: Deleting an athlete still cascaded away their combine results
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** `POST /athletes/merge` refused to merge an athlete who was on a combine roster, but `DELETE /athletes/{id}` and `DELETE /athletes/` (delete-all) deleted the same athlete with a 204/200 and no warning. On the day, an admin told "remove them from the roster first" by the merge guard would simply delete the duplicate instead.

**Root Cause:** `combine_participants.athlete_id` and `combine_attempts.participant_id` are both `ON DELETE CASCADE`, so deleting an athlete takes their roster row and every attempt logged against them at every station. Only the merge path checked the roster. Attempts are the log of record (decision 112) — re-sync rebuilds promoted rows from them, so once they are gone the day's results cannot be recovered. The `log_deletion` summary counted only `performance_events`, so nothing recorded what was lost.

**Fix:** `_combine_roster_rows()` (chunked 500 at a time, because a coach can hold hundreds of athletes and `.in_()` travels in the query string) is now the single roster check used by all three paths. `delete_athlete` returns 409 naming the event and pointing at withdrawal — "remove them from the roster" is a dead end, since `delete_participant` itself refuses once attempts exist. `delete_all_data` returns 409 naming the event and the order that unblocks a genuine wipe (delete the combine event first). Both audit entries now carry `combine_participants_count`.

**Prevention:** A cascade guard belongs on every path that reaches the cascade, not on the one where the case was first noticed. A 409 that blocks an operation has to name the way out.

---

## BUG-036: A landmine ladder could orphan the reference load, emptying the Punch panel
**Date:** 2026-09-16
**Severity:** High
**Status:** Fixed

**Symptom:** Typing the real ladder ("12, 17, 22, 27") into Event settings while the reference load stayed at its default 20 kg was accepted with no error. Every landmine throw then saved, showed on the station chips and promoted a VBT profile — and the Punch panel on the public board stayed empty all day, with the Combine Score averaged over five stations instead of six. `PATCH` also accepted an empty ladder, 50 loads, or negative loads.

**Root Cause:** `combine_engine.score_attempt` drops any landmine throw further than `landmine_reference_tolerance_kg` from `landmine_reference_load_kg`. Nothing checked that the reference load was reachable from the ladder: `CombineEventBase` had no such validator, `CombineEventUpdate.landmine_loads_kg` was a bare `Optional[List[float]]` with no validation at all, and `update_event` wrote the merged payload unchecked. The console validated the ladder client-side but never compared it with the reference load.

**Fix:** `reference_load_error()` in `schemas/combine.py` is the one statement of the rule. `CombineEventCreate` gains a `model_validator` using it (on the create model, not `CombineEventBase`, because `CombineEventResponse` inherits the base and an already-misconfigured row must stay readable — decision 22). `CombineEventUpdate` gains the create schema's `landmine_loads_kg` validator. `update_event` re-checks the merged settings whenever a PATCH touches one of the three landmine fields, returning 422 naming the nearest ladder load. `lib/combineLandmine.ts` mirrors the rule for the console (a standing warning, a refusal when a stranded reference load is typed, and moving the reference onto the nearest new load when the ladder changes, since neither field can be changed first on its own) and for the station's "Ref" badge, which gated on exact equality and so vanished on a legitimately within-tolerance configuration.

**Prevention:** Two settings that only make sense together are validated together, on the merged result of a partial update. A badge that can be absent for an innocent reason is not a signal.
