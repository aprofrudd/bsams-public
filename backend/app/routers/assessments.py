"""Movement assessment API router."""

import logging
import time
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

logger = logging.getLogger(__name__)

from app.core.access_control import require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.assessment import (
    AssessmentPhotoResponse,
    MovementAssessmentCreate,
    MovementAssessmentListItem,
    MovementAssessmentResponse,
    MovementAssessmentUpdate,
    VALID_ASSESSMENT_TYPES,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])

STORAGE_BUCKET = "assessment-photos"
SIGNED_URL_EXPIRY = 3600  # 1 hour


def _verify_assessment_ownership(client, assessment_id: UUID, current_user: AuthenticatedUser) -> dict | None:
    """Verify assessment exists and belongs to a user-accessible athlete. Returns assessment data or None."""
    response = (
        client.table("movement_assessments")
        .select("*, athletes!inner(coach_id, user_id)")
        .eq("id", str(assessment_id))
        .execute()
    )
    if not response.data:
        return None
    assessment = response.data[0]
    athlete_data = assessment.get("athletes", {})
    if current_user.role in ("coach", "admin"):
        if str(athlete_data.get("coach_id")) != str(current_user.id):
            return None
    elif current_user.role == "athlete":
        if str(athlete_data.get("user_id")) != str(current_user.id):
            return None
    else:
        return None
    assessment.pop("athletes", None)
    return assessment


def _get_photos_for_assessment(client, assessment_id: str) -> list[dict]:
    """Fetch photos for an assessment and generate signed URLs."""
    response = (
        client.table("assessment_photos")
        .select("*")
        .eq("assessment_id", assessment_id)
        .order("created_at")
        .execute()
    )
    photos = response.data or []
    for photo in photos:
        try:
            signed = client.storage.from_(STORAGE_BUCKET).create_signed_url(
                photo["storage_path"], SIGNED_URL_EXPIRY
            )
            photo["photo_url"] = signed.get("signedURL") or signed.get("signedUrl")
        except Exception:
            photo["photo_url"] = None
    return photos


