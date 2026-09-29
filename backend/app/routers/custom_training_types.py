"""Custom training types API router."""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.access_control import require_coach_or_admin
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.custom_training_type import (
    CustomTrainingTypeCreate,
    CustomTrainingTypeResponse,
    TrainingTypeItem,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["training-types"])

SYSTEM_DEFAULTS = ["Strength", "Mobility", "Conditioning", "Circuit"]


def _resolve_coach_id(client, current_user: AuthenticatedUser) -> UUID:
    """Resolve the coach_id for the current user.

    For coaches/admins, returns their own ID.
    For athletes, looks up their coach_id from the athletes table.
    """
    if current_user.role in ("coach", "admin"):
        return current_user.id

    # Athlete: look up coach_id via athletes table
    response = (
        client.table("athletes")
        .select("coach_id")
        .eq("user_id", str(current_user.id))
        .limit(1)
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found",
        )
    return UUID(response.data[0]["coach_id"])


@router.get(
    "/types/",
    response_model=List[TrainingTypeItem],
)
def list_training_types(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List system defaults and coach's custom training types.

    For athletes, resolves their coach_id from the athletes table.
    """
    client = get_client_or_503()

    coach_id = _resolve_coach_id(client, current_user)

    # System defaults
    items: List[TrainingTypeItem] = [
        TrainingTypeItem(type_name=name, is_system=True)
        for name in SYSTEM_DEFAULTS
    ]

    # Coach's custom types
    response = (
        client.table("custom_training_types")
        .select("*")
        .eq("coach_id", str(coach_id))
        .order("display_order")
        .execute()
    )

    for row in response.data:
        items.append(
            TrainingTypeItem(
                type_name=row["type_name"],
                is_system=False,
                id=row["id"],
            )
        )

    return items


@router.post(
    "/types/",
    response_model=CustomTrainingTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_training_type(
    payload: CustomTrainingTypeCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a custom training type. Coach/admin only."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # Reject duplicates of system defaults (case-insensitive)
    if payload.type_name.lower() in [s.lower() for s in SYSTEM_DEFAULTS]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{payload.type_name}' is a system default and cannot be created as a custom type",
        )

    data = {
        "coach_id": str(current_user.id),
        "type_name": payload.type_name,
    }

    try:
        response = client.table("custom_training_types").insert(data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A custom training type with this name already exists")

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create training type",
        )

    return response.data[0]


@router.delete(
    "/types/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_training_type(
    type_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a custom training type. Coach/admin only.

    Sessions keep their stored training_type string (no FK).
    """
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # Verify ownership
    existing = (
        client.table("custom_training_types")
        .select("*")
        .eq("id", str(type_id))
        .eq("coach_id", str(current_user.id))
        .execute()
    )

    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Training type not found",
        )

    client.table("custom_training_types").delete().eq("id", str(type_id)).execute()

    return None
