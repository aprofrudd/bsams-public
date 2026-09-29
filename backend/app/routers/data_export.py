"""Data export for GDPR right to portability."""

import csv
import io
import json
import logging
import zipfile
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.access_control import verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/athlete/{athlete_id}")
@limiter.limit("5/minute")
def export_athlete_json(
    request: Request,
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Export all data for an athlete as JSON (GDPR data portability)."""
    client = get_client_or_503()

    if not verify_athlete_access(client, athlete_id, current_user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found",
        )

    aid = str(athlete_id)

    # Gather all data
    athlete = client.table("athletes").select("*").eq("id", aid).execute()
    events = client.table("performance_events").select("*").eq("athlete_id", aid).execute()
    sessions = client.table("training_sessions").select("*").eq("athlete_id", aid).execute()
    wellness = client.table("wellness_entries").select("*").eq("athlete_id", aid).execute()

    # Get exercise prescriptions via sessions
    session_ids = [s["id"] for s in (sessions.data or [])]
    exercises = []
    if session_ids:
        exercises_result = client.table("exercise_prescriptions").select("*").in_("session_id", session_ids).execute()
        exercises = exercises_result.data or []

    # VBT profiles
    vbt_profiles = client.table("vbt_profiles").select("*").eq("athlete_id", aid).execute()
    vbt_profile_ids = [p["id"] for p in (vbt_profiles.data or [])]
    vbt_sets = []
    if vbt_profile_ids:
        vbt_sets_result = client.table("vbt_sets").select("*").in_("profile_id", vbt_profile_ids).execute()
        vbt_sets = vbt_sets_result.data or []

    # Assessments (without photos - binary data)
    assessments = client.table("movement_assessments").select("*").eq("athlete_id", aid).execute()

    # Lactate tests
    lactate_tests = client.table("lactate_tests").select("*").eq("athlete_id", aid).execute()
    lactate_test_ids = [t["id"] for t in (lactate_tests.data or [])]
    lactate_stages = []
    if lactate_test_ids:
        lactate_stages_result = client.table("lactate_stages").select("*").in_("test_id", lactate_test_ids).execute()
        lactate_stages = lactate_stages_result.data or []

    # Air bike tests
    air_bike_tests = client.table("air_bike_tests").select("*").eq("athlete_id", aid).execute()
    air_bike_test_ids = [t["id"] for t in (air_bike_tests.data or [])]
    air_bike_sprints = []
    if air_bike_test_ids:
        air_bike_sprints_result = client.table("air_bike_sprints").select("*").in_("test_id", air_bike_test_ids).execute()
        air_bike_sprints = air_bike_sprints_result.data or []

    # Combine roster entries hold personal data (bib, club, weight category, body
    # mass) that lives nowhere else, so it has to be part of a portability export.
    combine_participants = (
        client.table("combine_participants").select("*").eq("athlete_id", aid).execute()
    )
    combine_participant_ids = [p["id"] for p in (combine_participants.data or [])]
    combine_attempts = []
    if combine_participant_ids:
        combine_attempts_result = (
            client.table("combine_attempts")
            .select("*")
            .in_("participant_id", combine_participant_ids)
            .execute()
        )
        combine_attempts = combine_attempts_result.data or []

    export_data = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "athlete": athlete.data[0] if athlete.data else None,
        "performance_events": events.data or [],
        "training_sessions": sessions.data or [],
        "wellness_entries": wellness.data or [],
        "exercise_prescriptions": exercises,
        "vbt_profiles": vbt_profiles.data or [],
        "vbt_sets": vbt_sets,
        "movement_assessments": assessments.data or [],
        "lactate_tests": lactate_tests.data or [],
        "lactate_stages": lactate_stages,
        "air_bike_tests": air_bike_tests.data or [],
        "air_bike_sprints": air_bike_sprints,
        "combine_participants": combine_participants.data or [],
        "combine_attempts": combine_attempts,
    }

    return export_data


@router.get("/athlete/{athlete_id}/csv")
@limiter.limit("5/minute")
def export_athlete_csv(
    request: Request,
    athlete_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Export all data for an athlete as a ZIP of CSV files (GDPR data portability)."""
    # Get JSON data first
    json_data = export_athlete_json(request, athlete_id, current_user)

    # Create ZIP with CSVs
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for key, rows in json_data.items():
            if key == "export_date" or key == "athlete":
                continue
            if isinstance(rows, list) and rows:
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    # Flatten any dict/list values to JSON strings
                    flat_row = {}
                    for k, v in row.items():
                        if isinstance(v, (dict, list)):
                            flat_row[k] = json.dumps(v)
                        else:
                            flat_row[k] = v
                    writer.writerow(flat_row)
                zf.writestr(f"{key}.csv", output.getvalue())

        # Add athlete profile as JSON
        if json_data.get("athlete"):
            zf.writestr("athlete_profile.json", json.dumps(json_data["athlete"], indent=2, default=str))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=athlete_{athlete_id}_export.zip"},
    )
