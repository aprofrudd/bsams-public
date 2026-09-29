"""Boxing Science Combine schemas.

Three layers:
  - the event and its roster
  - station attempts (a discriminated union, one member per station)
  - the leaderboard, in an authenticated form and a sanitised public form

Station value ranges here are deliberately tighter than the metric registry's
(CMJ <= 90 cm, not <= 200). A mistyped decimal on a busy station would otherwise
own the big screen all day.
"""

from datetime import date, datetime
from typing import Annotated, Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.enums import Gender

Station = Literal["cmj", "pogo", "landmine", "grip", "trunk_rotation", "air_bike"]
EventStatus = Literal["draft", "live", "closed"]
NameStyle = Literal["full", "first_initial", "first_only", "bib"]
VelocityMetric = Literal["peak", "mean"]
# W/kg only: ranking raw watts against a W/kg Boxing Science norm put every boxer
# in the top band and labelled watts "W/kg" on the public screen.
AirBikeBasis = Literal["w_per_kg"]
RfdUnit = Literal["n_s", "kg_s"]
# How the Combine Score is composed. 'z' is a T-score over within-cohort z-scores;
# 'percentile' averages the boxer's per-station percentiles, which one freakish value
# on a skewed metric cannot inflate — on contact time only 1.7% of the project's
# athletes clear z >= 1.0 where normal theory expects 15.9%.
OverallScoreBasis = Literal["z", "percentile"]

# Some dynamometers read rate of force development in kg/s. Everything downstream —
# the metric registry, the engine, promotion, the norms — assumes N/s and carries no
# unit, so kg/s is converted at this boundary and never stored.
KGF_TO_NEWTONS = 9.80665
RFD_MAX_N_S = 20000

# The 20 England Boxing amateur categories, ascending. Mirrored by WEIGHT_CATEGORIES
# in frontend/src/lib/combineParticipantForm.ts — the two lists must stay in step.
WEIGHT_CATEGORIES = (
    "46kg", "48kg", "50kg", "51kg", "52kg", "54kg", "56kg", "57kg",
    "60kg", "63.5kg", "64kg", "67kg", "69kg", "71kg", "75kg", "80kg",
    "81kg", "86kg", "91kg", "91+kg",
)


def normalise_weight_category(raw: Optional[str]) -> Optional[str]:
    """Map a typed weight category onto the England Boxing vocabulary.

    Rosters are pasted from spreadsheets, so "57", "57 kg", "57KG", "+91" and
    "91kg+" all mean a category the board already knows. Anything else returns
    None, which the caller turns into a rejected row — a free-text division would
    sit in the filter chips matching one boxer and nobody else.
    """
    if raw is None:
        return None
    text = raw.strip().lower().replace(" ", "").replace("kg", "")
    open_ended = "+" in text
    text = text.replace("+", "")
    if not text:
        return None
    try:
        mass = float(text)
    except ValueError:
        return None
    # 57.0 -> "57", 63.5 -> "63.5"
    candidate = f"{mass:g}{'+kg' if open_ended else 'kg'}"
    return candidate if candidate in WEIGHT_CATEGORIES else None


# ---------------------------------------------------------------------------
# Event
# ---------------------------------------------------------------------------


MAX_LANDMINE_LOADS = 12


def validate_landmine_loads(loads: List[float]) -> List[float]:
    """A ladder the station screen can actually render, sorted and deduped."""
    if not loads:
        raise ValueError("At least one landmine load is required")
    if len(loads) > MAX_LANDMINE_LOADS:
        raise ValueError(f"At most {MAX_LANDMINE_LOADS} landmine loads")
    if any(load <= 0 or load > 100 for load in loads):
        raise ValueError("Landmine loads must be between 0 and 100 kg")
    return sorted(set(loads))


def reference_load_error(
    loads: Optional[List[float]],
    reference: Optional[float],
    tolerance: Optional[float],
) -> Optional[str]:
    """Why this landmine configuration would leave the Punch panel empty, if it would.

    `combine_engine.score_attempt` ranks a throw only when its load is within
    `tolerance` of the reference load. A reference no ladder load can reach is the
    quiet failure: every throw saves, the station chips fill, a VBT profile is
    promoted — and nothing at all reaches the board.
    """
    if not loads or reference is None:
        return None
    nearest = min(loads, key=lambda load: abs(load - reference))
    allowed = tolerance or 0
    if abs(nearest - reference) <= allowed:
        return None
    return (
        f"The reference load {reference:g} kg is not on the landmine ladder — the "
        f"nearest load is {nearest:g} kg and the tolerance is {allowed:g} kg, so no "
        "throw would be ranked on the board"
    )