@router.post(
    "/",
    response_model=MovementAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    assessment: MovementAssessmentCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a new movement assessment."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    if assessment.assessment_type not in VALID_ASSESSMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment type. Must be one of: {VALID_ASSESSMENT_TYPES}",
        )

    if not verify_athlete_access(client, assessment.athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    data = {
        "athlete_id": str(assessment.athlete_id),
        "assessment_date": assessment.assessment_date.isoformat(),
        "assessment_type": assessment.assessment_type,
        "findings": assessment.findings,
        "notes": assessment.notes,
        "summary": assessment.summary,
    }

    try:
        response = client.table("movement_assessments").insert(data).execute()
    except Exception as e:
        error_msg = str(e)
        if "unique" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Assessment already exists for this athlete, date, and type",
            )
        raise

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create assessment",
        )

    row = response.data[0]
    return MovementAssessmentResponse(
        id=row["id"],
        athlete_id=row["athlete_id"],
        assessment_date=row["assessment_date"],
        assessment_type=row["assessment_type"],
        findings=row["findings"],
        notes=row.get("notes"),
        summary=row.get("summary"),
        photos=[],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.get(
    "/athlete/{athlete_id}",
    response_model=List[MovementAssessmentListItem],
)
def list_assessments(
    athlete_id: UUID,
    assessment_type: Optional[str] = Query(None, description="Filter by assessment type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List movement assessments for an athlete."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    query = (
        client.table("movement_assessments")
        .select("*")
        .eq("athlete_id", str(athlete_id))
    )

    if assessment_type:
        query = query.eq("assessment_type", assessment_type)

    response = query.order("assessment_date", desc=True).range(skip, skip + limit - 1).execute()
    assessments = response.data or []

    # Get photo counts in a single query
    assessment_ids = [a["id"] for a in assessments]
    photo_counts: dict[str, int] = {}
    if assessment_ids:
        photos_response = (
            client.table("assessment_photos")
            .select("assessment_id")
            .in_("assessment_id", assessment_ids)
            .execute()
        )
        for p in photos_response.data or []:
            aid = p["assessment_id"]
            photo_counts[aid] = photo_counts.get(aid, 0) + 1

    result = []
    for a in assessments:
        result.append(
            MovementAssessmentListItem(
                id=a["id"],
                athlete_id=a["athlete_id"],
                assessment_date=a["assessment_date"],
                assessment_type=a["assessment_type"],
                findings=a["findings"],
                notes=a.get("notes"),
                summary=a.get("summary"),
                photo_count=photo_counts.get(a["id"], 0),
                created_at=a["created_at"],
                updated_at=a["updated_at"],
            )
        )

    return result


@router.get(
    "/{assessment_id}",
    response_model=MovementAssessmentResponse,
)
def get_assessment(
    assessment_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get a single movement assessment with photos."""
    client = get_client_or_503()

    assessment = _verify_assessment_ownership(client, assessment_id, current_user)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    photos = _get_photos_for_assessment(client, str(assessment_id))

    return MovementAssessmentResponse(
        id=assessment["id"],
        athlete_id=assessment["athlete_id"],
        assessment_date=assessment["assessment_date"],
        assessment_type=assessment["assessment_type"],
        findings=assessment["findings"],
        notes=assessment.get("notes"),
        summary=assessment.get("summary"),
        photos=[AssessmentPhotoResponse(**p) for p in photos],
        created_at=assessment["created_at"],
        updated_at=assessment["updated_at"],
    )


@router.patch(
    "/{assessment_id}",
    response_model=MovementAssessmentResponse,
)
def update_assessment(
    assessment_id: UUID,
    update: MovementAssessmentUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update a movement assessment."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    assessment = _verify_assessment_ownership(client, assessment_id, current_user)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    update_data = update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    if "assessment_type" in update_data and update_data["assessment_type"] not in VALID_ASSESSMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid assessment type. Must be one of: {VALID_ASSESSMENT_TYPES}",
        )

    if "assessment_date" in update_data and update_data["assessment_date"]:
        update_data["assessment_date"] = update_data["assessment_date"].isoformat()

    client.table("movement_assessments").update(update_data).eq("id", str(assessment_id)).execute()

    return get_assessment(assessment_id, current_user)


@router.delete(
    "/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_assessment(
    assessment_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a movement assessment (CASCADE deletes photos)."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    assessment = _verify_assessment_ownership(client, assessment_id, current_user)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    # Delete photos from storage
    photos_response = (
        client.table("assessment_photos")
        .select("storage_path")
        .eq("assessment_id", str(assessment_id))
        .execute()
    )
    for photo in photos_response.data or []:
        try:
            client.storage.from_(STORAGE_BUCKET).remove([photo["storage_path"]])
        except Exception:
            pass  # Best effort cleanup

    client.table("movement_assessments").delete().eq("id", str(assessment_id)).execute()
    return None


@router.post(
    "/{assessment_id}/photos",
    response_model=AssessmentPhotoResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_photo(
    assessment_id: UUID,
    file: UploadFile = File(...),
    view_type: str = Form(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Upload a photo for a movement assessment."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    assessment = _verify_assessment_ownership(client, assessment_id, current_user)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found",
        )

    if view_type not in ("anterior", "lateral", "posterior"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view_type must be one of: anterior, lateral, posterior",
        )

    # Validate file type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    # Read file content
    file_bytes = file.file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 10MB)",
        )

    # Determine extension
    ext = "jpg"
    if "png" in content_type:
        ext = "png"
    elif "webp" in content_type:
        ext = "webp"

    timestamp = int(time.time())
    storage_path = f"{current_user.id}/{assessment['athlete_id']}/{assessment_id}/{view_type}_{timestamp}.{ext}"

    try:
        client.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            file_bytes,
            {"content-type": content_type},
        )
    except Exception as e:
        logger.exception("Photo upload failed for assessment %s", assessment_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Photo upload failed",
        )

    # Insert photo record
    photo_data = {
        "assessment_id": str(assessment_id),
        "view_type": view_type,
        "storage_path": storage_path,
    }
    photo_response = client.table("assessment_photos").insert(photo_data).execute()

    if not photo_response.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save photo record",
        )

    photo_row = photo_response.data[0]

    # Generate signed URL
    photo_url = None
    try:
        signed = client.storage.from_(STORAGE_BUCKET).create_signed_url(
            storage_path, SIGNED_URL_EXPIRY
        )
        photo_url = signed.get("signedURL") or signed.get("signedUrl")
    except Exception:
        pass

    return AssessmentPhotoResponse(
        id=photo_row["id"],
        assessment_id=photo_row["assessment_id"],
        view_type=photo_row["view_type"],
        storage_path=photo_row["storage_path"],
        photo_url=photo_url,
        created_at=photo_row["created_at"],
    )


@router.delete(
    "/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_photo(
    photo_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a single assessment photo."""
    require_coach_or_admin(current_user)

    client = get_client_or_503()

    # Fetch photo with ownership check via assessment → athlete chain
    response = (
        client.table("assessment_photos")
        .select("*, movement_assessments!inner(athlete_id, athletes!inner(coach_id, user_id))")
        .eq("id", str(photo_id))
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    photo = response.data[0]
    assessment_data = photo.get("movement_assessments", {})
    athlete_data = assessment_data.get("athletes", {})
    if current_user.role in ("coach", "admin"):
        if str(athlete_data.get("coach_id")) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo not found",
            )
    elif current_user.role == "athlete":
        if str(athlete_data.get("user_id")) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Photo not found",
            )

    # Delete from storage
    try:
        client.storage.from_(STORAGE_BUCKET).remove([photo["storage_path"]])
    except Exception:
        pass

    # Delete record
    client.table("assessment_photos").delete().eq("id", str(photo_id)).execute()
    return None
