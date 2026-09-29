"""Tests for Pydantic schemas."""

from datetime import date, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.athlete import AthleteCreate, AthleteResponse, AthleteUpdate
from app.schemas.enums import Gender, UserRole
from app.schemas.performance_event import (
    PerformanceEventCreate,
    PerformanceEventResponse,
    PerformanceEventUpdate,
)


class TestEnums:
    """Test enum definitions."""

    def test_gender_values(self):
        """Gender enum should have male and female values."""
        assert Gender.MALE.value == "male"
        assert Gender.FEMALE.value == "female"

    def test_user_role_values(self):
        """UserRole enum should have coach and admin values."""
        assert UserRole.COACH.value == "coach"
        assert UserRole.ADMIN.value == "admin"


class TestAthleteCreate:
    """Test AthleteCreate schema."""

    def test_valid_athlete(self):
        """Should accept valid athlete data."""
        athlete = AthleteCreate(
            name="John Doe",
            gender=Gender.MALE,
            date_of_birth=date(1990, 5, 15),
        )
        assert athlete.name == "John Doe"
        assert athlete.gender == Gender.MALE
        assert athlete.date_of_birth == date(1990, 5, 15)

    def test_minimal_athlete(self):
        """Should accept minimal required fields."""
        athlete = AthleteCreate(name="Jane", gender=Gender.FEMALE)
        assert athlete.name == "Jane"
        assert athlete.gender == Gender.FEMALE
        assert athlete.date_of_birth is None

    def test_empty_name_rejected(self):
        """Should reject empty name."""
        with pytest.raises(ValidationError) as exc_info:
            AthleteCreate(name="", gender=Gender.MALE)
        assert "String should have at least 1 character" in str(exc_info.value)

    def test_long_name_rejected(self):
        """Should reject names over 100 characters."""
        with pytest.raises(ValidationError) as exc_info:
            AthleteCreate(name="x" * 101, gender=Gender.MALE)
        assert "String should have at most 100 characters" in str(exc_info.value)

    def test_invalid_gender_rejected(self):
        """Should reject invalid gender values."""
        with pytest.raises(ValidationError):
            AthleteCreate(name="Test", gender="invalid")


class TestAthleteUpdate:
    """Test AthleteUpdate schema."""

    def test_all_fields_optional(self):
        """All fields should be optional for updates."""
        update = AthleteUpdate()
        assert update.name is None
        assert update.gender is None
        assert update.date_of_birth is None

    def test_partial_update(self):
        """Should accept partial updates."""
        update = AthleteUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.gender is None


class TestAthleteResponse:
    """Test AthleteResponse schema."""

    def test_valid_response(self):
        """Should accept valid response data."""
        now = datetime.now()
        athlete = AthleteResponse(
            id=uuid4(),
            coach_id=uuid4(),
            name="Test Athlete",
            gender=Gender.MALE,
            date_of_birth=date(1995, 1, 1),
            created_at=now,
            updated_at=now,
        )
        assert isinstance(athlete.id, UUID)
        assert isinstance(athlete.coach_id, UUID)


class TestPerformanceEventCreate:
    """Test PerformanceEventCreate schema."""

    def test_valid_event(self):
        """Should accept valid event data."""
        event = PerformanceEventCreate(
            athlete_id=uuid4(),
            event_date=date(2024, 1, 15),
            metrics={"test_type": "CMJ", "height_cm": 45.5, "body_mass_kg": 75.0},
        )
        assert event.event_date == date(2024, 1, 15)
        assert event.metrics["test_type"] == "CMJ"
        assert event.metrics["height_cm"] == 45.5

    def test_empty_metrics_rejected(self):
        """Should accept empty metrics dict (valid JSONB)."""
        event = PerformanceEventCreate(
            athlete_id=uuid4(),
            event_date=date(2024, 1, 15),
            metrics={},
        )
        assert event.metrics == {}

    def test_all_metrics_accepted(self):
        """Should accept all valid metric keys."""
        event = PerformanceEventCreate(
            athlete_id=uuid4(),
            event_date=date(2024, 1, 15),
            metrics={
                "test_type": "CMJ",
                "height_cm": 45.5,
                "sj_height_cm": 35.0,
                "eur_cm": 10.5,
                "rsi": 2.21,
                "flight_time_ms": 450.0,
                "contraction_time_ms": 200.0,
                "body_mass_kg": 72.0,
            },
        )
        assert len(event.metrics) == 8
        assert event.metrics["height_cm"] == 45.5
        assert event.metrics["rsi"] == 2.21


class TestPerformanceEventUpdate:
    """Test PerformanceEventUpdate schema."""

    def test_all_fields_optional(self):
        """All fields should be optional for updates."""
        update = PerformanceEventUpdate()
        assert update.event_date is None
        assert update.metrics is None

    def test_partial_update(self):
        """Should accept partial updates."""
        update = PerformanceEventUpdate(
            metrics={"height_cm": 46.0},
        )
        assert update.metrics["height_cm"] == 46.0


class TestPerformanceEventResponse:
    """Test PerformanceEventResponse schema."""

    def test_valid_response(self):
        """Should accept valid response data."""
        now = datetime.now()
        event = PerformanceEventResponse(
            id=uuid4(),
            athlete_id=uuid4(),
            event_date=date(2024, 1, 15),
            metrics={"test_type": "CMJ", "height_cm": 45.5},
            created_at=now,
            updated_at=now,
        )
        assert isinstance(event.id, UUID)
        assert isinstance(event.athlete_id, UUID)
        assert event.metrics["test_type"] == "CMJ"
