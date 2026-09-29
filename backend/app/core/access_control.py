"""Centralized access control for role-based authorization."""

from uuid import UUID

from fastapi import HTTPException, status

from app.core.security import AuthenticatedUser


def verify_athlete_access(client, athlete_id: UUID, current_user: AuthenticatedUser) -> bool:
    """
    Check if the current user can access data for the given athlete.
    - Coach/Admin: athlete must have coach_id matching current_user.id
    - Athlete: athlete must have user_id matching current_user.id
    """
    if current_user.role in ("coach", "admin"):
        response = (
            client.table("athletes")
            .select("id")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )
    elif current_user.role == "athlete":
        response = (
            client.table("athletes")
            .select("id")
            .eq("id", str(athlete_id))
            .eq("user_id", str(current_user.id))
            .execute()
        )
    else:
        return False
    return bool(response.data)


def require_coach_or_admin(current_user: AuthenticatedUser) -> None:
    """Raise 403 if the user is not a coach or admin. Guards mutation endpoints."""
    if current_user.role not in ("coach", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches and admins can perform this action",
        )


def require_admin(current_user: AuthenticatedUser) -> None:
    """Raise 403 if the user is not an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform this action",
        )


def get_athlete_coach_id(client, current_user: AuthenticatedUser) -> str:
    """For an athlete user, look up their coach_id via athletes.user_id. Raises 404 if not linked."""
    response = (
        client.table("athletes")
        .select("coach_id")
        .eq("user_id", str(current_user.id))
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found",
        )
    return response.data[0]["coach_id"]
