"""Program marketplace API router."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.access_control import require_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503, raise_on_duplicate
from app.schemas.program import (
    InstalledTemplateResponse,
    ProgramPackageCreate,
    ProgramPackageDetailResponse,
    ProgramPackageResponse,
    ProgramPackageUpdate,
    ProgramTemplateCreate,
    ProgramTemplateResponse,
    ProgramTemplateUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/programs", tags=["programs"])


# ── Installed templates (must be before /{program_id} to avoid UUID parse) ──


@router.get(
    "/installed-templates",
    response_model=List[InstalledTemplateResponse],
)
def list_installed_templates(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List all templates from installed programs for the current user."""
    client = get_client_or_503()

    # Get user's installations
    install_resp = (
        client.table("program_installations")
        .select("program_id")
        .eq("user_id", str(current_user.id))
        .execute()
    )

    if not install_resp.data:
        return []

    program_ids = [row["program_id"] for row in install_resp.data]

    # Load program names
    programs_resp = (
        client.table("program_packages")
        .select("id, program_name")
        .in_("id", program_ids)
        .execute()
    )
    program_names = {p["id"]: p["program_name"] for p in (programs_resp.data or [])}

    # Load all templates from installed programs
    templates_resp = (
        client.table("program_templates")
        .select("*")
        .in_("program_id", program_ids)
        .order("order_index")
        .execute()
    )

    results = []
    for t in templates_resp.data or []:
        results.append({
            **t,
            "program_name": program_names.get(t["program_id"], "Unknown"),
        })

    return results


# ── Program listing & detail ──


