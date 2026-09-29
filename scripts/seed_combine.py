#!/usr/bin/env python3
"""Seed a rehearsal combine so the big screen can be proven before the real day.

Creates an event, ~38 fake boxers and plausible results across all six stations,
then prints the kiosk URL. Nothing here touches a real athlete: every record it
creates is tagged in `notes`, and --teardown removes only records carrying that
marker under the rehearsal owner.

The rehearsal runs under a dedicated non-admin coach (BSAMS_REHEARSAL_EMAIL), never
the admin account: admin-owned athletes are the Boxing Science benchmark pool, so 38
invented boxers would quietly move every coach's benchmarks. For the same reason the
bands on the rehearsal board come from a synthetic snapshot written onto the event.

Usage:
    BSAMS_REHEARSAL_EMAIL=coach@example.com python scripts/seed_combine.py
    python scripts/seed_combine.py --dry-run       # show what would be created
    python scripts/seed_combine.py --teardown      # remove it and the athletes it made
    python scripts/seed_combine.py --partial       # leave some stations incomplete
"""

import argparse
import os
import random
import secrets
import sys
from datetime import date, datetime, timedelta, timezone

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Dedicated coach account for rehearsals. Never the admin account — see module docstring.
REHEARSAL_EMAIL = os.environ.get("BSAMS_REHEARSAL_EMAIL", "")

SEED_MARKER = "bsams-rehearsal-combine"
EVENT_NAME = "Rehearsal Combine"

FIRST_NAMES = [
    "Jack", "Sam", "Ali", "Tyler", "Reece", "Kai", "Louie", "Zaid", "Finn", "Rhys",
    "Callum", "Owen", "Nathan", "Jude", "Marcus", "Devon", "Isaac", "Leo", "Amir",
    "Grace", "Maya", "Chloe", "Erin", "Nia", "Faye", "Ruby", "Isla", "Tara",
]
SURNAMES = [
    "Reid", "Okoro", "Hassan", "Doyle", "Whitfield", "Ashworth", "Boateng", "Kaur",
    "Nowak", "Mensah", "Byrne", "Sharpe", "Iqbal", "Rowley", "Fenton", "Coyle",
    "Ellis", "Marsh", "Nadeem", "Pryce",
]
CLUBS = ["Repton", "GB Boxing", "Steel City ABC", "Hatton Health", "Rotunda ABC"]
WEIGHT_CATEGORIES = ["51kg", "54kg", "57kg", "60kg", "63.5kg", "67kg", "71kg", "80kg"]
AGE_GROUPS = ["Junior", "Youth", "Elite"]

# Synthetic Boxing Science norms for the rehearsal board, as (mean, sd) per gender.
# The real snapshot is built from the admin pool by the console's "Refresh Boxing
# Science bands"; a rehearsal coach has no pool, so refreshing here would write an
# empty snapshot and take every band off the screen. n is above the engine's minimum
# of 20 so the bands actually render.
SYNTHETIC_NORMS = {
    # score_key: ((male mean, male sd), (female mean, female sd))
    "height_cm": ((38.0, 5.0), (31.5, 4.5)),
    "pogo_rsi": ((2.40, 0.35), (2.10, 0.30)),
    "grip_best_kg": ((48.0, 7.0), (35.0, 6.0)),
    "trunk_rotation_best_kg": ((74.0, 11.0), (57.0, 9.0)),
    "landmine_velocity_ms": ((4.00, 0.40), (3.40, 0.35)),
    "air_bike_power_7s_wkg": ((13.5, 1.6), (11.2, 1.4)),
}
NORM_N = {"male": 24, "female": 21}


def client():
    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_KEY (service_role) first.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def rehearsal_coach_id(db) -> str:
    """The non-admin coach that owns the rehearsal event and its boxers.

    Every athlete owned by an admin is a Boxing Science reference athlete for every
    coach in the product, so seeding under an admin would publish 38 invented boxers
    as benchmark data. Refuse rather than pollute the pool.
    """
    if not REHEARSAL_EMAIL:
        sys.exit(
            "Set BSAMS_REHEARSAL_EMAIL to a dedicated non-admin coach account. "
            "Seeding under an admin would add fake boxers to the Boxing Science pool."
        )
    result = (
        db.table("profiles")
        .select("id, email, role")
        .eq("email", REHEARSAL_EMAIL)
        .limit(1)
        .execute()
    )
    if not result.data:
        sys.exit(f"No profile found for {REHEARSAL_EMAIL}. Create the rehearsal coach first.")
    profile = result.data[0]
    if (profile.get("role") or "") == "admin":
        sys.exit(
            f"{REHEARSAL_EMAIL} is an admin account. Use a coach account: admin-owned "
            "athletes become Boxing Science benchmark data for every coach."
        )
    return profile["id"]


