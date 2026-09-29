"""Tests for batch session assignment endpoint."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BATCH_URL = "/api/v1/training/sessions/batch"


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


def _make_session(athlete_id: str) -> dict:
    """Helper to create a fake session response row."""
    return {
        "id": str(uuid4()),
        "athlete_id": athlete_id,
        "session_date": "2024-06-01",
        "training_type": "Strength",
        "duration_minutes": None,
        "rpe": None,
        "srpe": None,
        "notes": None,
        "metrics": {},
        "status": "assigned",
        "created_by": str(uuid4()),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _setup_batch_mocks(
    mock_supabase,
    athlete_ids: list[str],
    found_athlete_ids: list[str] | None = None,
    template_data: dict | None = None,
    template_exercises: list[dict] | None = None,
    created_sessions: list[dict] | None = None,
):
    """
    Configure mock_supabase.table() to return appropriate mocks
    for each table accessed in batch_assign_sessions.

    Tables accessed in order:
      1. session_templates (select, eq, eq, execute)
      2. athletes (select, eq, in_, execute)
      3. template_exercises (select, eq, order, execute)
      4. training_sessions (insert, execute)
      5. exercise_prescriptions (insert, execute) — only if template has exercises

    Returns a dict of table_name -> mock_table for assertions.
    """
    if found_athlete_ids is None:
        found_athlete_ids = athlete_ids
    if template_data is None:
        template_data = {
            "id": str(uuid4()),
            "coach_id": str(uuid4()),
            "template_name": "Test Template",
            "training_type": "Strength",
        }
    if template_exercises is None:
        template_exercises = []
    if created_sessions is None:
        created_sessions = [_make_session(aid) for aid in athlete_ids]

    # Store table mocks so tests can inspect them after the call
    table_mocks = {}

    def table_side_effect(table_name):
        mock_table = MagicMock()

        if table_name == "session_templates":
            mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = (
                [template_data] if template_data != "NOT_FOUND" else []
            )
        elif table_name == "athletes":
            mock_table.select.return_value.eq.return_value.in_.return_value.execute.return_value.data = [
                {"id": aid} for aid in found_athlete_ids
            ]
        elif table_name == "template_exercises":
            mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
                template_exercises
            )
        elif table_name == "training_sessions":
            mock_table.insert.return_value.execute.return_value.data = created_sessions
        elif table_name == "exercise_prescriptions":
            mock_table.insert.return_value.execute.return_value.data = []

        table_mocks[table_name] = mock_table
        return mock_table

    mock_supabase.table.side_effect = table_side_effect
    return table_mocks


class TestBatchAssignSuccess:
    """Tests for successful batch assignment."""

    def test_batch_assign_success(self, mock_supabase):
        """3 athletes, template with 2 exercises (3 sets each) -> 18 prescription rows."""
        athlete_ids = [str(uuid4()) for _ in range(3)]
        template_id = str(uuid4())
        template_exercises = [
            {
                "exercise_name": "Back Squat",
                "exercise_category": "Strength",
                "sets": 3,
                "reps": 5,
                "weight_kg": 100,
                "tempo": "3010",
                "rest_seconds": 120,
                "duration_seconds": None,
                "distance_meters": None,
            },
            {
                "exercise_name": "Bench Press",
                "exercise_category": "Strength",
                "sets": 3,
                "reps": 8,
                "weight_kg": 80,
                "tempo": "2010",
                "rest_seconds": 90,
                "duration_seconds": None,
                "distance_meters": None,
            },
        ]
        created_sessions = [_make_session(aid) for aid in athlete_ids]

        table_mocks = _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            template_exercises=template_exercises,
            created_sessions=created_sessions,
        )

        response = client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["created_count"] == 3
        assert len(data["sessions"]) == 3

        # Verify prescriptions insert was called with 18 rows (3 athletes x 2 exercises x 3 sets)
        assert "exercise_prescriptions" in table_mocks
        ep_table = table_mocks["exercise_prescriptions"]
        insert_call = ep_table.insert.call_args
        inserted_rows = insert_call[0][0]
        assert len(inserted_rows) == 18

    def test_batch_assign_single_athlete(self, mock_supabase):
        """Batch of 1 athlete works fine."""
        athlete_ids = [str(uuid4())]
        template_id = str(uuid4())
        created_sessions = [_make_session(athlete_ids[0])]

        _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            template_exercises=[],
            created_sessions=created_sessions,
        )

        response = client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["created_count"] == 1
        assert len(data["sessions"]) == 1

    def test_batch_assign_with_notes(self, mock_supabase):
        """Notes string is included in session rows."""
        athlete_ids = [str(uuid4())]
        template_id = str(uuid4())
        session_with_notes = _make_session(athlete_ids[0])
        session_with_notes["notes"] = "Focus on technique"

        table_mocks = _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            template_exercises=[],
            created_sessions=[session_with_notes],
        )

        response = client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
                "notes": "Focus on technique",
            },
        )

        assert response.status_code == 201

        # Verify the insert was called with notes in session rows
        assert "training_sessions" in table_mocks
        ts_table = table_mocks["training_sessions"]
        insert_call = ts_table.insert.call_args
        inserted_rows = insert_call[0][0]
        assert inserted_rows[0]["notes"] == "Focus on technique"

    def test_batch_assign_empty_template(self, mock_supabase):
        """Template with no exercises: sessions created, prescriptions NOT inserted."""
        athlete_ids = [str(uuid4()), str(uuid4())]
        template_id = str(uuid4())
        created_sessions = [_make_session(aid) for aid in athlete_ids]

        _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            template_exercises=[],
            created_sessions=created_sessions,
        )

        response = client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["created_count"] == 2

        # Verify exercise_prescriptions table was NOT accessed
        calls = mock_supabase.table.call_args_list
        prescription_calls = [c for c in calls if c[0][0] == "exercise_prescriptions"]
        assert len(prescription_calls) == 0

    def test_batch_assign_admin_success(self, mock_supabase, admin_client):
        """Admin can batch-assign sessions."""
        athlete_ids = [str(uuid4())]
        template_id = str(uuid4())
        created_sessions = [_make_session(athlete_ids[0])]

        _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            template_exercises=[],
            created_sessions=created_sessions,
        )

        response = admin_client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["created_count"] == 1


class TestBatchAssignErrors:
    """Tests for error cases in batch assignment."""

    def test_batch_assign_template_not_found(self, mock_supabase):
        """Template query returns empty -> 404."""
        athlete_ids = [str(uuid4())]
        template_id = str(uuid4())

        _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            template_data="NOT_FOUND",
        )

        response = client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]

    def test_batch_assign_athlete_not_owned(self, mock_supabase):
        """3 athletes requested, only 2 found -> 400."""
        athlete_ids = [str(uuid4()) for _ in range(3)]
        template_id = str(uuid4())

        # Only first 2 athletes found
        _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            found_athlete_ids=athlete_ids[:2],
        )

        response = client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 400
        assert "not found or not owned" in response.json()["detail"]

    def test_batch_assign_all_athletes_not_owned(self, mock_supabase):
        """All athletes fail ownership -> 400."""
        athlete_ids = [str(uuid4()) for _ in range(3)]
        template_id = str(uuid4())

        _setup_batch_mocks(
            mock_supabase,
            athlete_ids=athlete_ids,
            found_athlete_ids=[],
        )

        response = client.post(
            BATCH_URL,
            json={
                "template_id": template_id,
                "athlete_ids": athlete_ids,
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 400
        assert "not found or not owned" in response.json()["detail"]

    def test_batch_assign_no_database(self):
        """get_supabase_client returns None -> 503."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                BATCH_URL,
                json={
                    "template_id": str(uuid4()),
                    "athlete_ids": [str(uuid4())],
                    "session_date": "2024-06-01",
                },
            )

        assert response.status_code == 503

    def test_batch_assign_athlete_role_forbidden(self, mock_supabase, athlete_client):
        """Athlete role -> 403."""
        response = athlete_client.post(
            BATCH_URL,
            json={
                "template_id": str(uuid4()),
                "athlete_ids": [str(uuid4())],
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 403


class TestBatchAssignValidation:
    """Tests for schema validation."""

    def test_batch_assign_duplicate_athlete_ids(self):
        """Pydantic validator rejects duplicates -> 422."""
        dup_id = str(uuid4())
        response = client.post(
            BATCH_URL,
            json={
                "template_id": str(uuid4()),
                "athlete_ids": [dup_id, dup_id],
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 422

    def test_batch_assign_empty_athlete_list(self):
        """Empty list -> 422."""
        response = client.post(
            BATCH_URL,
            json={
                "template_id": str(uuid4()),
                "athlete_ids": [],
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 422

    def test_schema_max_athletes(self):
        """>50 athlete_ids -> 422."""
        response = client.post(
            BATCH_URL,
            json={
                "template_id": str(uuid4()),
                "athlete_ids": [str(uuid4()) for _ in range(51)],
                "session_date": "2024-06-01",
            },
        )

        assert response.status_code == 422

    def test_schema_notes_max_length(self):
        """Notes >1000 chars -> 422."""
        response = client.post(
            BATCH_URL,
            json={
                "template_id": str(uuid4()),
                "athlete_ids": [str(uuid4())],
                "session_date": "2024-06-01",
                "notes": "x" * 1001,
            },
        )

        assert response.status_code == 422