# A combine is booked a season or so either side of today; anything further out is a
# typo. It matters more than it looks: both `update_event` and `rotate_share_token`
# recompute the public link's expiry from `event_date`, so "0002-09-19" — a real
# onChange while someone keyboard-edits the year — issues an already-expired link and
# 404s the board. Once an attempt exists the date is frozen at 409, so on the day it
# cannot be corrected at all. Measured in days to sidestep leap years.
EVENT_DATE_WINDOW_DAYS = 365 * 2


def validate_event_date(v: date) -> date:
    today = date.today()
    if abs((v - today).days) > EVENT_DATE_WINDOW_DAYS:
        raise ValueError(
            f"The event date must be within two years of today ({today.isoformat()})"
        )
    return v


class CombineEventBase(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=120)
    event_date: date
    venue: Optional[str] = Field(None, max_length=200)
    public_name_style: NameStyle = "full"
    show_bs_benchmark: bool = True
    show_club: bool = True
    landmine_exercise_name: str = Field("Landmine Punch Throw", max_length=100)
    landmine_loads_kg: List[float] = Field(default_factory=lambda: [10, 15, 20, 25])
    landmine_reference_load_kg: float = Field(20, gt=0, le=100)
    landmine_reference_tolerance_kg: float = Field(1.0, ge=0, le=10)
    landmine_velocity_metric: VelocityMetric = "peak"
    airbike_score_basis: AirBikeBasis = "w_per_kg"
    # Which unit the dynamometers at this event read. Values are always stored in
    # N/s; this drives the station's field labels and the conversion on the way in.
    rfd_unit: RfdUnit = "n_s"
    # Defaults to 'z' so an event created today scores exactly as one created before
    # the choice existed. Only the operator switching this changes a board.
    overall_score_basis: OverallScoreBasis = "z"
    min_stations_for_overall: int = Field(3, ge=1, le=6)
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("landmine_loads_kg")
    @classmethod
    def validate_loads(cls, v: List[float]) -> List[float]:
        return validate_landmine_loads(v)


class CombineEventCreate(CombineEventBase):
    @model_validator(mode="after")
    def check_reference_load_sits_on_the_ladder(self) -> "CombineEventCreate":
        """Refuse a ladder and a reference load that do not agree.

        Deliberately on the create model rather than on `CombineEventBase`:
        `CombineEventResponse` inherits the base, and an event row written before
        this rule existed must stay readable — otherwise the console could not open
        the event to fix it. Input is validated, responses are not (decision 22).
        """
        error = reference_load_error(
            self.landmine_loads_kg,
            self.landmine_reference_load_kg,
            self.landmine_reference_tolerance_kg,
        )
        if error:
            raise ValueError(error)
        return self

    # On create and update rather than on `CombineEventBase`, for the same reason as
    # the ladder check above: `CombineEventResponse` inherits the base, and a row
    # already stored with an odd date must stay readable or the console could not
    # open the event to fix it. Input is validated, responses are not (decision 22).
    @field_validator("event_date")
    @classmethod
    def check_event_date(cls, v: date) -> date:
        return validate_event_date(v)