def synthetic_norms_snapshot() -> dict:
    """{score_key: {mean, sd, n, by_gender: {male: {...}, female: {...}}}}.

    Aggregates only — the same shape the public endpoint reads off the event row.
    """
    snapshot: dict = {}
    n_male, n_female = NORM_N["male"], NORM_N["female"]
    total = n_male + n_female
    for key, ((male_mean, male_sd), (female_mean, female_sd)) in SYNTHETIC_NORMS.items():
        snapshot[key] = {
            "mean": round((male_mean * n_male + female_mean * n_female) / total, 3),
            "sd": round((male_sd * n_male + female_sd * n_female) / total, 3),
            "n": total,
            "by_gender": {
                "male": {"mean": male_mean, "sd": male_sd, "n": n_male},
                "female": {"mean": female_mean, "sd": female_sd, "n": n_female},
            },
        }
    return snapshot


def make_boxers(count: int, rng: random.Random) -> list[dict]:
    """Plausible athletes — heavier boxers get more force, lighter ones more spring."""
    boxers = []
    for index in range(count):
        first = FIRST_NAMES[index % len(FIRST_NAMES)]
        surname = SURNAMES[(index * 7) % len(SURNAMES)]
        category = WEIGHT_CATEGORIES[index % len(WEIGHT_CATEGORIES)]
        mass = float(category.replace("kg", "")) + rng.uniform(-0.8, 0.8)
        boxers.append(
            {
                "first_name": first,
                "surname": f"{surname}",
                "gender": "female" if first in FIRST_NAMES[19:] else "male",
                "club": CLUBS[index % len(CLUBS)],
                "weight_category": category,
                "age_group": AGE_GROUPS[index % len(AGE_GROUPS)],
                "body_mass_kg": round(mass, 1),
                "bib": index + 1,
            }
        )
    return boxers


def station_attempts(boxer: dict, rng: random.Random, reference_load: float) -> list[tuple]:
    """(station, measures) pairs for one boxer. Heavier = stronger, lighter = springier."""
    mass = boxer["body_mass_kg"]
    spring = 1.0 + (65 - mass) * 0.006  # lighter boxers jump a little better
    strength = 1.0 + (mass - 65) * 0.008

    out: list[tuple] = []

    for _ in range(rng.randint(2, 3)):
        out.append(("cmj", {"height_cm": round(rng.gauss(38, 4.5) * spring, 1)}))

    for _ in range(rng.randint(1, 2)):
        contact = round(rng.gauss(195, 22))
        flight = round(rng.gauss(470, 45) * spring)
        out.append(("pogo", {"flight_time_ms": flight, "contact_time_ms": contact}))

    for load in sorted({reference_load, reference_load - 5, reference_load + 5}):
        if load <= 0:
            continue
        base = rng.gauss(4.0, 0.35) * strength - (load - reference_load) * 0.04
        for side in ("left", "right"):
            # The board ranks the best of either side, so throw both rather than
            # log one number twice — and exercise the per-side VBT profiles.
            hand = base if side == "right" else base * rng.uniform(0.90, 0.99)
            out.append(
                (
                    "landmine",
                    {
                        "load_kg": load,
                        "side": side,
                        "peak_velocity_ms": round(max(1.2, hand), 2),
                    },
                )
            )

    grip = rng.gauss(46, 6) * strength
    out.append(
        (
            "grip",
            {
                "left_kg": round(max(20, grip * rng.uniform(0.9, 1.0)), 1),
                "right_kg": round(max(20, grip * rng.uniform(0.95, 1.08)), 1),
            },
        )
    )

    rotation = rng.gauss(72, 11) * strength
    out.append(
        (
            "trunk_rotation",
            {
                "left_kg": round(max(25, rotation * rng.uniform(0.88, 1.0)), 1),
                "right_kg": round(max(25, rotation * rng.uniform(0.94, 1.1)), 1),
            },
        )
    )

    peak = rng.gauss(13.5, 1.6) * mass  # ~13.5 W/kg at 7s
    for sprint in (1, 2):
        decay = 1.0 if sprint == 1 else rng.uniform(0.86, 0.95)
        out.append(
            (
                "air_bike",
                {
                    "sprint_number": sprint,
                    "power_7s": round(peak * decay, 1),
                    "power_17s": round(peak * decay * rng.uniform(0.74, 0.82), 1),
                    "power_27s": round(peak * decay * rng.uniform(0.60, 0.70), 1),
                },
            )
        )

    return out


