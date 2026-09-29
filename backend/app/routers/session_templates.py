"""Session templates API router."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

logger = logging.getLogger(__name__)

from app.core.access_control import get_athlete_coach_id, require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.session_template import (
    SessionTemplateCreate,
    SessionTemplateResponse,
    SessionTemplateUpdate,
)

router = APIRouter(prefix="/session-templates", tags=["session-templates"])


def _verify_template_ownership(client, template_id: UUID, coach_id: UUID):
    """Verify template belongs to coach. Returns template data or raises 404."""
    response = (
        client.table("session_templates")
        .select("*")
        .eq("id", str(template_id))
        .eq("coach_id", str(coach_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return response.data[0]


def _load_template_exercises(client, template_id: str):
    """Load exercises for a template."""
    response = (
        client.table("template_exercises")
        .select("*")
        .eq("template_id", template_id)
        .order("order_index")
        .execute()
    )
    return response.data


def _save_template_exercises(client, template_id: str, exercises):
    """Save exercises for a template (replace-all semantics)."""
    # Delete existing exercises
    client.table("template_exercises").delete().eq("template_id", template_id).execute()

    # Insert new exercises
    if exercises:
        rows = []
        for ex in exercises:
            row = {
                "template_id": template_id,
                **{k: v for k, v in ex.model_dump(exclude_unset=False).items() if v is not None},
            }
            rows.append(row)
        try:
            client.table("template_exercises").insert(rows).execute()
        except Exception as e:
            logger.error("Template exercises insert failed. Data: %s\nError: %s", rows, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save template exercises: {str(e)}",
            )



@router.post(
    "/",
    response_model=SessionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    template: SessionTemplateCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new session template with optional exercises."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    data = {
        k: v
        for k, v in {
            "coach_id": str(current_user.id),
            "template_name": template.template_name,
            "training_type": template.training_type,
            "description": template.description,
            "notes": template.notes,
            "template_category": template.template_category,
            "tier": template.tier,
        }.items()
        if v is not None
    }

    try:
        response = client.table("session_templates").insert(data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A template with this name already exists")

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create template",
        )

    template_data = response.data[0]
    template_id = template_data["id"]

    # Save exercises if provided
    if template.exercises:
        _save_template_exercises(client, template_id, template.exercises)

    # Load exercises to return
    template_data["exercises"] = _load_template_exercises(client, template_id)

    return template_data


@router.get(
    "/",
    response_model=List[SessionTemplateResponse],
)
def list_templates(
    category: Optional[str] = Query(None, description="Filter by template_category (e.g. 'conditioning')"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List templates. When category='conditioning', returns gold-standard templates (admin-owned)."""
    client = get_client_or_503()

    if category == "conditioning":
        # Gold-standard conditioning templates: skip coach_id filter
        query = (
            client.table("session_templates")
            .select("*")
            .eq("template_category", "conditioning")
            .order("template_name")
        )
    else:
        if current_user.role == "athlete":
            coach_id = get_athlete_coach_id(client, current_user)
        else:
            require_coach_or_admin(current_user)
            coach_id = str(current_user.id)

        query = (
            client.table("session_templates")
            .select("*")
            .eq("coach_id", coach_id)
            .order("template_name")
        )

    response = query.execute()

    templates = response.data
    for t in templates:
        t["exercises"] = _load_template_exercises(client, t["id"])

    return templates