class CombineEventUpdate(BaseModel):
    event_name: Optional[str] = Field(None, min_length=1, max_length=120)
    event_date: Optional[date] = None
    venue: Optional[str] = Field(None, max_length=200)
    status: Optional[EventStatus] = None
    public_name_style: Optional[NameStyle] = None
    show_bs_benchmark: Optional[bool] = None
    show_club: Optional[bool] = None
    landmine_exercise_name: Optional[str] = Field(None, max_length=100)
    landmine_loads_kg: Optional[List[float]] = None
    landmine_reference_load_kg: Optional[float] = Field(None, gt=0, le=100)
    landmine_reference_tolerance_kg: Optional[float] = Field(None, ge=0, le=10)
    landmine_velocity_metric: Optional[VelocityMetric] = None
    airbike_score_basis: Optional[AirBikeBasis] = None
    rfd_unit: Optional[RfdUnit] = None
    overall_score_basis: Optional[OverallScoreBasis] = None
    min_stations_for_overall: Optional[int] = Field(None, ge=1, le=6)
    notes: Optional[str] = Field(None, max_length=2000)
    # Explicit confirmation that these (often under-18) names may be shown on a
    # public screen. Required before the event can go live.
    public_display_consent_confirmed: Optional[bool] = None

    @field_validator("landmine_loads_kg")
    @classmethod
    def validate_loads(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        """The same ladder rules as create — a PATCH is not a way around them."""
        return None if v is None else validate_landmine_loads(v)

    @field_validator("event_date")
    @classmethod
    def check_event_date(cls, v: Optional[date]) -> Optional[date]:
        """The console guards its own date field, but it is not the only caller."""
        return None if v is None else validate_event_date(v)


class CombineEventResponse(CombineEventBase):
    id: UUID
    coach_id: UUID
    status: EventStatus
    share_token: str
    share_url_path: str
    share_token_expires_at: datetime
    share_revoked_at: Optional[datetime] = None
    public_display_consent_confirmed_at: Optional[datetime] = None
    bs_norms_updated_at: Optional[datetime] = None
    # How many Boxing Science athletes back each band, per score key per gender.
    # Counts only — a mean or an SD here would hand the reference distribution to
    # anyone who can open the console.
    bs_norms_coverage: Dict[str, Dict[str, int]] = {}
    results_updated_at: datetime
    participant_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CombineEventListItem(BaseModel):
    id: UUID
    event_name: str
    event_date: date
    venue: Optional[str] = None
    status: EventStatus
    participant_count: int = 0
    attempt_count: int = 0
    results_updated_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class ShareTokenResponse(BaseModel):
    share_token: str
    share_url_path: str
    share_token_expires_at: datetime
    share_revoked_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------


class RosterRow(BaseModel):
    """One line of a pasted roster.

    `gender` is required — the CSV upload path defaults it to "male", which is the
    wrong behaviour for a mixed-gender combine.
    """

    athlete_id: Optional[UUID] = None
    first_name: str = Field(..., min_length=1, max_length=50)
    surname: Optional[str] = Field(None, max_length=50)
    gender: Gender
    date_of_birth: Optional[date] = None
    body_mass_kg: Optional[float] = Field(None, gt=0, le=300)
    club: Optional[str] = Field(None, max_length=100)
    weight_category: Optional[str] = Field(None, max_length=40)
    age_group: Optional[str] = Field(None, max_length=40)
    squad: Optional[str] = Field(None, max_length=40)
    bib: Optional[int] = Field(None, gt=0, lt=10000)


class RosterBulkRequest(BaseModel):
    rows: List[RosterRow] = Field(..., min_length=1, max_length=200)
    on_name_match: Literal["link", "create"] = "link"


class RosterRowResult(BaseModel):
    index: int
    action: Literal["linked", "created", "skipped", "error"]
    athlete_id: Optional[UUID] = None
    participant_id: Optional[UUID] = None
    matched_name: Optional[str] = None
    bib: Optional[int] = None
    reason: Optional[str] = None


class RosterBulkResponse(BaseModel):
    dry_run: bool
    created_athletes: int
    linked_athletes: int
    participants_added: int
    results: List[RosterRowResult]


class ParticipantUpdate(BaseModel):
    bib: Optional[int] = Field(None, gt=0, lt=10000)
    club: Optional[str] = Field(None, max_length=100)
    weight_category: Optional[str] = Field(None, max_length=40)
    age_group: Optional[str] = Field(None, max_length=40)
    body_mass_kg: Optional[float] = Field(None, gt=0, le=300)
    squad: Optional[str] = Field(None, max_length=40)
    withdrawn: Optional[bool] = None

    @field_validator("weight_category")
    @classmethod
    def validate_weight_category(cls, v: Optional[str]) -> Optional[str]:
        """Strict: a typo must not create a division nobody can filter on.

        Blank is how the console clears the field, so it maps to NULL rather than
        to an error.
        """
        if v is None or not v.strip():
            return None
        normalised = normalise_weight_category(v)
        if normalised is None:
            raise ValueError(
                f"Unknown weight category '{v}'. Use one of: {', '.join(WEIGHT_CATEGORIES)}"
            )
        return normalised


class ParticipantResponse(BaseModel):
    id: UUID
    combine_event_id: UUID
    athlete_id: UUID
    name: str
    # The stored name parts, so a weigh-in edit can PATCH body mass without
    # re-splitting the display name — "Ana Maria Lopez" would come back as first
    # name "Ana" and surname "Maria Lopez".
    first_name: Optional[str] = None
    surname: Optional[str] = None
    # Carried through from the athlete record so the roster form can prefill it —
    # otherwise editing a boxer means re-picking a gender that is already known.
    gender: Optional[Gender] = None
    bib: int
    club: Optional[str] = None
    weight_category: Optional[str] = None
    age_group: Optional[str] = None
    body_mass_kg: Optional[float] = None
    squad: Optional[str] = None
    withdrawn_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Attempts — one model per station, discriminated on `station`
# ---------------------------------------------------------------------------


class CmjMeasures(BaseModel):
    station: Literal["cmj"] = "cmj"
    height_cm: float = Field(..., gt=0, le=90)


class PogoMeasures(BaseModel):
    station: Literal["pogo"] = "pogo"
    flight_time_ms: Optional[float] = Field(None, gt=0, le=1500)
    contact_time_ms: Optional[float] = Field(None, gt=0, le=1500)
    rsi: Optional[float] = Field(None, gt=0, le=10)

    @model_validator(mode="after")
    def validate_inputs(self):
        has_pair = self.flight_time_ms is not None and self.contact_time_ms is not None
        if not has_pair and self.rsi is None:
            raise ValueError("Provide flight and contact times, or an RSI value")
        return self


class LandmineMeasures(BaseModel):
    station: Literal["landmine"] = "landmine"
    load_kg: float = Field(..., gt=0, le=100)
    peak_velocity_ms: Optional[float] = Field(None, gt=0, le=10)
    mean_velocity_ms: Optional[float] = Field(None, gt=0, le=5)
    side: Optional[Literal["left", "right"]] = None

    @model_validator(mode="after")
    def validate_velocity(self):
        if self.peak_velocity_ms is None and self.mean_velocity_ms is None:
            raise ValueError("At least one velocity (peak or mean) is required")
        return self


class BilateralForceMeasures(BaseModel):
    """Shared shape for the two dynamometer stations.

    RFD is stored canonically in N/s. A station whose dynamometer reads kg/s sends
    `rfd_unit="kg_s"` and the typed numbers are converted here, keeping what the
    operator actually typed so a reading can be checked back against the device.
    `rfd_unit` is input-only: `measures` holds measurements, so the unit is
    recorded only when it changed a value.
    """

    left_kg: Optional[float] = None
    right_kg: Optional[float] = None
    # No range on the field: the bounds belong after the kg/s conversion below.
    rfd_left_n_s: Optional[float] = None
    rfd_right_n_s: Optional[float] = None
    rfd_unit: RfdUnit = Field("n_s", exclude=True)
    rfd_left_entered: Optional[float] = None
    rfd_right_entered: Optional[float] = None
    rfd_unit_entered: Optional[RfdUnit] = None

    @model_validator(mode="after")
    def convert_rfd_to_n_s(self):
        # The "as entered" fields are server-owned, so anything a client sent is
        # discarded here. A correction PATCHes back the measures it loaded, which
        # already carry `rfd_unit_entered`; letting that suppress the conversion
        # would store kg/s numbers as N/s, an order of magnitude too low. Keying
        # off `rfd_unit` alone is still idempotent because it is input-only, so a
        # re-validated dump comes back as n_s and cannot multiply by g twice.
        self.rfd_left_entered = None
        self.rfd_right_entered = None
        self.rfd_unit_entered = None
        if self.rfd_unit == "kg_s":
            for side in ("left", "right"):
                typed = getattr(self, f"rfd_{side}_n_s")
                if typed is None:
                    continue
                setattr(self, f"rfd_{side}_entered", typed)
                setattr(self, f"rfd_{side}_n_s", round(typed * KGF_TO_NEWTONS, 1))
                self.rfd_unit_entered = "kg_s"  # only when something was converted

        for key in ("rfd_left_n_s", "rfd_right_n_s"):
            value = getattr(self, key)
            if value is not None and not 0 <= value <= RFD_MAX_N_S:
                raise ValueError(f"RFD must be between 0 and {RFD_MAX_N_S} N/s")
        return self

    @model_validator(mode="after")
    def validate_sides(self):
        if self.left_kg is None and self.right_kg is None:
            raise ValueError("At least one side is required")
        return self


class GripMeasures(BilateralForceMeasures):
    station: Literal["grip"] = "grip"
    left_kg: Optional[float] = Field(None, gt=0, le=120)
    right_kg: Optional[float] = Field(None, gt=0, le=120)


class TrunkRotationMeasures(BilateralForceMeasures):
    station: Literal["trunk_rotation"] = "trunk_rotation"
    left_kg: Optional[float] = Field(None, gt=0, le=200)
    right_kg: Optional[float] = Field(None, gt=0, le=200)


class AirBikeMeasures(BaseModel):
    station: Literal["air_bike"] = "air_bike"
    sprint_number: int = Field(..., ge=1, le=2)
    power_7s: float = Field(..., gt=0, le=3000)
    power_17s: float = Field(..., gt=0, le=3000)
    power_27s: float = Field(..., gt=0, le=3000)
    blood_lactate_mmol: Optional[float] = Field(None, ge=0, le=30)


CombineMeasures = Annotated[
    Union[
        CmjMeasures,
        PogoMeasures,
        LandmineMeasures,
        GripMeasures,
        TrunkRotationMeasures,
        AirBikeMeasures,
    ],
    Field(discriminator="station"),
]


class AttemptSubmit(BaseModel):
    participant_id: UUID
    measures: CombineMeasures
    # Client-generated, so a retry or a double-tapped SAVE cannot double-insert.
    client_attempt_id: Optional[UUID] = None
    notes: Optional[str] = Field(None, max_length=200)


class AttemptUpdate(BaseModel):
    measures: Optional[CombineMeasures] = None
    notes: Optional[str] = Field(None, max_length=200)


class AttemptResponse(BaseModel):
    id: UUID
    combine_event_id: UUID
    participant_id: UUID
    station: Station
    attempt_number: int
    measures: Dict[str, Any]
    value: Optional[float] = None
    display_value: Optional[str] = None
    voided_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Station roster — "who still needs this station"
# ---------------------------------------------------------------------------


class StationRosterEntry(BaseModel):
    participant_id: UUID
    bib: int
    name: str
    club: Optional[str] = None
    weight_category: Optional[str] = None
    body_mass_kg: Optional[float] = None
    squad: Optional[str] = None
    attempt_count: int = 0
    best_value: Optional[float] = None
    best_display: Optional[str] = None
    last_attempt_at: Optional[datetime] = None
    status: Literal["todo", "done"] = "todo"


class StationRosterResponse(BaseModel):
    station: Station
    label: str
    unit: str
    total: int
    done: int
    entries: List[StationRosterEntry]


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


class CohortStats(BaseModel):
    n: int
    mean: Optional[float] = None
    median: Optional[float] = None
    sd: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None


class PublicParticipantResult(BaseModel):
    """A public row. No identifiers, no numeric benchmark z, no body mass."""

    bib: Optional[int] = None
    display_name: str
    club: Optional[str] = None
    weight_category: Optional[str] = None
    age_group: Optional[str] = None
    value: Optional[float] = None
    display_value: Optional[str] = None
    rank: Optional[int] = None
    attempts: int = 0
    z_cohort: Optional[float] = None
    bs_band: Optional[str] = None
    asymmetry_pct: Optional[float] = None
    dominant_side: Optional[str] = None
    # Landmine only: which arm threw the ranked best, so the board can show L / R.
    side: Optional[str] = None


class PublicStationPanel(BaseModel):
    station: Station
    label: str
    short_label: str
    unit: str
    decimals: int
    higher_is_better: bool
    cohort_basis: Literal["event", "filtered"]
    completed: int
    stats: CohortStats
    results: List[PublicParticipantResult]


class PublicOverallEntry(BaseModel):
    bib: Optional[int] = None
    display_name: str
    club: Optional[str] = None
    weight_category: Optional[str] = None
    combine_score: float
    stations_completed: int
    eligible: bool
    rank: Optional[int] = None


class PublicLeaderboardResponse(BaseModel):
    event_name: str
    event_date: date
    venue: Optional[str] = None
    results_updated_at: datetime
    participant_count: int
    filters: Dict[str, List[str]] = {}
    # Which composite `combine_score` carries, so the board can label the number.
    # Defaults to 'z' — a payload built before this field existed is a z board.
    score_basis: OverallScoreBasis = "z"
    stations: List[PublicStationPanel]
    overall: List[PublicOverallEntry]


class PublicEventMeta(BaseModel):
    """Cheap boot payload — no results."""

    event_name: str
    event_date: date
    venue: Optional[str] = None
    status: EventStatus
    results_updated_at: datetime
    participant_count: int


class LeaderboardResult(PublicParticipantResult):
    """Authenticated row — adds identifiers and the raw benchmark z."""

    participant_id: Optional[UUID] = None
    athlete_id: Optional[UUID] = None
    z_bs: Optional[float] = None
    detail: Dict[str, Any] = {}


class LeaderboardPanel(PublicStationPanel):
    results: List[LeaderboardResult]


class LeaderboardOverallEntry(PublicOverallEntry):
    participant_id: Optional[UUID] = None
    mean_z: Optional[float] = None


class LeaderboardResponse(BaseModel):
    event_name: str
    event_date: date
    venue: Optional[str] = None
    results_updated_at: datetime
    participant_count: int
    filters: Dict[str, List[str]] = {}
    score_basis: OverallScoreBasis = "z"
    stations: List[LeaderboardPanel]
    overall: List[LeaderboardOverallEntry]
    unsynced_count: int = 0