def teardown(db) -> None:
    """Remove the rehearsal event and only the athletes this script created.

    A real boxer added to the rehearsal roster by hand must survive teardown, so
    athletes are deleted by owner + seed marker, never by roster membership.
    """
    events = (
        db.table("combine_events")
        .select("id, notes, coach_id")
        .eq("event_name", EVENT_NAME)
        .execute()
    )
    rows = [e for e in (events.data or []) if SEED_MARKER in (e.get("notes") or "")]
    if not rows:
        print("Nothing to remove.")
        return

    for event in rows:
        participants = (
            db.table("combine_participants")
            .select("athlete_id")
            .eq("combine_event_id", event["id"])
            .execute()
        )
        athlete_ids = [str(p["athlete_id"]) for p in (participants.data or [])]

        seeded_ids: list[str] = []
        for start in range(0, len(athlete_ids), 100):
            chunk = athlete_ids[start : start + 100]
            owned = (
                db.table("athletes")
                .select("id")
                .eq("coach_id", event["coach_id"])
                .eq("notes", SEED_MARKER)
                .in_("id", chunk)
                .execute()
            )
            seeded_ids.extend(str(a["id"]) for a in (owned.data or []))

        # Cascades participants and attempts; promoted rows have their tag nulled.
        db.table("combine_events").delete().eq("id", event["id"]).execute()

        for start in range(0, len(seeded_ids), 100):
            chunk = seeded_ids[start : start + 100]
            (
                db.table("athletes")
                .delete()
                .eq("coach_id", event["coach_id"])
                .eq("notes", SEED_MARKER)
                .in_("id", chunk)
                .execute()
            )

        skipped = len(athlete_ids) - len(seeded_ids)
        print(
            f"Removed {EVENT_NAME} and {len(seeded_ids)} rehearsal athletes "
            f"({skipped} roster athletes were not seed-created and were left alone)."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=38, help="How many boxers to create")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--teardown", action="store_true")
    parser.add_argument(
        "--partial",
        action="store_true",
        help="Leave some stations incomplete, as the room would look mid-morning",
    )
    parser.add_argument("--seed", type=int, default=20260910, help="Random seed")
    args = parser.parse_args()

    db = client()

    if args.teardown:
        teardown(db)
        return

    rng = random.Random(args.seed)
    coach_id = rehearsal_coach_id(db)
    boxers = make_boxers(args.count, rng)
    reference_load = 20.0

    if args.dry_run:
        print(f"Would create '{EVENT_NAME}' with {len(boxers)} boxers, e.g.:")
        for boxer in boxers[:3]:
            print(f"  #{boxer['bib']:>2} {boxer['first_name']} {boxer['surname']} "
                  f"({boxer['weight_category']}, {boxer['body_mass_kg']} kg, {boxer['club']})")
        print(f"  ...and {len(boxers) - 3} more")
        return

    teardown(db)

    token = secrets.token_urlsafe(24)
    event = (
        db.table("combine_events")
        .insert(
            {
                "coach_id": coach_id,
                "event_name": EVENT_NAME,
                "event_date": str(date.today()),
                "venue": "Lab rehearsal",
                "status": "live",
                "share_token": token,
                "share_token_expires_at": (
                    datetime.now(timezone.utc) + timedelta(days=2)
                ).isoformat(),
                "public_display_consent_confirmed_at": datetime.now(timezone.utc).isoformat(),
                "landmine_reference_load_kg": reference_load,
                "min_stations_for_overall": 3,
                # Bands without the admin pool — the rehearsal coach has none.
                "bs_norms_snapshot": synthetic_norms_snapshot(),
                "bs_norms_updated_at": datetime.now(timezone.utc).isoformat(),
                "notes": SEED_MARKER,
            }
        )
        .execute()
    ).data[0]

    attempts_payload = []
    for boxer in boxers:
        athlete = (
            db.table("athletes")
            .insert(
                {
                    "coach_id": coach_id,
                    "name": f"{boxer['first_name']} {boxer['surname']}",
                    "first_name": boxer["first_name"],
                    "surname": boxer["surname"],
                    "gender": boxer["gender"],
                    "body_mass_kg": boxer["body_mass_kg"],
                    "status": "amateur",
                    "notes": SEED_MARKER,
                }
            )
            .execute()
        ).data[0]

        participant = (
            db.table("combine_participants")
            .insert(
                {
                    "combine_event_id": event["id"],
                    "athlete_id": athlete["id"],
                    "bib": boxer["bib"],
                    "club": boxer["club"],
                    "weight_category": boxer["weight_category"],
                    "age_group": boxer["age_group"],
                    "body_mass_kg": boxer["body_mass_kg"],
                }
            )
            .execute()
        ).data[0]

        pairs = station_attempts(boxer, rng, reference_load)
        if args.partial and rng.random() < 0.45:
            # Mid-morning: not everyone has been round every station yet.
            keep = {"cmj", "pogo", "grip"}
            pairs = [p for p in pairs if p[0] in keep]

        counters: dict[str, int] = {}
        for station, measures in pairs:
            counters[station] = counters.get(station, 0) + 1
            attempts_payload.append(
                {
                    "combine_event_id": event["id"],
                    "participant_id": participant["id"],
                    "station": station,
                    "attempt_number": counters[station],
                    "measures": measures,
                    "entered_by": coach_id,
                }
            )

    for start in range(0, len(attempts_payload), 500):
        db.table("combine_attempts").insert(attempts_payload[start : start + 500]).execute()

    print(f"Created '{EVENT_NAME}' with {len(boxers)} boxers and {len(attempts_payload)} attempts.")
    print()
    print(f"  Big screen:  /combine/live/{token}")
    print(f"  Console:     /combine/{event['id']}")
    print()
    print("Results are not promoted to athlete records yet — hit 'Re-sync results' on the")
    print("console to exercise that path too.")
    print("Remove everything with: python scripts/seed_combine.py --teardown")


if __name__ == "__main__":
    main()
