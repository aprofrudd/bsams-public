#!/usr/bin/env python3
"""Seed gold-standard conditioning session templates.

Admin-owned, idempotent (skips duplicates), supports --dry-run.

Usage:
    python scripts/seed_conditioning_templates.py
    python scripts/seed_conditioning_templates.py --dry-run
"""

import argparse
import os
import sys

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Admin account — the Boxing Science admin user that owns gold-standard content
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")

# Gold-standard conditioning templates
# These are placeholders to refine with real programming
TEMPLATES = [
    {
        "template_name": "Foundation Assault Bike Intervals",
        "training_type": "Conditioning",
        "description": "Low-intensity assault bike intervals for aerobic base building. "
                       "Suitable for early off-season or return from injury.",
        "template_category": "conditioning",
        "tier": "foundation",
        "notes": "Target: 40-60% of peak power. Focus on steady effort and recovery.",
        "exercises": [
            {
                "exercise_name": "Assault Bike Intervals",
                "exercise_category": "Conditioning",
                "order_index": 1,
                "sets": 6,
                "reps": 1,
                "duration_seconds": 30,
                "rest_seconds": 90,
                "intensity_type": "power_watts",
            },
        ],
    },
    {
        "template_name": "Intermediate Assault Bike Intervals",
        "training_type": "Conditioning",
        "description": "Moderate-intensity assault bike intervals for building anaerobic capacity. "
                       "Mid-season work capacity development.",
        "template_category": "conditioning",
        "tier": "intermediate",
        "notes": "Target: 60-80% of peak power. Push through discomfort.",
        "exercises": [
            {
                "exercise_name": "Assault Bike Intervals",
                "exercise_category": "Conditioning",
                "order_index": 1,
                "sets": 8,
                "reps": 1,
                "duration_seconds": 20,
                "rest_seconds": 60,
                "intensity_type": "power_watts",
            },
        ],
    },
    {
        "template_name": "Advanced Assault Bike Sprint Repeats",
        "training_type": "Conditioning",
        "description": "High-intensity sprint repeats for peak anaerobic power. "
                       "Pre-fight or competition peaking phase.",
        "template_category": "conditioning",
        "tier": "advanced",
        "notes": "Target: 80-100% of peak power. Maximal effort each sprint.",
        "exercises": [
            {
                "exercise_name": "Assault Bike Sprints",
                "exercise_category": "Conditioning",
                "order_index": 1,
                "sets": 10,
                "reps": 1,
                "duration_seconds": 10,
                "rest_seconds": 50,
                "intensity_type": "power_watts",
            },
        ],
    },
    {
        "template_name": "Foundation Running Intervals",
        "training_type": "Conditioning",
        "description": "Steady-state running intervals for aerobic development. "
                       "Good for athletes building a running base.",
        "template_category": "conditioning",
        "tier": "foundation",
        "notes": "Target: 8-12 km/h. Maintain consistent pace throughout.",
        "exercises": [
            {
                "exercise_name": "Treadmill Intervals",
                "exercise_category": "Conditioning",
                "order_index": 1,
                "sets": 5,
                "reps": 1,
                "duration_seconds": 60,
                "rest_seconds": 120,
                "intensity_type": "speed_kmh",
            },
        ],
    },
    {
        "template_name": "Intermediate Mixed Conditioning",
        "training_type": "Conditioning",
        "description": "Mixed-modality conditioning combining bike and bodyweight work. "
                       "Develops work capacity across movement patterns.",
        "template_category": "conditioning",
        "tier": "intermediate",
        "notes": "Target: RPE 6-8. Circuit format with minimal rest between exercises.",
        "exercises": [
            {
                "exercise_name": "Assault Bike",
                "exercise_category": "Conditioning",
                "order_index": 1,
                "sets": 4,
                "reps": 1,
                "duration_seconds": 30,
                "rest_seconds": 30,
                "intensity_type": "power_watts",
            },
            {
                "exercise_name": "Battle Ropes",
                "exercise_category": "Conditioning",
                "order_index": 2,
                "sets": 4,
                "reps": 1,
                "duration_seconds": 30,
                "rest_seconds": 30,
                "intensity_type": "rpe",
            },
            {
                "exercise_name": "Box Jumps",
                "exercise_category": "Conditioning",
                "order_index": 3,
                "sets": 4,
                "reps": 8,
                "rest_seconds": 60,
                "intensity_type": "rpe",
            },
        ],
    },
]


def get_admin_id(client) -> str:
    """Find the admin user ID by email."""
    resp = (
        client.table("profiles")
        .select("id, role")
        .eq("email", ADMIN_EMAIL)
        .limit(1)
        .execute()
    )
    if not resp.data:
        print(f"ERROR: Admin profile not found for {ADMIN_EMAIL}")
        sys.exit(1)
    profile = resp.data[0]
    if profile.get("role") != "admin":
        print(f"WARNING: {ADMIN_EMAIL} has role '{profile.get('role')}', expected 'admin'")
    return profile["id"]


def seed_templates(client, admin_id: str, dry_run: bool = False):
    """Seed conditioning templates idempotently."""
    created = 0
    skipped = 0

    for tmpl in TEMPLATES:
        name = tmpl["template_name"]

        # Check if already exists
        existing = (
            client.table("session_templates")
            .select("id")
            .eq("coach_id", admin_id)
            .eq("template_name", name)
            .limit(1)
            .execute()
        )
        if existing.data:
            print(f"  SKIP: '{name}' (already exists)")
            skipped += 1
            continue

        if dry_run:
            print(f"  DRY-RUN: Would create '{name}' with {len(tmpl['exercises'])} exercises")
            created += 1
            continue

        # Insert template
        row = {
            "coach_id": admin_id,
            "template_name": tmpl["template_name"],
            "training_type": tmpl["training_type"],
            "description": tmpl.get("description"),
            "notes": tmpl.get("notes"),
            "template_category": tmpl.get("template_category"),
            "tier": tmpl.get("tier"),
        }
        resp = client.table("session_templates").insert(row).execute()
        if not resp.data:
            print(f"  ERROR: Failed to create '{name}'")
            continue

        template_id = resp.data[0]["id"]

        # Insert exercises
        if tmpl.get("exercises"):
            ex_rows = []
            for ex in tmpl["exercises"]:
                ex_row = {
                    "template_id": template_id,
                    **{k: v for k, v in ex.items() if v is not None},
                }
                ex_rows.append(ex_row)
            client.table("template_exercises").insert(ex_rows).execute()

        print(f"  CREATED: '{name}' ({len(tmpl.get('exercises', []))} exercises)")
        created += 1

    return created, skipped


def main():
    parser = argparse.ArgumentParser(description="Seed gold-standard conditioning templates")
    parser.add_argument("--dry-run", action="store_true", help="Preview without making changes")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set")
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Finding admin account...")
    admin_id = get_admin_id(client)
    print(f"  Admin ID: {admin_id}")

    print(f"\nSeeding conditioning templates {'(DRY RUN)' if args.dry_run else ''}...")
    created, skipped = seed_templates(client, admin_id, dry_run=args.dry_run)

    print(f"\nDone: {created} created, {skipped} skipped")


if __name__ == "__main__":
    main()
