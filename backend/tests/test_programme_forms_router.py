"""Tests for programme forms router."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

PATCH_PATH = "app.core.supabase_client.get_supabase_client"
COACH_ID = "00000000-0000-0000-0000-000000000001"

SAMPLE_FORM_ID = str(uuid4())
SAMPLE_ATHLETE_ID = str(uuid4())
SAMPLE_ATHLETE_ID_2 = str(uuid4())


def _make_form(form_id=None, coach_id=COACH_ID):
    return {
        "id": form_id or str(uuid4()),
        "coach_id": coach_id,
        "form_name": "Upper Body Programme",
        "description": "4-week upper body",
        "num_weeks": 4,
        "sessions_per_week": 2,
        "form_data": {
            "sessions": [
                {
                    "sections": [
                        {
                            "type": "strength",
                            "exercises": [
                                {
                                    "exercise_name": "Bench Press",
                                    "exercise_category": "Strength",
                                    "progressive": True,
                                    "weeks": [
                                        {"sets": 3, "reps": "8", "weight_kg": 60},
                                        {"sets": 3, "reps": "6", "weight_kg": 70},
                                        {"sets": 4, "reps": "4", "weight_kg": 80},
                                        {"sets": 4, "reps": "3", "weight_kg": 85},
                                    ],
                                }
                            ],
                        }
                    ]
                },
                {
                    "sections": [
                        {
                            "type": "accessory",
                            "exercises": [
                                {
                                    "exercise_name": "Lateral Raise",
                                    "description": "3x12",
                                }
                            ],
                        }
                    ]
                },
            ]
        },
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _make_athlete(athlete_id=None, coach_id=COACH_ID):
    return {
        "id": athlete_id or str(uuid4()),
        "coach_id": coach_id,
        "first_name": "John",
        "surname": "Doe",
    }


def _chain_mock(mock_client, data=None, side_effect=None):
    """Set up a fully chained mock for Supabase queries."""
    table_mock = MagicMock()
    mock_client.table.return_value = table_mock
    table_mock.select.return_value = table_mock
    table_mock.eq.return_value = table_mock
    table_mock.ilike.return_value = table_mock
    table_mock.in_.return_value = table_mock
    table_mock.order.return_value = table_mock
    table_mock.limit.return_value = table_mock
    table_mock.insert.return_value = table_mock
    table_mock.update.return_value = table_mock
    table_mock.delete.return_value = table_mock
    table_mock.upsert.return_value = table_mock

    resp = MagicMock()
    if side_effect:
        table_mock.execute.side_effect = side_effect
    else:
        resp.data = data or []
        table_mock.execute.return_value = resp
    return table_mock


# ──────────────────────────────────────────────────────────
# CRUD Tests
# ──────────────────────────────────────────────────────────


class TestCreateForm:
    def test_create_form_success(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = _make_form()
            _chain_mock(mock_client, data=[form])

            resp = client.post(
                "/api/v1/programme-forms/",
                json={
                    "form_name": "Upper Body Programme",
                    "description": "4-week upper body",
                    "num_weeks": 4,
                    "sessions_per_week": 2,
                },
            )
            assert resp.status_code == 201
            assert resp.json()["form_name"] == "Upper Body Programme"

    def test_create_form_duplicate_409(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = Exception(
                "duplicate key value violates unique constraint"
            )

            resp = client.post(
                "/api/v1/programme-forms/",
                json={"form_name": "Existing Form", "num_weeks": 4},
            )
            assert resp.status_code == 409

    def test_create_form_athlete_denied_403(self, athlete_client):
        resp = athlete_client.post(
            "/api/v1/programme-forms/",
            json={"form_name": "Test", "num_weeks": 4},
        )
        assert resp.status_code == 403

    def test_create_form_empty_name_422(self):
        resp = client.post(
            "/api/v1/programme-forms/",
            json={"form_name": "  ", "num_weeks": 4},
        )
        assert resp.status_code == 422


class TestListForms:
    def test_list_forms_success(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            forms = [_make_form(), _make_form(form_id=str(uuid4()))]
            _chain_mock(mock_client, data=forms)

            resp = client.get("/api/v1/programme-forms/")
            assert resp.status_code == 200
            assert len(resp.json()) == 2


class TestGetForm:
    def test_get_form_success(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = _make_form(form_id=SAMPLE_FORM_ID)
            _chain_mock(mock_client, data=[form])

            resp = client.get(f"/api/v1/programme-forms/{SAMPLE_FORM_ID}")
            assert resp.status_code == 200
            assert resp.json()["form_name"] == "Upper Body Programme"

    def test_get_form_not_found_404(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.get(f"/api/v1/programme-forms/{uuid4()}")
            assert resp.status_code == 404


class TestUpdateForm:
    def test_update_form_success(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = _make_form(form_id=SAMPLE_FORM_ID)
            updated_form = {**form, "form_name": "Updated Name"}

            ownership_resp = MagicMock()
            ownership_resp.data = [form]
            update_resp = MagicMock()
            update_resp.data = [updated_form]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [ownership_resp, update_resp]

            resp = client.patch(
                f"/api/v1/programme-forms/{SAMPLE_FORM_ID}",
                json={"form_name": "Updated Name"},
            )
            assert resp.status_code == 200
            assert resp.json()["form_name"] == "Updated Name"

    def test_update_form_not_found_404(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.patch(
                f"/api/v1/programme-forms/{uuid4()}",
                json={"form_name": "Updated"},
            )
            assert resp.status_code == 404


class TestDeleteForm:
    def test_delete_form_success(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = _make_form(form_id=SAMPLE_FORM_ID)
            ownership_resp = MagicMock()
            ownership_resp.data = [form]
            delete_resp = MagicMock()
            delete_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [ownership_resp, delete_resp]

            resp = client.delete(f"/api/v1/programme-forms/{SAMPLE_FORM_ID}")
            assert resp.status_code == 204

    def test_delete_form_not_found_404(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.delete(f"/api/v1/programme-forms/{uuid4()}")
            assert resp.status_code == 404


# ──────────────────────────────────────────────────────────
# Apply Tests
# ──────────────────────────────────────────────────────────


class TestApplyForm:
    def test_apply_form_success(self):
        """Apply a form with 2 sessions, 4 weeks, 1 athlete -> 8 sessions created."""
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = _make_form(form_id=SAMPLE_FORM_ID)
            athlete = _make_athlete(SAMPLE_ATHLETE_ID)

            # 4 weeks × 2 sessions = 8 sessions
            created_sessions = [
                {"id": str(uuid4()), "athlete_id": SAMPLE_ATHLETE_ID}
                for _ in range(8)
            ]

            form_resp = MagicMock()
            form_resp.data = [form]
            athletes_resp = MagicMock()
            athletes_resp.data = [athlete]
            sessions_insert_resp = MagicMock()
            sessions_insert_resp.data = created_sessions
            prescriptions_resp = MagicMock()
            prescriptions_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [
                form_resp,           # verify form ownership
                athletes_resp,       # verify athletes
                sessions_insert_resp,  # bulk insert sessions
                prescriptions_resp,  # bulk insert prescriptions
            ]

            resp = client.post(
                f"/api/v1/programme-forms/{SAMPLE_FORM_ID}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",  # Monday
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["created_count"] == 8
            assert data["sessions_per_athlete"] == 8

    def test_apply_form_no_sessions_400(self):
        """Form with empty sessions list -> 400."""
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = _make_form(form_id=SAMPLE_FORM_ID)
            form["form_data"] = {"sessions": []}

            form_resp = MagicMock()
            form_resp.data = [form]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [form_resp]

            resp = client.post(
                f"/api/v1/programme-forms/{SAMPLE_FORM_ID}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 400
            assert "no sessions" in resp.json()["detail"]

    def test_apply_form_start_date_not_monday_422(self):
        resp = client.post(
            f"/api/v1/programme-forms/{SAMPLE_FORM_ID}/apply",
            json={
                "athlete_ids": [SAMPLE_ATHLETE_ID],
                "start_date": "2026-03-17",  # Tuesday
            },
        )
        assert resp.status_code == 422

    def test_apply_form_athlete_not_found_400(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = _make_form(form_id=SAMPLE_FORM_ID)

            form_resp = MagicMock()
            form_resp.data = [form]
            athletes_resp = MagicMock()
            athletes_resp.data = []  # No athletes found

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [form_resp, athletes_resp]

            resp = client.post(
                f"/api/v1/programme-forms/{SAMPLE_FORM_ID}/apply",
                json={
                    "athlete_ids": [str(uuid4())],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 400

    def test_apply_form_not_found_404(self):
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.post(
                f"/api/v1/programme-forms/{uuid4()}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 404

    def test_apply_form_with_progressive_exercises(self):
        """Progressive exercises: week 1 has sets=3 reps='8', verify set expansion."""
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = {
                "id": SAMPLE_FORM_ID,
                "coach_id": COACH_ID,
                "form_name": "Progressive Test",
                "description": None,
                "num_weeks": 2,
                "sessions_per_week": 1,
                "form_data": {
                    "sessions": [
                        {
                            "sections": [
                                {
                                    "type": "strength",
                                    "exercises": [
                                        {
                                            "exercise_name": "Squat",
                                            "exercise_category": "Strength",
                                            "progressive": True,
                                            "weeks": [
                                                {"sets": 3, "reps": "8", "weight_kg": 60},
                                                {"sets": 4, "reps": "6", "weight_kg": 70},
                                            ],
                                        }
                                    ],
                                }
                            ]
                        }
                    ]
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            athlete = _make_athlete(SAMPLE_ATHLETE_ID)
            # 2 weeks × 1 session = 2 sessions
            created_sessions = [
                {"id": str(uuid4()), "athlete_id": SAMPLE_ATHLETE_ID}
                for _ in range(2)
            ]

            form_resp = MagicMock()
            form_resp.data = [form]
            athletes_resp = MagicMock()
            athletes_resp.data = [athlete]
            sessions_resp = MagicMock()
            sessions_resp.data = created_sessions
            prescriptions_resp = MagicMock()
            prescriptions_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [
                form_resp,
                athletes_resp,
                sessions_resp,
                prescriptions_resp,
            ]

            # Capture inserted prescriptions
            inserted_prescriptions = []
            original_insert = table_mock.insert

            def capture_insert(rows):
                if isinstance(rows, list) and rows and "exercise_name" in rows[0]:
                    inserted_prescriptions.extend(rows)
                return table_mock

            table_mock.insert.side_effect = capture_insert

            resp = client.post(
                f"/api/v1/programme-forms/{SAMPLE_FORM_ID}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["created_count"] == 2

            # Week 1: 3 sets expanded = 3 rows, Week 2: 4 sets = 4 rows = 7 total
            assert len(inserted_prescriptions) == 7

            # Check week 1 prescriptions (first 3)
            week1_rows = [p for p in inserted_prescriptions[:3]]
            assert all(p["reps"] == 8 for p in week1_rows)
            assert all(p["recommended_weight_kg"] == 60 for p in week1_rows)

            # Check week 2 prescriptions (next 4)
            week2_rows = [p for p in inserted_prescriptions[3:]]
            assert all(p["reps"] == 6 for p in week2_rows)
            assert all(p["recommended_weight_kg"] == 70 for p in week2_rows)

    def test_apply_form_with_core_circuit(self):
        """Core circuit: 2 exercises × 3 circuit_sets = 6 interleaved rows."""
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = {
                "id": SAMPLE_FORM_ID,
                "coach_id": COACH_ID,
                "form_name": "Circuit Test",
                "description": None,
                "num_weeks": 1,
                "sessions_per_week": 1,
                "form_data": {
                    "sessions": [
                        {
                            "sections": [
                                {
                                    "type": "core_circuit",
                                    "circuit_sets": 3,
                                    "exercises": [
                                        {
                                            "exercise_name": "Plank",
                                            "description": "30s",
                                        },
                                        {
                                            "exercise_name": "Russian Twist",
                                            "description": "20",
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            athlete = _make_athlete(SAMPLE_ATHLETE_ID)
            created_sessions = [
                {"id": str(uuid4()), "athlete_id": SAMPLE_ATHLETE_ID}
            ]

            form_resp = MagicMock()
            form_resp.data = [form]
            athletes_resp = MagicMock()
            athletes_resp.data = [athlete]
            sessions_resp = MagicMock()
            sessions_resp.data = created_sessions
            prescriptions_resp = MagicMock()
            prescriptions_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [
                form_resp,
                athletes_resp,
                sessions_resp,
                prescriptions_resp,
            ]

            inserted_prescriptions = []

            def capture_insert(rows):
                if isinstance(rows, list) and rows and "exercise_name" in rows[0]:
                    inserted_prescriptions.extend(rows)
                return table_mock

            table_mock.insert.side_effect = capture_insert

            resp = client.post(
                f"/api/v1/programme-forms/{SAMPLE_FORM_ID}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 200

            # 3 rounds × 2 exercises = 6 interleaved rows
            circuit_rows = [
                p for p in inserted_prescriptions if p.get("exercise_category") == "Circuit"
            ]
            assert len(circuit_rows) == 6

            # Verify interleaving: Plank, Russian Twist, Plank, Russian Twist, ...
            names = [p["exercise_name"] for p in circuit_rows]
            assert names == ["Plank", "Russian Twist"] * 3

            # All should have section_type = core_circuit
            assert all(p["section_type"] == "core_circuit" for p in circuit_rows)

    def test_apply_form_with_simple_exercises(self):
        """Simple (non-progressive) exercises: 1 prescription row each."""
        with patch(PATCH_PATH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            form = {
                "id": SAMPLE_FORM_ID,
                "coach_id": COACH_ID,
                "form_name": "Simple Test",
                "description": None,
                "num_weeks": 1,
                "sessions_per_week": 1,
                "form_data": {
                    "sessions": [
                        {
                            "sections": [
                                {
                                    "type": "accessory",
                                    "exercises": [
                                        {
                                            "exercise_name": "Bicep Curl",
                                            "description": "3x12",
                                        },
                                        {
                                            "exercise_name": "Tricep Extension",
                                            "description": "4+4",
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                },
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            athlete = _make_athlete(SAMPLE_ATHLETE_ID)
            created_sessions = [
                {"id": str(uuid4()), "athlete_id": SAMPLE_ATHLETE_ID}
            ]

            form_resp = MagicMock()
            form_resp.data = [form]
            athletes_resp = MagicMock()
            athletes_resp.data = [athlete]
            sessions_resp = MagicMock()
            sessions_resp.data = created_sessions
            prescriptions_resp = MagicMock()
            prescriptions_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [
                form_resp,
                athletes_resp,
                sessions_resp,
                prescriptions_resp,
            ]

            inserted_prescriptions = []

            def capture_insert(rows):
                if isinstance(rows, list) and rows and "exercise_name" in rows[0]:
                    inserted_prescriptions.extend(rows)
                return table_mock

            table_mock.insert.side_effect = capture_insert

            resp = client.post(
                f"/api/v1/programme-forms/{SAMPLE_FORM_ID}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 200

            # 2 simple exercises = 2 rows
            assert len(inserted_prescriptions) == 2

            # First exercise: "3x12" - not a pure integer, so reps=None
            assert inserted_prescriptions[0]["exercise_name"] == "Bicep Curl"
            assert inserted_prescriptions[0]["reps_text"] == "3x12"
            assert "reps" not in inserted_prescriptions[0]  # filtered by filter_none

            # Second exercise: "4+4" - not a pure integer, so reps=None
            assert inserted_prescriptions[1]["exercise_name"] == "Tricep Extension"
            assert inserted_prescriptions[1]["reps_text"] == "4+4"
            assert "reps" not in inserted_prescriptions[1]

            # Both should have section_type
            assert all(p["section_type"] == "accessory" for p in inserted_prescriptions)