@router.get(
    "/",
    response_model=List[ProgramPackageResponse],
)
def list_programs(
    category: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List published programs (admins see all)."""
    client = get_client_or_503()

    query = client.table("program_packages").select("*")

    if current_user.role != "admin":
        query = query.eq("is_published", True)

    if category:
        query = query.eq("category", category)

    query = query.order("program_name")
    response = query.execute()
    programs = response.data or []

    # Get template counts
    program_ids = [p["id"] for p in programs]
    template_counts: dict = {}
    if program_ids:
        for pid in program_ids:
            count_resp = (
                client.table("program_templates")
                .select("id", count="exact")
                .eq("program_id", pid)
                .execute()
            )
            template_counts[pid] = count_resp.count if count_resp.count is not None else len(count_resp.data or [])

    # Get user's installations
    install_resp = (
        client.table("program_installations")
        .select("program_id")
        .eq("user_id", str(current_user.id))
        .execute()
    )
    installed_ids = {row["program_id"] for row in (install_resp.data or [])}

    # Enrich
    for p in programs:
        p["template_count"] = template_counts.get(p["id"], 0)
        p["is_installed"] = p["id"] in installed_ids

    return programs


@router.get(
    "/{program_id}",
    response_model=ProgramPackageDetailResponse,
)
def get_program(
    program_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a program with its templates."""
    client = get_client_or_503()

    response = (
        client.table("program_packages")
        .select("*")
        .eq("id", str(program_id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    program = response.data[0]

    # Non-admins can only see published programs
    if not program["is_published"] and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    # Load templates
    templates_resp = (
        client.table("program_templates")
        .select("*")
        .eq("program_id", str(program_id))
        .order("order_index")
        .execute()
    )
    program["templates"] = templates_resp.data or []

    # Template count and install status
    program["template_count"] = len(program["templates"])

    install_resp = (
        client.table("program_installations")
        .select("id")
        .eq("user_id", str(current_user.id))
        .eq("program_id", str(program_id))
        .execute()
    )
    program["is_installed"] = bool(install_resp.data)

    return program


# ── Installation ──


@router.post(
    "/{program_id}/install",
    status_code=status.HTTP_201_CREATED,
)
def install_program(
    program_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Install a published program for the current user."""
    client = get_client_or_503()

    # Verify program exists and is published
    prog_resp = (
        client.table("program_packages")
        .select("id, is_published")
        .eq("id", str(program_id))
        .execute()
    )
    if not prog_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )
    if not prog_resp.data[0]["is_published"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    # Insert installation
    try:
        client.table("program_installations").insert({
            "user_id": str(current_user.id),
            "program_id": str(program_id),
        }).execute()
    except Exception as e:
        raise_on_duplicate(e, "Program already installed")

    return {"detail": "Program installed"}


@router.delete(
    "/{program_id}/install",
    status_code=status.HTTP_204_NO_CONTENT,
)
def uninstall_program(
    program_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Uninstall a program for the current user."""
    client = get_client_or_503()

    # Check installation exists
    install_resp = (
        client.table("program_installations")
        .select("id")
        .eq("user_id", str(current_user.id))
        .eq("program_id", str(program_id))
        .execute()
    )
    if not install_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not installed",
        )

    client.table("program_installations").delete().eq(
        "user_id", str(current_user.id)
    ).eq(
        "program_id", str(program_id)
    ).execute()

    return None


# ── Admin: Program CRUD ──


@router.post(
    "/",
    response_model=ProgramPackageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_program(
    program: ProgramPackageCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new program package (admin only)."""
    require_admin(current_user)
    client = get_client_or_503()

    data = {
        "created_by": str(current_user.id),
        "program_name": program.program_name,
        "description": program.description,
        "category": program.category,
        "cover_image_url": program.cover_image_url,
        "is_published": program.is_published,
    }
    # Filter None values
    data = {k: v for k, v in data.items() if v is not None}

    try:
        response = client.table("program_packages").insert(data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A program with this name already exists")

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create program",
        )

    result = response.data[0]
    result["template_count"] = 0
    result["is_installed"] = False
    return result


@router.patch(
    "/{program_id}",
    response_model=ProgramPackageResponse,
)
def update_program(
    program_id: UUID,
    program: ProgramPackageUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a program package (admin only)."""
    require_admin(current_user)
    client = get_client_or_503()

    # Verify exists
    existing = (
        client.table("program_packages")
        .select("id")
        .eq("id", str(program_id))
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    update_data = program.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        response = (
            client.table("program_packages")
            .update(update_data)
            .eq("id", str(program_id))
            .execute()
        )
    except Exception as e:
        raise_on_duplicate(e, "A program with this name already exists")

    result = response.data[0]

    # Enrich with template count
    count_resp = (
        client.table("program_templates")
        .select("id", count="exact")
        .eq("program_id", str(program_id))
        .execute()
    )
    result["template_count"] = count_resp.count if count_resp.count is not None else len(count_resp.data or [])

    # Check install status
    install_resp = (
        client.table("program_installations")
        .select("id")
        .eq("user_id", str(current_user.id))
        .eq("program_id", str(program_id))
        .execute()
    )
    result["is_installed"] = bool(install_resp.data)

    return result


@router.delete(
    "/{program_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_program(
    program_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a program package (admin only). Cascades to templates and installations."""
    require_admin(current_user)
    client = get_client_or_503()

    # Verify exists
    existing = (
        client.table("program_packages")
        .select("id")
        .eq("id", str(program_id))
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    client.table("program_packages").delete().eq("id", str(program_id)).execute()

    return None


# ── Admin: Program Template CRUD ──


@router.post(
    "/{program_id}/templates",
    response_model=ProgramTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_program_template(
    program_id: UUID,
    template: ProgramTemplateCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Add a template to a program (admin only)."""
    require_admin(current_user)
    client = get_client_or_503()

    # Verify program exists
    prog_resp = (
        client.table("program_packages")
        .select("id")
        .eq("id", str(program_id))
        .execute()
    )
    if not prog_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program not found",
        )

    # Serialize exercises JSONB
    exercises_json = [ex.model_dump(exclude_unset=False) for ex in template.exercises]
    exercises_json = [{k: v for k, v in ex.items() if v is not None} for ex in exercises_json]

    data = {
        "program_id": str(program_id),
        "template_name": template.template_name,
        "training_type": template.training_type,
        "order_index": template.order_index,
        "notes": template.notes,
        "exercises": exercises_json,
    }

    try:
        response = client.table("program_templates").insert(data).execute()
    except Exception as e:
        raise_on_duplicate(e, "A template with this name already exists in this program")

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create program template",
        )

    return response.data[0]


@router.patch(
    "/{program_id}/templates/{template_id}",
    response_model=ProgramTemplateResponse,
)
def update_program_template(
    program_id: UUID,
    template_id: UUID,
    template: ProgramTemplateUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a program template (admin only)."""
    require_admin(current_user)
    client = get_client_or_503()

    # Verify template belongs to program
    existing = (
        client.table("program_templates")
        .select("id")
        .eq("id", str(template_id))
        .eq("program_id", str(program_id))
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program template not found",
        )

    update_data = template.model_dump(exclude_unset=True)

    # Serialize exercises if provided
    if "exercises" in update_data and update_data["exercises"] is not None:
        exercises_json = [ex.model_dump(exclude_unset=False) for ex in template.exercises]
        exercises_json = [{k: v for k, v in ex.items() if v is not None} for ex in exercises_json]
        update_data["exercises"] = exercises_json

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    try:
        response = (
            client.table("program_templates")
            .update(update_data)
            .eq("id", str(template_id))
            .eq("program_id", str(program_id))
            .execute()
        )
    except Exception as e:
        raise_on_duplicate(e, "A template with this name already exists in this program")

    return response.data[0]


@router.delete(
    "/{program_id}/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_program_template(
    program_id: UUID,
    template_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a program template (admin only)."""
    require_admin(current_user)
    client = get_client_or_503()

    # Verify template belongs to program
    existing = (
        client.table("program_templates")
        .select("id")
        .eq("id", str(template_id))
        .eq("program_id", str(program_id))
        .execute()
    )
    if not existing.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program template not found",
        )

    client.table("program_templates").delete().eq("id", str(template_id)).execute()

    return None


# ── Apply program template to session ──


@router.post(
    "/templates/{template_id}/apply",
    status_code=status.HTTP_201_CREATED,
)
def apply_program_template(
    template_id: UUID,
    session_id: UUID = Query(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Apply a program template to a training session, creating exercise prescriptions.

    For each template exercise with `sets: N`, creates N exercise_prescription rows
    with set_number 1..N.
    User must have the program installed.
    """
    client = get_client_or_503()

    # Load template and its program
    template_resp = (
        client.table("program_templates")
        .select("*")
        .eq("id", str(template_id))
        .execute()
    )
    if not template_resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Program template not found",
        )

    template_data = template_resp.data[0]
    program_id = template_data["program_id"]

    # Verify user has program installed
    install_resp = (
        client.table("program_installations")
        .select("id")
        .eq("user_id", str(current_user.id))
        .eq("program_id", program_id)
        .execute()
    )
    if not install_resp.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must install the program before applying its templates",
        )

    # Verify session exists and user has access
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
    athlete_id = session["athlete_id"]

    if current_user.role == "athlete":
        if not verify_athlete_access(client, UUID(athlete_id), current_user):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training session not found",
            )
    else:
        # Coach/admin: verify athlete belongs to them
        athlete_resp = (
            client.table("athletes")
            .select("id")
            .eq("id", athlete_id)
            .eq("coach_id", str(current_user.id))
            .execute()
        )
        if not athlete_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Training session not found",
            )

    # Read exercises from JSONB
    exercises = template_data.get("exercises") or []

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
                "rep_intensity_values": ex.get("rep_intensity_values"),
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
                    "duration_seconds": ex.get("duration_seconds"),
                    "rest_seconds": ex.get("rest_seconds"),
                    "intensity_type": ex.get("intensity_type"),
                    "intensity_value": ex.get("intensity_value"),
                }
                prescriptions.append({k: v for k, v in prescription.items() if v is not None})
                set_counter += 1

    if prescriptions:
        try:
            response = client.table("exercise_prescriptions").insert(prescriptions).execute()
        except Exception as e:
            logger.error("Apply program template insert failed. Data: %s\nError: %s", prescriptions, str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to apply program template: {str(e)}",
            )
        return response.data

    return []
