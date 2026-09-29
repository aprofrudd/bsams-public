"""Upload API router for CSV file processing."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

from app.core.access_control import require_coach_or_admin
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.upload import CSVUploadResult
from app.services.csv_ingestion import CSVIngestionService

router = APIRouter(prefix="/uploads", tags=["uploads"])
limiter = Limiter(key_func=get_remote_address)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROW_COUNT = 10_000


@router.post("/csv", response_model=CSVUploadResult, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def upload_csv(
    request: Request,
    file: UploadFile = File(..., description="CSV file to upload"),
    athlete_id: Optional[UUID] = Query(None, description="Athlete ID to associate with all rows"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Upload and process a CSV file containing performance data.

    The CSV should have columns for Date (DD/MM/YYYY format) and metrics
    like "CMJ Height (cm)". Optionally include "Body Mass (kg)" and "Athlete" columns.

    If athlete_id is provided, all rows will be associated with that athlete.
    Otherwise, rows must have an "Athlete" column for matching.
    """
    require_coach_or_admin(current_user)

    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    # Read file content with size check
    try:
        content = file.file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
            )
        csv_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        )

    # Validate CSV structure
    ingestion_service = CSVIngestionService()
    warnings = ingestion_service.validate_csv_structure(csv_content)

    # Check for critical warnings (missing date column)
    critical_warnings = [w for w in warnings if "date column" in w.lower() and "optional" not in w.lower()]
    if critical_warnings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=critical_warnings[0],
        )

    # Process CSV
    events, errors = ingestion_service.process_csv(csv_content, athlete_id=athlete_id)

    if not events and not errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid data found in CSV. Check column names and date format (DD/MM/YYYY).",
        )

    # Check row count limit
    if len(events) > MAX_ROW_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Too many rows. Maximum is {MAX_ROW_COUNT:,} rows per upload.",
        )

    # Get Supabase client
    client = get_client_or_503()

    # Pre-scan events to collect gender per athlete name (keyed by raw name for lookup)
    athlete_gender: dict[str, str] = {}
    for event in events:
        name = event.get("athlete_name")
        gender = event.get("gender")
        if name and gender and name not in athlete_gender:
            athlete_gender[name] = gender

    # Resolve athlete IDs for all events
    processed_count = 0
    athlete_cache: dict[str, str] = {}  # name -> id cache

    # If athlete_id provided, verify once upfront
    if athlete_id:
        athlete_check = (
            client.table("athletes")
            .select("id")
            .eq("id", str(athlete_id))
            .eq("coach_id", str(current_user.id))
            .execute()
        )
        if not athlete_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Athlete not found",
            )

    # Resolve athlete IDs and build batch list
    batch_list = []
    for event in events:
        try:
            resolved_athlete_id = None

            if athlete_id:
                resolved_athlete_id = str(athlete_id)

            elif "athlete_name" in event:
                # Normalize: collapse whitespace, title case
                raw_name = event["athlete_name"]
                athlete_name = " ".join(raw_name.split()).title()
                cache_key = athlete_name.lower()

                if cache_key in athlete_cache:
                    resolved_athlete_id = athlete_cache[cache_key]
                else:
                    # Case-insensitive lookup by name for this coach
                    athlete_result = (
                        client.table("athletes")
                        .select("id")
                        .eq("coach_id", str(current_user.id))
                        .ilike("name", athlete_name)
                        .execute()
                    )

                    if athlete_result.data:
                        resolved_athlete_id = athlete_result.data[0]["id"]
                    else:
                        # Auto-create athlete with gender
                        gender = athlete_gender.get(raw_name, "male")
                        new_athlete = (
                            client.table("athletes")
                            .insert({
                                "name": athlete_name,
                                "coach_id": str(current_user.id),
                                "gender": gender,
                            })
                            .execute()
                        )
                        resolved_athlete_id = new_athlete.data[0]["id"]

                    athlete_cache[cache_key] = resolved_athlete_id

            if resolved_athlete_id:
                batch_list.append({
                    "athlete_id": resolved_athlete_id,
                    "event_date": event["event_date"],
                    "metrics": event["metrics"],
                })
            else:
                errors.append({
                    "row": 0,
                    "reason": "No athlete ID or name for event",
                })

        except Exception as e:
            logger.exception("Error resolving athlete")
            errors.append({
                "row": 0,
                "reason": "Error resolving athlete",
            })

    # Deduplicate: check for existing events with same athlete_id + event_date
    if batch_list:
        # Group by athlete_id to batch the existence checks
        athlete_ids_in_batch = list({e["athlete_id"] for e in batch_list})
        existing_keys: set[tuple[str, str]] = set()

        for aid in athlete_ids_in_batch:
            existing = (
                client.table("performance_events")
                .select("athlete_id, event_date")
                .eq("athlete_id", aid)
                .execute()
            )
            for row in existing.data:
                existing_keys.add((row["athlete_id"], row["event_date"]))

        new_events = []
        skipped = 0
        for event_data in batch_list:
            key = (event_data["athlete_id"], event_data["event_date"])
            if key in existing_keys:
                skipped += 1
            else:
                new_events.append(event_data)

        if skipped > 0:
            errors.append({
                "row": 0,
                "reason": f"Skipped {skipped} duplicate(s) (same athlete + date already exists)",
            })

        batch_list = new_events

    # Batch insert all events at once
    if batch_list:
        try:
            client.table("performance_events").insert(batch_list).execute()
            processed_count = len(batch_list)
        except Exception:
            # Fall back to individual inserts on batch failure
            for event_data in batch_list:
                try:
                    client.table("performance_events").insert(event_data).execute()
                    processed_count += 1
                except Exception as e:
                    logger.exception("Failed to insert event for athlete %s", event_data.get("athlete_id"))
                    errors.append({
                        "row": 0,
                        "reason": "Database error",
                    })

    return CSVUploadResult(
        processed=processed_count,
        errors=errors,
        athlete_id=str(athlete_id) if athlete_id else None,
    )


@router.post("/csv/preview", status_code=status.HTTP_200_OK)
def preview_csv(
    file: UploadFile = File(..., description="CSV file to preview"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Preview CSV file without storing data.

    Returns parsed events and any validation warnings/errors.
    Useful for validating data before actual upload.
    """
    require_coach_or_admin(current_user)

    # Validate file type
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    # Read file content with size check
    try:
        content = file.file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
            )
        csv_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded",
        )

    # Validate and process
    ingestion_service = CSVIngestionService()
    warnings = ingestion_service.validate_csv_structure(csv_content)
    events, errors = ingestion_service.process_csv(csv_content)

    return {
        "warnings": warnings,
        "events_preview": events[:10],  # Return first 10 events as preview
        "total_events": len(events),
        "errors": errors,
    }
