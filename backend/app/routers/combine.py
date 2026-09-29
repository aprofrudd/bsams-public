"""Boxing Science Combine router.

Three audiences:
  - the coach console (event setup, roster, sync)
  - the station iPads (submit and correct attempts)
  - the gym big screen, which is PUBLIC and unauthenticated

Everything is a sync `def` so FastAPI runs it in the threadpool: the Supabase
client is synchronous, and an `async def` here would block the event loop under
polling (BUG-007).
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
from datetime import date, datetime, time as dtime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.access_control import require_admin, require_coach_or_admin
from app.core.security import AuthenticatedUser, get_current_user
from app.core.supabase_client import get_client_or_503
from app.schemas.combine import (
    AttemptResponse,
    AttemptSubmit,
    AttemptUpdate,
    CombineEventCreate,
    CombineEventListItem,
    CombineEventResponse,
    CombineEventUpdate,
    LeaderboardResponse,
    ParticipantResponse,
    ParticipantUpdate,
    PublicEventMeta,
    PublicLeaderboardResponse,
    RosterBulkRequest,
    RosterBulkResponse,
    RosterRowResult,
    ShareTokenResponse,
    Station,
    StationRosterEntry,
    StationRosterResponse,
    normalise_weight_category,
    reference_load_error,
)
from app.services import combine_promotion
from app.services.combine_engine import (
    STATION_SPECS,
    AttemptValue,
    LeaderboardFilters,
    StationSpec,
    best_per_participant,
    build_leaderboard,
    score_attempt,
)
from app.services.combine_norms import (
    compute_bs_norms,
    coverage_from_snapshot,
    fetch_all_rows,
)

logger = logging.getLogger("bsams")

router = APIRouter(prefix="/combine", tags=["combine"])

limiter = Limiter(key_func=get_remote_address)


def _token_key(request: Request) -> str:
    """Key the public limiter on the share token, not the client address.

    Browser traffic reaches this service through the Next.js rewrite proxy and
    uvicorn runs without --proxy-headers, so `get_remote_address` returns a proxy
    address shared by every viewer. An IP bucket here would throttle the whole gym
    as one client.
    """
    token = request.path_params.get("token")
    return f"combine_public:{token}" if token else get_remote_address(request)


public_limiter = Limiter(key_func=_token_key)

SHARE_TOKEN_BYTES = 24  # 192 bits — this URL is on a wall all day
SHARE_TOKEN_TTL_DAYS = 2
MAX_TOKEN_RETRIES = 3
# Both landmine sides plus re-runs put a real boxer well past twenty attempts at one
# station; migration 034 widens the column CHECK to match.
MAX_ATTEMPTS_PER_STATION = 40
# Two workers can read the same attempt_number before either of them inserts.
MAX_INSERT_RETRIES = 3
# Every device showing the link shares one bucket per token, and a 304 counts against
# it too: twenty boards polling every 5 s is 240 requests a minute on its own.
PUBLIC_RATE_LIMIT = "1200/minute"
PUBLIC_CACHE_TTL_S = 5.0
PUBLIC_CACHE_MAX_KEYS = 64
PAYLOAD_SCHEMA_VERSION = 2
# The console edits these three as separate fields, so only a merged view can tell
# whether the reference load still sits on the ladder.
LANDMINE_SETTING_KEYS = (
    "landmine_loads_kg",
    "landmine_reference_load_kg",
    "landmine_reference_tolerance_kg",
)

# Identical body for every public failure: a caller must not be able to tell a
# revoked token from one that never existed.
_PUBLIC_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
)

_leaderboard_cache: Dict[str, Tuple[float, str, dict]] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_share_token() -> str:
    return secrets.token_urlsafe(SHARE_TOKEN_BYTES)


def _default_expiry(event_date: date) -> str:
    return datetime.combine(
        event_date + timedelta(days=SHARE_TOKEN_TTL_DAYS), dtime(23, 59), timezone.utc
    ).isoformat()


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _share_url_path(token: str) -> str:
    return f"/combine/live/{token}"


def _get_owned_event(client, event_id: UUID, current_user: AuthenticatedUser) -> dict:
    """Fetch an event the caller owns, or 404.

    Ownership is by `coach_id`, matching `verify_athlete_access` — an admin does not
    get global access to other coaches' events.
    """
    result = (
        client.table("combine_events").select("*").eq("id", str(event_id)).limit(1).execute()
    )
    rows = result.data or []
    if not rows or str(rows[0].get("coach_id")) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Combine event not found"
        )
    return rows[0]


def _get_participant(client, participant_id: UUID, event_id: str) -> dict:
    result = (
        client.table("combine_participants")
        .select("*")
        .eq("id", str(participant_id))
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows or str(rows[0].get("combine_event_id")) != str(event_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found"
        )
    return rows[0]


def _load_participants(client, event_id: str) -> List[dict]:
    """Roster rows joined to the athlete name fields the board displays."""
    result = (
        client.table("combine_participants")
        .select("*, athletes!inner(first_name, surname, name, gender, date_of_birth)")
        .eq("combine_event_id", event_id)
        .execute()
    )
    out: List[dict] = []
    for row in result.data or []:
        athlete = row.pop("athletes", None) or {}
        out.append(
            {
                **row,
                "first_name": athlete.get("first_name"),
                "surname": athlete.get("surname"),
                "name": athlete.get("name"),
                "gender": athlete.get("gender"),
            }
        )
    return out


def _load_attempts(client, event_id: str, *, include_voided: bool = False) -> List[dict]:
    """Every attempt for the event, paged past PostgREST's db-max-rows.

    Forty boxers logging both landmine sides reaches roughly 1,080 rows, and an
    unpaginated select is cut at 1,000 silently — results would simply stop appearing
    on the board with nothing to say why.
    """

    def build():
        query = client.table("combine_attempts").select("*").eq("combine_event_id", event_id)
        return query if include_voided else query.is_("voided_at", "null")

    return fetch_all_rows(build)


def _count(client, table: str, column: str, value: str) -> int:
    result = client.table(table).select("id").eq(column, value).execute()
    return len(result.data or [])


def _event_response(row: dict, participant_count: int = 0) -> CombineEventResponse:
    return CombineEventResponse(
        **{k: v for k, v in row.items() if k in CombineEventResponse.model_fields},
        share_url_path=_share_url_path(row["share_token"]),
        participant_count=participant_count,
        # Counts only. The console needs to know which bands are backed by enough
        # athletes, not what the Boxing Science distribution looks like.
        bs_norms_coverage=coverage_from_snapshot(row.get("bs_norms_snapshot")),
    )


def _touch_results(client, event_id: str) -> None:
    """Bump the change probe that drives polling clients' ETags."""
    client.table("combine_events").update(
        {"results_updated_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", event_id).execute()
    _invalidate_cache(event_id)


def _invalidate_cache(event_id: str) -> None:
    for key in [k for k in _leaderboard_cache if k.startswith(f"{event_id}|")]:
        _leaderboard_cache.pop(key, None)


FILTER_ATTRS = ("weight_category", "age_group", "club", "squad")


def _filter_token(attr: str, value: Optional[str]) -> Optional[str]:
    """One comparable spelling of a filter value.

    Board URLs are typed onto a TV by hand — `?weight_category=57 KG`, `?club=repton` —
    and an exact match answers those with an empty board in a full hall. Query values
    and roster values both come through here, so the two can only differ on substance.
    The token also keys the ETag and the public cache, so two spellings of one filter
    stay one cache entry rather than two copies of the same board.
    """
    text = (value or "").strip()
    if not text:
        return None
    if attr == "weight_category":
        # `or text.casefold()`: a free-text category predating the England Boxing
        # vocabulary still has to match itself on the roster.
        return normalise_weight_category(text) or text.casefold()
    return text.casefold()


def _filters_from_query(
    weight_category: Optional[str],
    age_group: Optional[str],
    club: Optional[str],
    squad: Optional[str],
) -> LeaderboardFilters:
    """Tokenised query values. `_resolve_filters` points them at the roster's spelling."""
    return LeaderboardFilters(
        weight_category=_filter_token("weight_category", weight_category),
        age_group=_filter_token("age_group", age_group),
        club=_filter_token("club", club),
        squad=_filter_token("squad", squad),
    )


def _resolve_filters(filters: LeaderboardFilters, participants: List[dict]) -> LeaderboardFilters:
    """Turn each token back into the exact string the roster stores.

    The engine matches raw strings, so this is where a forgiving URL meets it. A
    token nothing on the roster matches falls back to no filter, the way the kiosk's
    panel parameter falls back to rotating: a mistyped TV link then shows the whole
    room instead of a blank screen.
    """
    resolved: Dict[str, Optional[str]] = {}
    for attr in FILTER_ATTRS:
        token = getattr(filters, attr)
        match: Optional[str] = None
        if token:
            for participant in participants:
                value = participant.get(attr)
                if value and _filter_token(attr, value) == token:
                    match = value
                    break
        resolved[attr] = match
    return LeaderboardFilters(**resolved)


def _float(value: Any) -> Optional[float]:
    """Coerce a JSONB value to float. PostgREST hands NUMERIC back as a string."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _require_ranked_velocity(event: dict, station: str, measures: dict) -> None:
    """422 when a landmine throw carries nothing in the metric this event ranks on.

    There is no peak/mean fallback anywhere downstream, so such an attempt would save,
    promote nothing and sit off the board — and the operator would only find out at the
    end of the day.
    """
    if station != "landmine":
        return
    metric = event.get("landmine_velocity_metric") or "peak"
    key = "peak_velocity_ms" if metric == "peak" else "mean_velocity_ms"
    if measures.get(key) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"This event ranks landmine on {metric} velocity — enter it",
        )


def _attempt_display(
    row: dict, event: dict, scored: Optional[AttemptValue], spec: StationSpec
) -> Optional[str]:
    """The text on the station screen's attempt chips.

    Landmine and air bike read their measures rather than the ranked value: a throw at
    a non-reference load and a sprint by a boxer who has not been weighed in are both
    unrankable, and a chip reading "—" looks like a save that was lost.
    """
    measures = row.get("measures") or {}
    station = row.get("station")

    if station == "landmine":
        metric = event.get("landmine_velocity_metric") or "peak"
        primary = "peak_velocity_ms" if metric == "peak" else "mean_velocity_ms"
        velocity = _float(measures.get(primary))
        if velocity is None:
            # Only for attempts logged before the metric was required; the board still
            # ranks the configured one alone.
            velocity = _float(measures.get("peak_velocity_ms")) or _float(
                measures.get("mean_velocity_ms")
            )
        if velocity is None:
            return None
        parts = [f"{velocity:.{spec.decimals}f} {spec.unit}"]
        load = _float(measures.get("load_kg"))
        if load is not None:
            parts.append(f"{load:g} kg")
        side = str(measures.get("side") or "").strip()
        if side:
            parts.append(side[0].upper())
        return " · ".join(parts)

    if station == "air_bike":
        sprint = measures.get("sprint_number")
        suffix = f" · S{int(sprint)}" if sprint else ""
        if scored is not None:
            return f"{scored.primary:.{spec.decimals}f} {spec.unit}{suffix}"
        # No body mass on the roster yet, so W/kg is undefined: show what was typed.
        power = _float(measures.get("power_7s"))
        return f"{power:g} W{suffix}" if power is not None else None

    if scored is None:
        return None
    unit = f" {spec.unit}" if spec.unit else ""
    return f"{scored.primary:.{spec.decimals}f}{unit}"


def _attempt_response(row: dict, event: dict, participant: dict) -> AttemptResponse:
    scored = score_attempt(row, participant=participant, event=event)
    spec = STATION_SPECS.get(row["station"])
    display = _attempt_display(row, event, scored, spec) if spec else None
    return AttemptResponse(
        **{k: v for k, v in row.items() if k in AttemptResponse.model_fields},
        value=scored.primary if scored else None,
        display_value=display,
    )


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@router.post("/events", response_model=CombineEventResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_event(
    request: Request,
    body: CombineEventCreate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Create a combine event and mint its public share token."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    payload = body.model_dump()
    payload["event_date"] = str(body.event_date)
    payload["coach_id"] = str(current_user.id)
    payload["share_token_expires_at"] = _default_expiry(body.event_date)

    for _ in range(MAX_TOKEN_RETRIES):
        payload["share_token"] = _generate_share_token()
        try:
            result = client.table("combine_events").insert(payload).execute()
        except Exception as exc:  # pragma: no cover - collision is vanishingly rare
            if "share_token" in str(exc):
                continue
            if "combine_events_coach_id_event_name_event_date_key" in str(exc) or (
                "duplicate" in str(exc).lower()
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An event with this name and date already exists",
                )
            logger.exception("Failed to create combine event")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create combine event",
            )
        if result.data:
            return _event_response(result.data[0])

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to create combine event",
    )


@router.get("/events", response_model=List[CombineEventListItem])
@limiter.limit("60/minute")
def list_events(
    request: Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List the caller's combine events, newest first."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    result = (
        client.table("combine_events")
        .select("*")
        .eq("coach_id", str(current_user.id))
        .order("event_date", desc=True)
        .execute()
    )
    events = result.data or []
    if not events:
        return []

    event_ids = [str(e["id"]) for e in events]
    participants = (
        client.table("combine_participants")
        .select("combine_event_id")
        .in_("combine_event_id", event_ids)
        .execute()
    ).data or []
    attempts = (
        client.table("combine_attempts")
        .select("combine_event_id")
        .in_("combine_event_id", event_ids)
        .execute()
    ).data or []

    participant_counts: Dict[str, int] = {}
    for row in participants:
        key = str(row["combine_event_id"])
        participant_counts[key] = participant_counts.get(key, 0) + 1
    attempt_counts: Dict[str, int] = {}
    for row in attempts:
        key = str(row["combine_event_id"])
        attempt_counts[key] = attempt_counts.get(key, 0) + 1

    return [
        CombineEventListItem(
            **{k: v for k, v in e.items() if k in CombineEventListItem.model_fields},
            participant_count=participant_counts.get(str(e["id"]), 0),
            attempt_count=attempt_counts.get(str(e["id"]), 0),
        )
        for e in events
    ]


@router.get("/events/{event_id}", response_model=CombineEventResponse)
@limiter.limit("60/minute")
def get_event(
    request: Request,
    event_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)
    count = _count(client, "combine_participants", "combine_event_id", str(event_id))
    return _event_response(event, count)


@router.patch("/events/{event_id}", response_model=CombineEventResponse)
@limiter.limit("60/minute")
def update_event(
    request: Request,
    event_id: UUID,
    body: CombineEventUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Update event settings.

    Going live requires the display-consent confirmation: these are usually minors
    and the board is a public URL.
    """
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)

    update = body.model_dump(exclude_unset=True)
    consent = update.pop("public_display_consent_confirmed", None)
    if consent is True and not event.get("public_display_consent_confirmed_at"):
        update["public_display_consent_confirmed_at"] = datetime.now(timezone.utc).isoformat()
    elif consent is False:
        update["public_display_consent_confirmed_at"] = None

    already_confirmed = event.get("public_display_consent_confirmed_at")
    confirming_now = update.get("public_display_consent_confirmed_at")
    if update.get("status") == "live" and not (already_confirmed or confirming_now):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Confirm that participants' names may be shown on a public screen "
                "before making this event live"
            ),
        )

    if "event_date" in update and update["event_date"] is not None:
        new_date = str(update["event_date"])
        update["event_date"] = new_date
        if new_date != str(event.get("event_date")):
            # Promoted rows are keyed on the event date, so moving it strands every
            # result already written and the merge RPC starts a second row.
            if _count(client, "combine_attempts", "combine_event_id", str(event_id)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Results are already logged for this event — the date can no "
                        "longer change"
                    ),
                )
            # The public link expires two days after the event, so the link moves too.
            update["share_token_expires_at"] = _default_expiry(
                date.fromisoformat(new_date)
            )

    # Checked against the merged settings, and only when this PATCH touches one of
    # them: an event that is already misconfigured has to stay editable, not least to
    # fix exactly this.
    if any(key in update for key in LANDMINE_SETTING_KEYS):
        resolved = {key: update.get(key, event.get(key)) for key in LANDMINE_SETTING_KEYS}
        error = reference_load_error(
            resolved["landmine_loads_kg"],
            resolved["landmine_reference_load_kg"],
            resolved["landmine_reference_tolerance_kg"],
        )
        if error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    if update:
        update["results_updated_at"] = datetime.now(timezone.utc).isoformat()
        result = (
            client.table("combine_events").update(update).eq("id", str(event_id)).execute()
        )
        event = (result.data or [event])[0]
        _invalidate_cache(str(event_id))

    count = _count(client, "combine_participants", "combine_event_id", str(event_id))
    return _event_response(event, count)


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
def delete_event(
    request: Request,
    event_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete an event. Promoted athlete results survive (the tag is set to NULL)."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    _get_owned_event(client, event_id, current_user)
    client.table("combine_events").delete().eq("id", str(event_id)).execute()
    _invalidate_cache(str(event_id))
    return None


@router.post("/events/{event_id}/rotate-token", response_model=ShareTokenResponse)
@limiter.limit("10/minute")
def rotate_share_token(
    request: Request,
    event_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Issue a new share token, killing the old link immediately."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)

    update = {
        "share_token": _generate_share_token(),
        "share_token_expires_at": _default_expiry(
            date.fromisoformat(str(event["event_date"]))
        ),
        "share_revoked_at": None,
    }
    result = client.table("combine_events").update(update).eq("id", str(event_id)).execute()
    row = (result.data or [{**event, **update}])[0]
    _invalidate_cache(str(event_id))
    return ShareTokenResponse(
        share_token=row["share_token"],
        share_url_path=_share_url_path(row["share_token"]),
        share_token_expires_at=row["share_token_expires_at"],
        share_revoked_at=row.get("share_revoked_at"),
    )


@router.post("/events/{event_id}/revoke-token", response_model=ShareTokenResponse)
@limiter.limit("10/minute")
def revoke_share_token(
    request: Request,
    event_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Kill the public link without issuing a new one."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)

    revoked_at = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("combine_events")
        .update({"share_revoked_at": revoked_at})
        .eq("id", str(event_id))
        .execute()
    )
    row = (result.data or [{**event, "share_revoked_at": revoked_at}])[0]
    _invalidate_cache(str(event_id))
    return ShareTokenResponse(
        share_token=row["share_token"],
        share_url_path=_share_url_path(row["share_token"]),
        share_token_expires_at=row["share_token_expires_at"],
        share_revoked_at=row.get("share_revoked_at"),
    )


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------


def _participant_response(row: dict) -> ParticipantResponse:
    name = row.get("name") or " ".join(
        p for p in [row.get("first_name"), row.get("surname")] if p
    )
    return ParticipantResponse(
        **{k: v for k, v in row.items() if k in ParticipantResponse.model_fields and k != "name"},
        name=name or "—",
    )


@router.get("/events/{event_id}/participants", response_model=List[ParticipantResponse])
@limiter.limit("120/minute")
def list_participants(
    request: Request,
    event_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    client = get_client_or_503()
    _get_owned_event(client, event_id, current_user)
    rows = _load_participants(client, str(event_id))
    rows.sort(key=lambda r: r.get("bib") or 0)
    return [_participant_response(r) for r in rows]


@router.post(
    "/events/{event_id}/participants/bulk",
    response_model=RosterBulkResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("10/minute")
def bulk_add_participants(
    request: Request,
    event_id: UUID,
    body: RosterBulkRequest,
    dry_run: bool = Query(False, description="Preview matching without writing anything"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Import a roster, creating athlete records where needed.

    Run it with `dry_run=true` first: the response has the identical shape, so the
    console can show exactly which rows would be created and which would be linked
    to an existing athlete. That preview is the guard against quietly creating forty
    duplicate athletes five minutes before the first boxer steps on the mat.
    """
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)

    existing_participants = _load_participants(client, str(event_id))
    taken_bibs: Set[int] = {p["bib"] for p in existing_participants if p.get("bib")}
    linked_athletes: Set[str] = {str(p["athlete_id"]) for p in existing_participants}
    next_bib = max(taken_bibs) + 1 if taken_bibs else 1

    # Paged: an admin can own more than PostgREST's 1,000-row page, and this lookup is
    # the only thing between a pasted roster and forty duplicate athlete records.
    coach_athletes = fetch_all_rows(
        lambda: client.table("athletes")
        .select("id, name, first_name, surname")
        .eq("coach_id", str(current_user.id))
    )
    by_name: Dict[str, dict] = {}
    for athlete in coach_athletes:
        full = (athlete.get("name") or "").strip().lower()
        if full:
            by_name.setdefault(full, athlete)

    results: List[RosterRowResult] = []
    created_athletes = 0
    linked_count = 0
    participants_added = 0

    for index, row in enumerate(body.rows):
        # Strict vocabulary: a free-text division would sit in the board's filter chips
        # matching one boxer and nobody else.
        weight_category = normalise_weight_category(row.weight_category)
        if (row.weight_category or "").strip() and weight_category is None:
            results.append(
                RosterRowResult(
                    index=index,
                    action="error",
                    reason=f"Unknown weight category '{row.weight_category}'",
                )
            )
            continue

        full_name = " ".join(p for p in [row.first_name, row.surname] if p).strip()
        athlete_id: Optional[str] = None
        action = "created"
        matched_name: Optional[str] = None

        if row.athlete_id:
            owned = (
                client.table("athletes")
                .select("id, name")
                .eq("id", str(row.athlete_id))
                .eq("coach_id", str(current_user.id))
                .execute()
            ).data or []
            if not owned:
                results.append(
                    RosterRowResult(
                        index=index,
                        action="error",
                        reason="Athlete not found for this account",
                    )
                )
                continue
            athlete_id = str(owned[0]["id"])
            matched_name = owned[0].get("name")
            action = "linked"
        elif body.on_name_match == "link" and full_name.lower() in by_name:
            match = by_name[full_name.lower()]
            athlete_id = str(match["id"])
            matched_name = match.get("name")
            action = "linked"

        if athlete_id and athlete_id in linked_athletes:
            results.append(
                RosterRowResult(
                    index=index,
                    action="skipped",
                    athlete_id=UUID(athlete_id),
                    matched_name=matched_name,
                    reason="Already on this roster",
                )
            )
            continue

        bib = row.bib
        if bib is None:
            while next_bib in taken_bibs:
                next_bib += 1
            bib = next_bib
        elif bib in taken_bibs:
            results.append(
                RosterRowResult(index=index, action="error", bib=bib, reason="Bib already used")
            )
            continue
        taken_bibs.add(bib)

        if dry_run:
            results.append(
                RosterRowResult(
                    index=index,
                    action=action,
                    athlete_id=UUID(athlete_id) if athlete_id else None,
                    matched_name=matched_name,
                    bib=bib,
                )
            )
            if action == "created":
                created_athletes += 1
            else:
                linked_count += 1
            participants_added += 1
            continue

        if athlete_id is None:
            athlete_payload = {
                "coach_id": str(current_user.id),
                "name": full_name,
                "first_name": row.first_name,
                "surname": row.surname,
                "gender": row.gender.value if hasattr(row.gender, "value") else row.gender,
                "status": "amateur",
            }
            if row.date_of_birth:
                athlete_payload["date_of_birth"] = str(row.date_of_birth)
            if row.body_mass_kg is not None:
                athlete_payload["body_mass_kg"] = row.body_mass_kg
            created = client.table("athletes").insert(athlete_payload).execute()
            if not created.data:
                results.append(
                    RosterRowResult(index=index, action="error", reason="Failed to create athlete")
                )
                continue
            athlete_id = str(created.data[0]["id"])
            created_athletes += 1
        else:
            linked_count += 1

        participant_payload = {
            "combine_event_id": str(event_id),
            "athlete_id": athlete_id,
            "bib": bib,
            "club": row.club,
            "weight_category": weight_category,
            "age_group": row.age_group,
            "body_mass_kg": row.body_mass_kg,
            "squad": row.squad,
        }
        created_participant = (
            client.table("combine_participants").insert(participant_payload).execute()
        )
        if not created_participant.data:
            results.append(
                RosterRowResult(index=index, action="error", reason="Failed to add to roster")
            )
            continue

        linked_athletes.add(athlete_id)
        participants_added += 1
        results.append(
            RosterRowResult(
                index=index,
                action=action,
                athlete_id=UUID(athlete_id),
                participant_id=UUID(str(created_participant.data[0]["id"])),
                matched_name=matched_name,
                bib=bib,
            )
        )

    if not dry_run and participants_added:
        _touch_results(client, str(event_id))

    return RosterBulkResponse(
        dry_run=dry_run,
        created_athletes=created_athletes,
        linked_athletes=linked_count,
        participants_added=participants_added,
        results=results,
    )


@router.patch("/participants/{participant_id}", response_model=ParticipantResponse)
@limiter.limit("120/minute")
def update_participant(
    request: Request,
    participant_id: UUID,
    body: ParticipantUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    existing = (
        client.table("combine_participants")
        .select("*")
        .eq("id", str(participant_id))
        .limit(1)
        .execute()
    ).data or []
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    event = _get_owned_event(client, UUID(str(existing[0]["combine_event_id"])), current_user)

    update = body.model_dump(exclude_unset=True)
    withdrawn = update.pop("withdrawn", None)
    if withdrawn is True:
        update["withdrawn_at"] = datetime.now(timezone.utc).isoformat()
    elif withdrawn is False:
        update["withdrawn_at"] = None

    mass_changed = "body_mass_kg" in update and update["body_mass_kg"] != existing[0].get(
        "body_mass_kg"
    )

    if update:
        client.table("combine_participants").update(update).eq(
            "id", str(participant_id)
        ).execute()
        _touch_results(client, str(event["id"]))

    rows = _load_participants(client, str(event["id"]))
    row = next((r for r in rows if str(r["id"]) == str(participant_id)), None)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    if mass_changed:
        # air_bike_tests.body_mass_kg is NOT NULL, so a sprint logged before the
        # weigh-in had nowhere to land. The weigh-in is when that test gets created —
        # and every W/kg on the board is rescaled by the corrected mass.
        #
        # Scoped to the bike, because body mass changes nothing else: a full rebuild
        # would read-modify-write the whole `metrics` column, which is not atomic
        # against a station save merging into it in the same moment.
        _promote_for_participant(client, event, row, merge=True, station="air_bike")

    return _participant_response(row)


@router.delete("/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
def delete_participant(
    request: Request,
    participant_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Remove someone from the roster. Their athlete record is left alone.

    Refused once they have logged anything: the attempts FK cascades, so this would
    delete the record of what they actually did on the day, voided attempts included.
    """
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    existing = (
        client.table("combine_participants")
        .select("id, combine_event_id")
        .eq("id", str(participant_id))
        .limit(1)
        .execute()
    ).data or []
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    event = _get_owned_event(client, UUID(str(existing[0]["combine_event_id"])), current_user)

    if _count(client, "combine_attempts", "participant_id", str(participant_id)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This boxer has logged attempts — mark them withdrawn instead",
        )

    client.table("combine_participants").delete().eq("id", str(participant_id)).execute()
    _touch_results(client, str(event["id"]))
    return None


# ---------------------------------------------------------------------------
# Attempts
# ---------------------------------------------------------------------------


def _promote_for_participant(
    client,
    event: dict,
    participant: dict,
    *,
    merge: bool,
    station: Optional[str] = None,
) -> None:
    """Re-derive this athlete's promoted results from their surviving attempts.

    `station` is the hot path: a save writes only the station it just saved, so two
    iPads on two stations cannot roll each other's best back with a stale read. The
    cold path leaves it unset and rebuilds everything, which is the only way to clear
    a station whose attempts have all been voided.
    """
    attempts = (
        client.table("combine_attempts")
        .select("*")
        .eq("participant_id", str(participant["id"]))
        .execute()
    ).data or []
    combine_promotion.promote_participant(
        client,
        event=event,
        participant=participant,
        attempts=attempts,
        merge=merge,
        station=station,
    )


def _find_by_client_id(client, event_id: str, client_attempt_id) -> Optional[dict]:
    """The attempt an earlier send of this same tap already created, if there is one."""
    if not client_attempt_id:
        return None
    rows = (
        client.table("combine_attempts")
        .select("*")
        .eq("combine_event_id", event_id)
        .eq("client_attempt_id", str(client_attempt_id))
        .limit(1)
        .execute()
    ).data or []
    return rows[0] if rows else None


def _next_attempt_number(client, participant_id: str, station: str) -> int:
    prior = (
        client.table("combine_attempts")
        .select("attempt_number")
        .eq("participant_id", participant_id)
        .eq("station", station)
        .execute()
    ).data or []
    numbers = [int(r["attempt_number"]) for r in prior if r.get("attempt_number") is not None]
    return (max(numbers) + 1) if numbers else 1


@router.post(
    "/events/{event_id}/attempts",
    response_model=AttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("300/minute")
def submit_attempt(
    request: Request,
    event_id: UUID,
    body: AttemptSubmit,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Log one attempt at one station.

    Every station iPad in the gym shares one apparent client address, hence the
    generous limit. `client_attempt_id` makes a retry — or a double-tapped SAVE —
    return the original attempt instead of creating a second one, and the same id
    resolves the race where two workers insert at once rather than 500ing at the
    station.
    """
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)
    participant = _get_participant(client, body.participant_id, str(event_id))

    existing = _find_by_client_id(client, str(event_id), body.client_attempt_id)
    if existing:
        return _attempt_response(existing, event, participant)

    measures = body.measures.model_dump()
    station = measures.pop("station")
    _require_ranked_velocity(event, station, measures)

    created_row: Optional[dict] = None
    for _ in range(MAX_INSERT_RETRIES):
        attempt_number = _next_attempt_number(client, str(body.participant_id), station)
        if attempt_number > MAX_ATTEMPTS_PER_STATION:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {MAX_ATTEMPTS_PER_STATION} attempts per station",
            )

        payload = {
            "combine_event_id": str(event_id),
            "participant_id": str(body.participant_id),
            "station": station,
            "attempt_number": attempt_number,
            "measures": {k: v for k, v in measures.items() if v is not None},
            "client_attempt_id": str(body.client_attempt_id) if body.client_attempt_id else None,
            "entered_by": str(current_user.id),
            "notes": body.notes,
        }
        try:
            created = client.table("combine_attempts").insert(payload).execute()
        except Exception as exc:
            if str(getattr(exc, "code", "")) != combine_promotion.UNIQUE_VIOLATION:
                logger.exception("Failed to save combine attempt")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to save attempt",
                )
            # The other worker got there first. If it was this same tap its row is the
            # answer; otherwise it only took the attempt number, so pick the next one.
            duplicate = _find_by_client_id(client, str(event_id), body.client_attempt_id)
            if duplicate:
                return _attempt_response(duplicate, event, participant)
            continue
        if created.data:
            created_row = created.data[0]
            break

    if created_row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save attempt"
        )

    _touch_results(client, str(event_id))
    _promote_for_participant(client, event, participant, merge=True, station=station)
    return _attempt_response(created_row, event, participant)


@router.get("/events/{event_id}/attempts", response_model=List[AttemptResponse])
@limiter.limit("120/minute")
def list_attempts(
    request: Request,
    event_id: UUID,
    participant_id: Optional[UUID] = Query(None),
    station: Optional[Station] = Query(None),
    include_voided: bool = Query(False),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Attempts for correction on the station screen."""
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)

    query = client.table("combine_attempts").select("*").eq("combine_event_id", str(event_id))
    if participant_id:
        query = query.eq("participant_id", str(participant_id))
    if station:
        query = query.eq("station", station)
    if not include_voided:
        query = query.is_("voided_at", "null")
    rows = query.execute().data or []
    rows.sort(key=lambda r: (r.get("station") or "", r.get("attempt_number") or 0))

    participants = {str(p["id"]): p for p in _load_participants(client, str(event_id))}
    return [
        _attempt_response(row, event, participants.get(str(row["participant_id"]), {}))
        for row in rows
    ]


@router.patch("/attempts/{attempt_id}", response_model=AttemptResponse)
@limiter.limit("120/minute")
def update_attempt(
    request: Request,
    attempt_id: UUID,
    body: AttemptUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Correct a mistyped attempt."""
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    existing = (
        client.table("combine_attempts").select("*").eq("id", str(attempt_id)).limit(1).execute()
    ).data or []
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    attempt = existing[0]
    event = _get_owned_event(client, UUID(str(attempt["combine_event_id"])), current_user)
    participant = _get_participant(
        client, UUID(str(attempt["participant_id"])), str(event["id"])
    )

    update: Dict[str, Any] = {}
    if body.measures is not None:
        measures = body.measures.model_dump()
        station = measures.pop("station")
        if station != attempt["station"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An attempt cannot be moved to a different station",
            )
        _require_ranked_velocity(event, station, measures)
        update["measures"] = {k: v for k, v in measures.items() if v is not None}
    if body.notes is not None:
        update["notes"] = body.notes

    if update:
        result = (
            client.table("combine_attempts").update(update).eq("id", str(attempt_id)).execute()
        )
        attempt = (result.data or [attempt])[0]
        _touch_results(client, str(event["id"]))
        # A correction can lower the best, so rebuild rather than merge.
        _promote_for_participant(client, event, participant, merge=False)

    return _attempt_response(attempt, event, participant)


@router.delete("/attempts/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
def delete_attempt(
    request: Request,
    attempt_id: UUID,
    hard: bool = Query(False, description="Delete permanently instead of voiding"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Void an attempt (default) or delete it outright.

    Voiding keeps the audit trail of what was actually recorded on the day, which
    matters more than tidiness when someone queries a result afterwards.
    """
    require_coach_or_admin(current_user)
    client = get_client_or_503()

    existing = (
        client.table("combine_attempts").select("*").eq("id", str(attempt_id)).limit(1).execute()
    ).data or []
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    attempt = existing[0]
    event = _get_owned_event(client, UUID(str(attempt["combine_event_id"])), current_user)
    participant = _get_participant(
        client, UUID(str(attempt["participant_id"])), str(event["id"])
    )

    if hard:
        client.table("combine_attempts").delete().eq("id", str(attempt_id)).execute()
    else:
        client.table("combine_attempts").update(
            {"voided_at": datetime.now(timezone.utc).isoformat(), "void_reason": "coach"}
        ).eq("id", str(attempt_id)).execute()

    _touch_results(client, str(event["id"]))
    _promote_for_participant(client, event, participant, merge=False)
    return None


@router.get(
    "/events/{event_id}/stations/{station}/roster", response_model=StationRosterResponse
)
@limiter.limit("120/minute")
def station_roster(
    request: Request,
    event_id: UUID,
    station: Station,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Who still needs this station, and what everyone has done so far."""
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)
    spec = STATION_SPECS[station]

    participants = [p for p in _load_participants(client, str(event_id)) if not p.get("withdrawn_at")]
    participants_by_id = {str(p["id"]): p for p in participants}
    attempts = [
        a for a in _load_attempts(client, str(event_id)) if a.get("station") == station
    ]
    bests = best_per_participant(
        attempts, participants_by_id=participants_by_id, event=event
    )

    counts: Dict[str, int] = {}
    last_at: Dict[str, str] = {}
    for attempt in attempts:
        pid = str(attempt["participant_id"])
        counts[pid] = counts.get(pid, 0) + 1
        created = attempt.get("created_at")
        if created and created > last_at.get(pid, ""):
            last_at[pid] = created

    entries: List[StationRosterEntry] = []
    for participant in participants:
        pid = str(participant["id"])
        best = bests.get(pid, {}).get(station)
        display = None
        if best is not None:
            unit = f" {spec.unit}" if spec.unit else ""
            display = f"{best.primary:.{spec.decimals}f}{unit}"
        name = participant.get("name") or " ".join(
            p for p in [participant.get("first_name"), participant.get("surname")] if p
        )
        entries.append(
            StationRosterEntry(
                participant_id=pid,
                bib=participant.get("bib") or 0,
                name=name or "—",
                club=participant.get("club"),
                weight_category=participant.get("weight_category"),
                body_mass_kg=participant.get("body_mass_kg"),
                squad=participant.get("squad"),
                attempt_count=counts.get(pid, 0),
                best_value=best.primary if best else None,
                best_display=display,
                last_attempt_at=last_at.get(pid),
                status="done" if counts.get(pid, 0) else "todo",
            )
        )

    # To-do first, then by bib — the operator works down the list.
    entries.sort(key=lambda e: (e.status == "done", e.bib))
    done = sum(1 for e in entries if e.status == "done")

    return StationRosterResponse(
        station=station,
        label=spec.label,
        unit=spec.unit,
        total=len(entries),
        done=done,
        entries=entries,
    )


# ---------------------------------------------------------------------------
# Leaderboard, norms, sync
# ---------------------------------------------------------------------------


def _build_board(client, event: dict, filters: LeaderboardFilters, *, public: bool) -> dict:
    """Three round-trips, regardless of how many boxers are in the room."""
    participants = _load_participants(client, str(event["id"]))
    attempts = _load_attempts(client, str(event["id"]))
    return build_leaderboard(
        event=event,
        participants=participants,
        attempts=attempts,
        filters=_resolve_filters(filters, participants),
        public=public,
    )


@router.get("/events/{event_id}/leaderboard", response_model=LeaderboardResponse)
@limiter.limit("120/minute")
def get_leaderboard(
    request: Request,
    event_id: UUID,
    weight_category: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    club: Optional[str] = Query(None),
    squad: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """The coach's view: real names, athlete ids and the numeric benchmark z."""
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)
    filters = _filters_from_query(weight_category, age_group, club, squad)
    board = _build_board(client, event, filters, public=False)
    return LeaderboardResponse(**board, unsynced_count=0)


@router.post("/events/{event_id}/refresh-norms", response_model=CombineEventResponse)
@limiter.limit("5/minute")
def refresh_norms(
    request: Request,
    event_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Snapshot the Boxing Science norms onto the event.

    Admin-only, matching the `boxing_science` benchmark guard in analysis.py. The
    snapshot holds aggregates only (mean, sd, n) — it is what the public board reads,
    so it must never contain athlete rows.
    """
    require_admin(current_user)
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)

    participants = _load_participants(client, str(event_id))
    exclude = {str(p["athlete_id"]) for p in participants}

    try:
        snapshot = compute_bs_norms(client, event=event, exclude_athlete_ids=exclude)
    except Exception:
        logger.exception("Failed to compute Boxing Science norms for event %s", event_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh benchmark norms",
        )

    result = (
        client.table("combine_events")
        .update(
            {
                "bs_norms_snapshot": snapshot,
                "bs_norms_updated_at": datetime.now(timezone.utc).isoformat(),
                "results_updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", str(event_id))
        .execute()
    )
    row = (result.data or [event])[0]
    _invalidate_cache(str(event_id))
    return _event_response(row, len(participants))


@router.post("/events/{event_id}/sync", response_model=LeaderboardResponse)
@limiter.limit("5/minute")
def sync_event(
    request: Request,
    event_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Re-promote every participant from their attempts.

    Attempts are authoritative; this rebuilds the derived athlete records. Idempotent,
    so it is the repair button when a promotion failed mid-event. `unsynced_count` is
    how many boxers still have a target that would not write, which is the one failure
    mode pressing the button again cannot fix.
    """
    require_coach_or_admin(current_user)
    client = get_client_or_503()
    event = _get_owned_event(client, event_id, current_user)

    participants = _load_participants(client, str(event_id))
    attempts = _load_attempts(client, str(event_id), include_voided=True)
    unsynced = combine_promotion.promote_event(
        client, event=event, participants=participants, attempts=attempts
    )
    _touch_results(client, str(event_id))

    board = _build_board(client, event, LeaderboardFilters(), public=False)
    return LeaderboardResponse(**board, unsynced_count=unsynced)


# ---------------------------------------------------------------------------
# PUBLIC — the gym big screen. No authentication.
# ---------------------------------------------------------------------------


def _resolve_public_event(token: str) -> dict:
    """Return the event for a valid public token, else raise an identical 404.

    Every check is explicit here: the backend holds the Supabase service_role key,
    so row-level security offers no protection on this path.
    """
    if not token or len(token) > 64:
        raise _PUBLIC_NOT_FOUND

    client = get_client_or_503()

    try:
        result = (
            client.table("combine_events")
            .select(
                "id, event_name, event_date, venue, status, public_name_style, "
                "show_bs_benchmark, show_club, landmine_reference_load_kg, "
                "landmine_reference_tolerance_kg, landmine_velocity_metric, "
                "airbike_score_basis, min_stations_for_overall, bs_norms_snapshot, "
                # The overall score is computed from this. A column left out of an
                # explicit projection reads as absent however the row is written, and
                # `overall_basis` maps absent to 'z' — so the console would switch to
                # percentile and the wall would quietly carry on scoring on z.
                "overall_score_basis, "
                "results_updated_at, share_token_expires_at, share_revoked_at, "
                "public_display_consent_confirmed_at"
            )
            .eq("share_token", token)
            .limit(1)
            .execute()
        )
    except Exception:
        logger.exception("Public combine lookup failed")
        # Not a 404: the kiosk clears the screen after three consecutive 404s, so a
        # Supabase blip would blank the TV as if the link had been revoked, and the
        # coach's only visible remedy is to rotate a link that was never broken. The
        # identical-404 rule governs what a *successful* lookup may reveal; a failure
        # that happens for every token, valid or not, distinguishes nothing.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )

    rows = result.data or []
    if not rows:
        raise _PUBLIC_NOT_FOUND
    event = rows[0]

    if event.get("status") not in ("live", "closed"):
        raise _PUBLIC_NOT_FOUND
    if event.get("share_revoked_at"):
        raise _PUBLIC_NOT_FOUND
    if not event.get("public_display_consent_confirmed_at"):
        raise _PUBLIC_NOT_FOUND
    expires = _parse_ts(event.get("share_token_expires_at"))
    if expires is None or expires < datetime.now(timezone.utc):
        raise _PUBLIC_NOT_FOUND

    return event


def _etag_for(event: dict, filter_key: str) -> str:
    raw = (
        f"{event['id']}|{event.get('results_updated_at')}|{filter_key}|{PAYLOAD_SCHEMA_VERSION}"
    )
    return 'W/"' + hashlib.sha256(raw.encode()).hexdigest()[:32] + '"'


def _cache_get(key: str) -> Optional[Tuple[str, dict]]:
    entry = _leaderboard_cache.get(key)
    if entry and entry[0] > time.monotonic():
        return entry[1], entry[2]
    if entry:
        _leaderboard_cache.pop(key, None)
    return None


def _cache_put(key: str, etag: str, payload: dict) -> None:
    if len(_leaderboard_cache) >= PUBLIC_CACHE_MAX_KEYS:
        _leaderboard_cache.clear()
    _leaderboard_cache[key] = (time.monotonic() + PUBLIC_CACHE_TTL_S, etag, payload)


@router.get("/public/{token}/meta", response_model=PublicEventMeta)
@public_limiter.limit(PUBLIC_RATE_LIMIT)
def public_meta(request: Request, token: str):
    """Cheap boot payload for the kiosk — no results."""
    event = _resolve_public_event(token)
    client = get_client_or_503()
    count = _count(client, "combine_participants", "combine_event_id", str(event["id"]))
    return PublicEventMeta(
        event_name=event["event_name"],
        event_date=event["event_date"],
        venue=event.get("venue"),
        status=event["status"],
        results_updated_at=event["results_updated_at"],
        participant_count=count,
    )


@router.get("/public/{token}", response_model=PublicLeaderboardResponse)
@public_limiter.limit(PUBLIC_RATE_LIMIT)
def public_leaderboard(
    request: Request,
    response: Response,
    token: str,
    weight_category: Optional[str] = Query(None, max_length=40),
    age_group: Optional[str] = Query(None, max_length=40),
    club: Optional[str] = Query(None, max_length=100),
    squad: Optional[str] = Query(None, max_length=40),
):
    """The big screen.

    Sanitised: no identifiers, no dates of birth, no body mass, and the Boxing
    Science comparison is a band rather than a z-score — a number next to the raw
    value would let anyone recover the norm's mean and SD.
    """
    event = _resolve_public_event(token)
    if not event.get("show_club", True):
        # A club the board does not show must not narrow it either: the filter would
        # let anyone enumerate the hidden club membership of named minors, one club at
        # a time. Dropped here, before `filter_key`, so it cannot key the ETag or the
        # cache either.
        club = None
    filters = _filters_from_query(weight_category, age_group, club, squad)
    filter_key = "|".join(
        [filters.weight_category or "", filters.age_group or "", filters.club or "", filters.squad or ""]
    )
    cache_key = f"{event['id']}|{filter_key}|public"
    etag = _etag_for(event, filter_key)

    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "no-cache"

    if request.headers.get("if-none-match") == etag:
        # The 304 carries the cache policy too: without it a proxy may answer the next
        # poll from its own copy and the board stops noticing new results.
        return Response(
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={"ETag": etag, "Cache-Control": "no-cache"},
        )

    cached = _cache_get(cache_key)
    if cached and cached[0] == etag:
        return PublicLeaderboardResponse(**cached[1])

    client = get_client_or_503()
    board = _build_board(client, event, filters, public=True)
    _cache_put(cache_key, etag, board)
    return PublicLeaderboardResponse(**board)
