"""Admin data pool service for Boxing Science reference groups."""

from typing import List, Set


def get_admin_athlete_ids(client) -> List[str]:
    """
    Get all athlete IDs belonging to admin users.

    Queries the profiles table for users with role='admin',
    then returns all athlete IDs owned by those admin users.
    """
    # Find all admin user IDs
    admin_profiles = (
        client.table("profiles")
        .select("id")
        .eq("role", "admin")
        .execute()
    )

    if not admin_profiles.data:
        return []

    admin_user_ids = [p["id"] for p in admin_profiles.data]

    # Get all athletes belonging to admin users
    all_athlete_ids = []
    for admin_id in admin_user_ids:
        athletes = (
            client.table("athletes")
            .select("id")
            .eq("coach_id", admin_id)
            .execute()
        )
        all_athlete_ids.extend(a["id"] for a in athletes.data)

    return all_athlete_ids


def get_admin_athletes(client) -> list:
    """
    Get all athletes (with gender) belonging to admin users.

    Returns list of dicts with 'id' and 'gender' keys.
    """
    admin_profiles = (
        client.table("profiles")
        .select("id")
        .eq("role", "admin")
        .execute()
    )

    if not admin_profiles.data:
        return []

    admin_user_ids = [p["id"] for p in admin_profiles.data]

    all_athletes = []
    for admin_id in admin_user_ids:
        athletes = (
            client.table("athletes")
            .select("id, gender")
            .eq("coach_id", admin_id)
            .execute()
        )
        all_athletes.extend(athletes.data)

    return all_athletes


def _get_admin_ids(client) -> Set[str]:
    """Get set of admin user IDs."""
    admin_profiles = (
        client.table("profiles")
        .select("id")
        .eq("role", "admin")
        .execute()
    )
    return {p["id"] for p in (admin_profiles.data or [])}


def get_opted_in_athletes(client) -> list:
    """
    Get all athletes (with gender) belonging to opted-in coaches.

    Queries coach_consents, filters data_sharing_enabled in Python,
    excludes admin accounts, then batch-queries athletes.
    Returns list of dicts with 'id' and 'gender' keys.
    """
    # Get all consents and filter in Python (boolean filter unreliable in supabase-py)
    consents = (
        client.table("coach_consents")
        .select("coach_id, data_sharing_enabled")
        .execute()
    )
    opted_in = [
        c for c in (consents.data or [])
        if c.get("data_sharing_enabled") is True
    ]
    if not opted_in:
        return []

    # Exclude admin users
    admin_ids = _get_admin_ids(client)
    opted_in_coach_ids = [
        c["coach_id"] for c in opted_in
        if c["coach_id"] not in admin_ids
    ]
    if not opted_in_coach_ids:
        return []

    # Batch query athletes
    athletes_result = (
        client.table("athletes")
        .select("id, gender")
        .in_("coach_id", opted_in_coach_ids)
        .execute()
    )
    return athletes_result.data or []