@router.get(
    "/{template_id}",
    response_model=SessionTemplateResponse,
)
def get_template(
    template_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single template with exercises."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    template_data = _verify_template_ownership(client, template_id, current_user.id)
    template_data["exercises"] = _load_template_exercises(client, str(template_id))
    return template_data


@router.patch(
    "/{template_id}",
    response_model=SessionTemplateResponse,
)
def update_template(
    template_id: UUID,
    template: SessionTemplateUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a session template. If exercises provided, replaces all exercises."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    _verify_template_ownership(client, template_id, current_user.id)

    update_data = template.model_dump(exclude_unset=True, exclude={"exercises"})

    if update_data:
        try:
            client.table("session_templates").update(update_data).eq(
                "id", str(template_id)
            ).execute()
        except Exception as e:
            raise_on_duplicate(e, "A template with this name already exists")

    # Replace exercises if provided
    if template.exercises is not None:
        _save_template_exercises(client, str(template_id), template.exercises)

    # Reload and return
    updated = (
        client.table("session_templates")
        .select("*")
        .eq("id", str(template_id))
        .execute()
    )
    result = updated.data[0]
    result["exercises"] = _load_template_exercises(client, str(template_id))
    return result


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_template(
    template_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a session template (cascades to exercises)."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    _verify_template_ownership(client, template_id, current_user.id)

    client.table("session_templates").delete().eq("id", str(template_id)).execute()

    return None


@router.post(
    "/{template_id}/apply",
    status_code=status.HTTP_201_CREATED,
)
def apply_template(
    template_id: UUID,
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Apply a template to a training session, creating exercise prescriptions.

    For each template exercise with `sets: N`, creates N exercise_prescription rows
    with set_number 1..N.
    """
    client = get_client_or_503()

    # Load template by ID (gold-standard templates are admin-owned)
    template_resp = (
        client.table("session_templates")
        .select("*")
        .eq("id", str(template_id))
        .execute()
    )
    if not template_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    template = template_resp.data[0]
    is_conditioning = template.get("template_category") == "conditioning"

    if current_user.role == "athlete":
        # Athlete: verify own session, look up coach, verify template belongs to coach
        session_resp = (
            client.table("training_sessions")
            .select("athlete_id, status, created_by")
            .eq("id", str(session_id))
            .execute()
        )
        if not session_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training session not found",
            )
        session = session_resp.data[0]
        if not verify_athlete_access(client, UUID(session["athlete_id"]), current_user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training session not found",
            )
        # Must be athlete's own session
        is_own = session.get("status") is None and session.get("created_by") == str(current_user.id)
        if not is_own:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Athletes can only apply templates to their own sessions",
            )
        if not is_conditioning:
            coach_id = get_athlete_coach_id(client, current_user)
            if template["coach_id"] != coach_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found",
                )
        athlete_id_for_targets = session["athlete_id"]
    else:
        require_coach_or_admin(current_user)
        if not is_conditioning:
            if template["coach_id"] != str(current_user.id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template not found",
                )

        # Verify session belongs to coach's athlete
        session_resp = (
            client.table("training_sessions")
            .select("athlete_id")
            .eq("id", str(session_id))
            .execute()
        )
        if not session_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training session not found",
            )
        athlete_id = session_resp.data[0]["athlete_id"]
        athlete_resp = (
            client.table("athletes")
            .select("id")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )
        if not athlete_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training session not found",
            )
        athlete_id_for_targets = athlete_id

    # Load template exercises
    exercises = _load_template_exercises(client, str(template_id))

    # Separate circuit vs non-circuit exercises
    circuit_exs = [ex for ex in exercises if ex.get("exercise_category") == "Circuit"]
    non_circuit_exs = [ex for ex in exercises if ex.get("exercise_category") != "Circuit"]

    # Create exercise prescriptions with set expansion
    prescriptions = []

    # Non-circuit: standard per-exercise set expansion
    for ex in non_circuit_exs:
        num_sets = ex.get("sets", 1) or 1
        for set_num in range(1, num_sets + 1):
            prescription = {
                "session_id": str(session_id),
                "exercise_name": ex["exercise_name"],
                "exercise_category": ex.get("exercise_category"),
                "set_number": set_num,
                "reps": ex.get("reps"),
                "weight_kg": ex.get("weight_kg"),
                "tempo": ex.get("tempo"),
                "rest_seconds": ex.get("rest_seconds"),
                "duration_seconds": ex.get("duration_seconds"),
                "distance_meters": ex.get("distance_meters"),
                "intensity_type": ex.get("intensity_type"),
                "intensity_value": ex.get("intensity_value"),
                "rest_between_reps_seconds": ex.get("rest_between_reps_seconds"),
                "rep_durations": ex.get("rep_durations"),
                "rest_between_reps": ex.get("rest_between_reps"),
                "rep_intensity_values": ex.get("rep_intensity_values"),
                "notes": ex.get("notes"),
            }
            prescriptions.append({k: v for k, v in prescription.items() if v is not None})

    # Circuit: interleaved expansion across rounds
    if circuit_exs:
        num_rounds = (circuit_exs[0].get("sets", 1) or 1)
        set_counter = (max((p["set_number"] for p in prescriptions), default=0)) + 1
        for _round in range(num_rounds):
            for i, ex in enumerate(circuit_exs):
                prescription = {
                    "session_id": str(session_id),
                    "exercise_name": ex["exercise_name"],
                    "exercise_category": "Circuit",
                    "set_number": set_counter,
                    "reps": ex.get("reps"),
                    "duration_seconds": ex.get("duration_seconds"),
                    "rest_seconds": ex.get("rest_seconds"),
                    "intensity_type": ex.get("intensity_type"),
                    "intensity_value": ex.get("intensity_value"),
                    "notes": ex.get("notes"),
                }
                prescriptions.append({k: v for k, v in prescription.items() if v is not None})
                set_counter += 1

    # Resolve tier-based intensity targets for conditioning templates
    tier = template.get("tier")
    if is_conditioning and tier and prescriptions:
        from app.services.conditioning_engine import resolve_target_intensity

        # Cache resolved targets per intensity_type to avoid redundant DB queries
        target_cache: dict[str, tuple] = {}
        for p in prescriptions:
            intensity_type = p.get("intensity_type")
            if not intensity_type:
                continue
            if intensity_type not in target_cache:
                target_cache[intensity_type] = resolve_target_intensity(
                    client, athlete_id_for_targets, tier, intensity_type
                )
            min_val, max_val, _source = target_cache[intensity_type]
            if min_val is not None:
                p["intensity_min"] = min_val
            if max_val is not None:
                p["intensity_max"] = max_val

    if prescriptions:
        try:
            response = client.table("exercise_prescriptions").insert(prescriptions).execute()
        except Exception as e:
            logger.error("Apply template insert failed. Data: %s\nError: %s", prescriptions, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to apply template: {str(e)}",
            )
        return response.data

    return []


@router.get(
    "/{template_id}/preview-targets",
)
def preview_template_targets(
    template_id: UUID,
    athlete_id: UUID = Query(..., description="Athlete to resolve targets for"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Preview resolved intensity targets for a conditioning template + athlete.

    Uses the conditioning engine to resolve tier-based intensity ranges
    per exercise based on the athlete's metabolic/air bike data.
    """
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    # Verify template exists (gold-standard templates are admin-owned, so skip coach_id check
    # if template_category is 'conditioning')
    template_resp = (
        client.table("session_templates")
        .select("*")
        .eq("id", str(template_id))
        .execute()
    )
    if not template_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    template = template_resp.data[0]

    # Gold-standard templates accessible by any coach; own templates require ownership
    if template.get("template_category") != "conditioning":
        if template["coach_id"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found",
            )

    # Verify athlete access
    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    tier = template.get("tier")
    exercises = _load_template_exercises(client, str(template_id))

    from app.services.conditioning_engine import resolve_target_intensity

    results = []
    for ex in exercises:
        intensity_type = ex.get("intensity_type")
        if intensity_type and tier:
            min_val, max_val, source = resolve_target_intensity(
                client, str(athlete_id), tier, intensity_type
            )
        else:
            min_val, max_val, source = None, None, "no_tier"

        results.append({
            "exercise_name": ex["exercise_name"],
            "intensity_type": intensity_type,
            "intensity_min": min_val,
            "intensity_max": max_val,
            "source": source,
        })

    return {
        "template_id": str(template_id),
        "athlete_id": str(athlete_id),
        "tier": tier,
        "exercises": results,
    }
