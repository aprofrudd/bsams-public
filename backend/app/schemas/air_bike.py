"""Air bike sprint test schemas.

Two split schemes are supported:
  - '7_14_27' — the original 30s sprint test (power at 7s, 14s, 27s)
  - '7_17_27' — the combine / roadmap protocol (power at 7s, 17s, 27s)

A sprint carries the 7s and 27s splits plus exactly one mid split. Existing callers
that send `power_14s` are unaffected: `split_scheme` defaults to '7_14_27'.
"""

from datetime import date, datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

SplitScheme = Literal["7_14_27", "7_17_27"]

DEFAULT_SPLIT_SCHEME: SplitScheme = "7_14_27"


class AirBikeSprintCreate(BaseModel):
    """Schema for creating an air bike sprint (one of 2 sprints)."""

    sprint_number: int = Field(..., ge=1, le=2)
    power_7s: float = Field(..., gt=0, le=5000)
    power_14s: Optional[float] = Field(None, gt=0, le=5000)
    power_17s: Optional[float] = Field(None, gt=0, le=5000)
    power_27s: float = Field(..., gt=0, le=5000)
    blood_lactate_mmol: Optional[float] = Field(None, ge=0, le=30)

    @model_validator(mode="after")
    def validate_mid_split(self):
        """Exactly one mid split must be present — it defines the protocol used."""
        if self.power_14s is None and self.power_17s is None:
            raise ValueError("A mid split is required: provide power_14s or power_17s")
        if self.power_14s is not None and self.power_17s is not None:
            raise ValueError("Provide only one mid split: power_14s or power_17s, not both")
        return self

    @property
    def split_scheme(self) -> SplitScheme:
        return "7_14_27" if self.power_14s is not None else "7_17_27"

    @property
    def power_mid(self) -> float:
        return self.power_14s if self.power_14s is not None else self.power_17s


class AirBikeSprintResponse(BaseModel):
    """Schema for air bike sprint responses.

    Both mid splits are Optional: rows created under either protocol leave the other NULL.
    """

    id: UUID
    test_id: UUID
    sprint_number: int
    power_7s: float
    power_14s: Optional[float] = None
    power_17s: Optional[float] = None
    power_27s: float
    blood_lactate_mmol: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


def _validate_sprints(sprints: Optional[List[AirBikeSprintCreate]]) -> None:
    """Sprint numbers must be unique and every sprint must use the same split scheme."""
    if not sprints:
        return
    numbers = [s.sprint_number for s in sprints]
    if len(numbers) != len(set(numbers)):
        raise ValueError("Sprint numbers must be unique")
    schemes = {s.split_scheme for s in sprints}
    if len(schemes) > 1:
        raise ValueError("All sprints in a test must use the same split scheme")


class AirBikeTestCreate(BaseModel):
    """Schema for creating an air bike test with nested sprints."""

    test_date: date
    body_mass_kg: float = Field(..., gt=0, le=300)
    notes: Optional[str] = Field(None, max_length=2000)
    sprints: List[AirBikeSprintCreate] = Field(..., min_length=1, max_length=2)

    @model_validator(mode="after")
    def validate_sprint_numbers(self):
        _validate_sprints(self.sprints)
        return self

    @property
    def split_scheme(self) -> SplitScheme:
        return self.sprints[0].split_scheme if self.sprints else DEFAULT_SPLIT_SCHEME


class AirBikeTestUpdate(BaseModel):
    """Schema for updating an air bike test."""

    test_date: Optional[date] = None
    body_mass_kg: Optional[float] = Field(None, gt=0, le=300)
    notes: Optional[str] = Field(None, max_length=2000)
    sprints: Optional[List[AirBikeSprintCreate]] = Field(None, min_length=1, max_length=2)

    @model_validator(mode="after")
    def validate_sprint_numbers(self):
        _validate_sprints(self.sprints)
        return self

    @property
    def split_scheme(self) -> Optional[SplitScheme]:
        return self.sprints[0].split_scheme if self.sprints else None


class AirBikeTestResponse(BaseModel):
    """Schema for air bike test responses with sprints."""

    id: UUID
    athlete_id: UUID
    test_date: date
    body_mass_kg: float
    split_scheme: SplitScheme = DEFAULT_SPLIT_SCHEME
    notes: Optional[str] = None
    sprints: List[AirBikeSprintResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AirBikeTestListItem(BaseModel):
    """Compact test item for list views (no full sprints)."""

    id: UUID
    athlete_id: UUID
    test_date: date
    body_mass_kg: float
    split_scheme: SplitScheme = DEFAULT_SPLIT_SCHEME
    notes: Optional[str] = None
    sprint_count: int = 0
    max_power_w: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
