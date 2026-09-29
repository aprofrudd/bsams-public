"""Tests for training blocks router."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BLOCKS_PATCH = "app.core.supabase_client.get_supabase_client"
COACH_ID = "00000000-0000-0000-0000-000000000001"

SAMPLE_BLOCK_ID = str(uuid4())
SAMPLE_SESSION_ID = str(uuid4())
SAMPLE_ATHLETE_ID = str(uuid4())
SAMPLE_ATHLETE_ID_2 = str(uuid4())


def _make_block(block_id=None, coach_id=COACH_ID):
    return {
        "id": block_id or str(uuid4()),
        "coach_id": coach_id,
        "block_name": "4-Week Strength Block",
        "description": "Progressive overload strength",
        "num_weeks": 4,
        "category": "Strength",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _make_block_session(session_id=None, block_id=SAMPLE_BLOCK_ID):
    return {
        "id": session_id or str(uuid4()),
        "block_id": block_id,
        "week_number": 1,
        "day_of_week": 1,
        "session_name": "Strength 1",
        "training_type": "Strength",
        "notes": None,
        "exercises": [
            {
                "exercise_name": "Back Squat",
                "exercise_category": "Strength",
                "order_index": 1,
                "sets": 5,
                "reps": 5,
                "percent_1rm": 75.0,
            }
        ],
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
# Block CRUD Tests
# ──────────────────────────────────────────────────────────


class TestCreateBlock:
    def test_create_block_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block()
            _chain_mock(mock_client, data=[block])

            resp = client.post(
                "/api/v1/training-blocks/",
                json={
                    "block_name": "4-Week Strength Block",
                    "description": "Progressive overload strength",
                    "num_weeks": 4,
                    "category": "Strength",
                },
            )
            assert resp.status_code == 201
            assert resp.json()["block_name"] == "4-Week Strength Block"

    def test_create_block_empty_name_422(self):
        resp = client.post(
            "/api/v1/training-blocks/",
            json={"block_name": "  ", "num_weeks": 4},
        )
        assert resp.status_code == 422

    def test_create_block_num_weeks_too_high_422(self):
        resp = client.post(
            "/api/v1/training-blocks/",
            json={"block_name": "Test", "num_weeks": 20},
        )
        assert resp.status_code == 422

    def test_create_block_duplicate_409(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = Exception(
                "duplicate key value violates unique constraint"
            )

            resp = client.post(
                "/api/v1/training-blocks/",
                json={"block_name": "Existing Block", "num_weeks": 4},
            )
            assert resp.status_code == 409

    def test_create_block_athlete_403(self, athlete_client):
        resp = athlete_client.post(
            "/api/v1/training-blocks/",
            json={"block_name": "Test", "num_weeks": 4},
        )
        assert resp.status_code == 403


class TestListBlocks:
    def test_list_blocks_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            blocks = [_make_block(), _make_block(block_id=str(uuid4()))]
            _chain_mock(mock_client, data=blocks)

            resp = client.get("/api/v1/training-blocks/")
            assert resp.status_code == 200
            assert len(resp.json()) == 2

    def test_list_blocks_empty(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.get("/api/v1/training-blocks/")
            assert resp.status_code == 200
            assert resp.json() == []


class TestGetBlock:
    def test_get_block_with_sessions(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            session = _make_block_session()

            block_resp = MagicMock()
            block_resp.data = [block]
            sessions_resp = MagicMock()
            sessions_resp.data = [session]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [block_resp, sessions_resp]

            resp = client.get(f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["block_name"] == "4-Week Strength Block"
            assert len(data["sessions"]) == 1

    def test_get_block_not_found(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.get(f"/api/v1/training-blocks/{uuid4()}")
            assert resp.status_code == 404


class TestUpdateBlock:
    def test_update_block_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            updated_block = {**block, "block_name": "Updated Name"}

            ownership_resp = MagicMock()
            ownership_resp.data = [block]
            update_resp = MagicMock()
            update_resp.data = [updated_block]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [ownership_resp, update_resp]

            resp = client.patch(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}",
                json={"block_name": "Updated Name"},
            )
            assert resp.status_code == 200
            assert resp.json()["block_name"] == "Updated Name"


class TestDeleteBlock:
    def test_delete_block_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            ownership_resp = MagicMock()
            ownership_resp.data = [block]
            delete_resp = MagicMock()
            delete_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [ownership_resp, delete_resp]

            resp = client.delete(f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}")
            assert resp.status_code == 204

    def test_delete_block_not_found(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.delete(f"/api/v1/training-blocks/{uuid4()}")
            assert resp.status_code == 404


# ──────────────────────────────────────────────────────────
# Block Session CRUD Tests
# ──────────────────────────────────────────────────────────


class TestCreateBlockSession:
    def test_create_session_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            session = _make_block_session()

            block_resp = MagicMock()
            block_resp.data = [block]
            insert_resp = MagicMock()
            insert_resp.data = [session]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [block_resp, insert_resp]

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions",
                json={
                    "week_number": 1,
                    "day_of_week": 1,
                    "session_name": "Strength 1",
                    "training_type": "Strength",
                    "exercises": [
                        {
                            "exercise_name": "Back Squat",
                            "exercise_category": "Strength",
                            "sets": 5,
                            "reps": 5,
                            "percent_1rm": 75.0,
                        }
                    ],
                },
            )
            assert resp.status_code == 201
            assert resp.json()["session_name"] == "Strength 1"

    def test_create_session_week_exceeds_block(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)  # num_weeks=4
            block_resp = MagicMock()
            block_resp.data = [block]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.return_value = block_resp

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions",
                json={
                    "week_number": 5,  # Exceeds num_weeks=4
                    "day_of_week": 1,
                    "session_name": "Test",
                    "training_type": "Strength",
                },
            )
            assert resp.status_code == 400
            assert "exceeds" in resp.json()["detail"]

    def test_create_session_block_not_found(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.post(
                f"/api/v1/training-blocks/{uuid4()}/sessions",
                json={
                    "week_number": 1,
                    "day_of_week": 1,
                    "session_name": "Test",
                    "training_type": "Strength",
                },
            )
            assert resp.status_code == 404


class TestDeleteBlockSession:
    def test_delete_session_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            session = _make_block_session(session_id=SAMPLE_SESSION_ID)

            block_resp = MagicMock()
            block_resp.data = [block]
            session_resp = MagicMock()
            session_resp.data = [session]
            delete_resp = MagicMock()
            delete_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [block_resp, session_resp, delete_resp]

            resp = client.delete(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions/{SAMPLE_SESSION_ID}"
            )
            assert resp.status_code == 204


class TestDuplicateBlockSession:
    def test_duplicate_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            session = _make_block_session(session_id=SAMPLE_SESSION_ID)
            new_session = {**session, "id": str(uuid4()), "week_number": 2}

            block_resp = MagicMock()
            block_resp.data = [block]
            session_resp = MagicMock()
            session_resp.data = [session]
            insert_resp = MagicMock()
            insert_resp.data = [new_session]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [block_resp, session_resp, insert_resp]

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions/{SAMPLE_SESSION_ID}/duplicate?target_week=2"
            )
            assert resp.status_code == 201
            assert resp.json()["week_number"] == 2

    def test_duplicate_target_week_exceeds_block(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)  # num_weeks=4
            session = _make_block_session(session_id=SAMPLE_SESSION_ID)

            block_resp = MagicMock()
            block_resp.data = [block]
            session_resp = MagicMock()
            session_resp.data = [session]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [block_resp, session_resp]

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions/{SAMPLE_SESSION_ID}/duplicate?target_week=5"
            )
            assert resp.status_code == 400


# ──────────────────────────────────────────────────────────
# Athlete Maxes Tests
# ──────────────────────────────────────────────────────────


class TestAthleteMaxes:
    def test_list_maxes(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            # verify_athlete_access mock chain
            access_resp = MagicMock()
            access_resp.data = [_make_athlete(SAMPLE_ATHLETE_ID)]
            maxes_resp = MagicMock()
            maxes_resp.data = [
                {
                    "id": str(uuid4()),
                    "athlete_id": SAMPLE_ATHLETE_ID,
                    "exercise_name": "Back Squat",
                    "max_kg": 140.0,
                    "source": "manual",
                    "updated_at": datetime.now().isoformat(),
                }
            ]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [access_resp, maxes_resp]

            resp = client.get(f"/api/v1/training-blocks/athlete-maxes/{SAMPLE_ATHLETE_ID}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["max_kg"] == 140.0

    def test_upsert_max_create(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            max_data = {
                "id": str(uuid4()),
                "athlete_id": SAMPLE_ATHLETE_ID,
                "exercise_name": "Back Squat",
                "max_kg": 140.0,
                "source": "manual",
                "updated_at": datetime.now().isoformat(),
            }

            access_resp = MagicMock()
            access_resp.data = [_make_athlete(SAMPLE_ATHLETE_ID)]
            upsert_resp = MagicMock()
            upsert_resp.data = [max_data]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [access_resp, upsert_resp]

            resp = client.put(
                f"/api/v1/training-blocks/athlete-maxes/{SAMPLE_ATHLETE_ID}",
                json={"exercise_name": "Back Squat", "max_kg": 140.0},
            )
            assert resp.status_code == 200
            assert resp.json()["max_kg"] == 140.0

    def test_upsert_max_update(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            max_data = {
                "id": str(uuid4()),
                "athlete_id": SAMPLE_ATHLETE_ID,
                "exercise_name": "Back Squat",
                "max_kg": 150.0,
                "source": "manual",
                "updated_at": datetime.now().isoformat(),
            }

            access_resp = MagicMock()
            access_resp.data = [_make_athlete(SAMPLE_ATHLETE_ID)]
            upsert_resp = MagicMock()
            upsert_resp.data = [max_data]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [access_resp, upsert_resp]

            resp = client.put(
                f"/api/v1/training-blocks/athlete-maxes/{SAMPLE_ATHLETE_ID}",
                json={"exercise_name": "Back Squat", "max_kg": 150.0},
            )
            assert resp.status_code == 200
            assert resp.json()["max_kg"] == 150.0

    def test_delete_max_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            max_id = str(uuid4())
            access_resp = MagicMock()
            access_resp.data = [_make_athlete(SAMPLE_ATHLETE_ID)]
            find_resp = MagicMock()
            find_resp.data = [{"id": max_id}]
            delete_resp = MagicMock()
            delete_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [access_resp, find_resp, delete_resp]

            resp = client.delete(
                f"/api/v1/training-blocks/athlete-maxes/{SAMPLE_ATHLETE_ID}/Back%20Squat"
            )
            assert resp.status_code == 204

    def test_delete_max_not_found(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            access_resp = MagicMock()
            access_resp.data = [_make_athlete(SAMPLE_ATHLETE_ID)]
            find_resp = MagicMock()
            find_resp.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [access_resp, find_resp]

            resp = client.delete(
                f"/api/v1/training-blocks/athlete-maxes/{SAMPLE_ATHLETE_ID}/NonExistent"
            )
            assert resp.status_code == 404

    def test_upsert_max_athlete_403(self, athlete_client):
        resp = athlete_client.put(
            f"/api/v1/training-blocks/athlete-maxes/{SAMPLE_ATHLETE_ID}",
            json={"exercise_name": "Back Squat", "max_kg": 140.0},
        )
        assert resp.status_code == 403

    def test_upsert_max_invalid_source_422(self):
        resp = client.put(
            f"/api/v1/training-blocks/athlete-maxes/{SAMPLE_ATHLETE_ID}",
            json={"exercise_name": "Back Squat", "max_kg": 140.0, "source": "invalid"},
        )
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────────
# Apply + Preview Tests
# ──────────────────────────────────────────────────────────


class TestApplyBlock:
    def test_apply_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            block_session = _make_block_session()
            # Exercise has percent_1rm, no weight_kg
            block_session["exercises"][0]["weight_kg"] = None

            athlete = _make_athlete(SAMPLE_ATHLETE_ID)
            session_id = str(uuid4())
            app_id = str(uuid4())

            block_resp = MagicMock()
            block_resp.data = [block]
            athletes_resp = MagicMock()
            athletes_resp.data = [athlete]
            sessions_query_resp = MagicMock()
            sessions_query_resp.data = [block_session]
            # bulk insert sessions
            created_sessions_resp = MagicMock()
            created_sessions_resp.data = [
                {"id": session_id, "athlete_id": SAMPLE_ATHLETE_ID}
            ]
            # athlete_maxes check (empty = no manual max)
            maxes_empty = MagicMock()
            maxes_empty.data = []
            # prescriptions bulk insert
            prescriptions_resp = MagicMock()
            prescriptions_resp.data = []
            # application audit
            app_resp = MagicMock()
            app_resp.data = [{"id": app_id}]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [
                block_resp,       # verify block ownership
                athletes_resp,    # verify athletes
                sessions_query_resp,  # load block sessions
                created_sessions_resp,  # bulk insert sessions
                maxes_empty,      # athlete_maxes check
                prescriptions_resp,  # bulk insert prescriptions
                app_resp,         # audit trail
            ]

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",  # Monday
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["created_count"] == 1
            assert data["sessions_per_athlete"] == 1
            assert len(data["unresolved_exercises"]) == 1
            assert data["unresolved_exercises"][0]["exercise_name"] == "Back Squat"

    def test_apply_not_monday_422(self):
        resp = client.post(
            f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
            json={
                "athlete_ids": [SAMPLE_ATHLETE_ID],
                "start_date": "2026-03-17",  # Tuesday
            },
        )
        assert resp.status_code == 422

    def test_apply_duplicate_athletes_422(self):
        resp = client.post(
            f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
            json={
                "athlete_ids": [SAMPLE_ATHLETE_ID, SAMPLE_ATHLETE_ID],
                "start_date": "2026-03-16",
            },
        )
        assert resp.status_code == 422

    def test_apply_block_not_found(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.post(
                f"/api/v1/training-blocks/{uuid4()}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 404

    def test_apply_no_sessions_400(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            athlete = _make_athlete(SAMPLE_ATHLETE_ID)

            block_resp = MagicMock()
            block_resp.data = [block]
            athletes_resp = MagicMock()
            athletes_resp.data = [athlete]
            empty_sessions = MagicMock()
            empty_sessions.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [block_resp, athletes_resp, empty_sessions]

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
                json={
                    "athlete_ids": [SAMPLE_ATHLETE_ID],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 400

    def test_apply_athlete_403(self, athlete_client):
        resp = athlete_client.post(
            f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
            json={
                "athlete_ids": [SAMPLE_ATHLETE_ID],
                "start_date": "2026-03-16",
            },
        )
        assert resp.status_code == 403

    def test_apply_missing_athletes_400(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            block_resp = MagicMock()
            block_resp.data = [block]
            athletes_resp = MagicMock()
            athletes_resp.data = []  # No athletes found

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [block_resp, athletes_resp]

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
                json={
                    "athlete_ids": [str(uuid4())],
                    "start_date": "2026-03-16",
                },
            )
            assert resp.status_code == 400


class TestPreviewBlock:
    def test_preview_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            block_session = _make_block_session()
            athlete = _make_athlete(SAMPLE_ATHLETE_ID)

            block_resp = MagicMock()
            block_resp.data = [block]
            athletes_resp = MagicMock()
            athletes_resp.data = [athlete]
            sessions_resp = MagicMock()
            sessions_resp.data = [block_session]
            # no recorded max
            maxes_empty = MagicMock()
            maxes_empty.data = []

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [
                block_resp,
                athletes_resp,
                sessions_resp,
                maxes_empty,
            ]

            resp = client.post(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/preview",
                json={"athlete_ids": [SAMPLE_ATHLETE_ID]},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["sessions_per_athlete"] == 1
            assert len(data["resolutions"]) == 1
            assert data["resolutions"][0]["source"] == "missing"

    def test_preview_block_not_found(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client
            _chain_mock(mock_client, data=[])

            resp = client.post(
                f"/api/v1/training-blocks/{uuid4()}/preview",
                json={"athlete_ids": [SAMPLE_ATHLETE_ID]},
            )
            assert resp.status_code == 404


# ──────────────────────────────────────────────────────────
# Schema Validation Tests
# ──────────────────────────────────────────────────────────


class TestSchemaValidation:
    def test_block_exercise_percent_1rm_range(self):
        from app.schemas.training_block import BlockExercise

        ex = BlockExercise(exercise_name="Squat", percent_1rm=80.0)
        assert ex.percent_1rm == 80.0

        with pytest.raises(Exception):
            BlockExercise(exercise_name="Squat", percent_1rm=0)

        with pytest.raises(Exception):
            BlockExercise(exercise_name="Squat", percent_1rm=101)

    def test_block_apply_start_date_must_be_monday(self):
        from app.schemas.training_block import BlockApplyRequest

        # Monday
        req = BlockApplyRequest(
            athlete_ids=["00000000-0000-0000-0000-000000000001"],
            start_date="2026-03-16",
        )
        assert req.start_date.weekday() == 0

        # Tuesday should fail
        with pytest.raises(Exception):
            BlockApplyRequest(
                athlete_ids=["00000000-0000-0000-0000-000000000001"],
                start_date="2026-03-17",
            )

    def test_block_apply_no_duplicate_athletes(self):
        from app.schemas.training_block import BlockApplyRequest

        with pytest.raises(Exception):
            BlockApplyRequest(
                athlete_ids=[
                    "00000000-0000-0000-0000-000000000001",
                    "00000000-0000-0000-0000-000000000001",
                ],
                start_date="2026-03-16",
            )

    def test_athlete_max_source_validation(self):
        from app.schemas.training_block import AthleteMaxUpsert

        manual = AthleteMaxUpsert(exercise_name="Squat", max_kg=100.0, source="manual")
        assert manual.source == "manual"

        vbt = AthleteMaxUpsert(exercise_name="Squat", max_kg=100.0, source="vbt")
        assert vbt.source == "vbt"

        with pytest.raises(Exception):
            AthleteMaxUpsert(exercise_name="Squat", max_kg=100.0, source="invalid")

    def test_block_session_week_day_range(self):
        from app.schemas.training_block import BlockSessionCreate

        with pytest.raises(Exception):
            BlockSessionCreate(
                week_number=0, day_of_week=1,
                session_name="Test", training_type="Strength"
            )

        with pytest.raises(Exception):
            BlockSessionCreate(
                week_number=1, day_of_week=8,
                session_name="Test", training_type="Strength"
            )


# ──────────────────────────────────────────────────────────
# Update Block Session Tests
# ──────────────────────────────────────────────────────────


class TestUpdateBlockSession:
    def test_update_session_success(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            session = _make_block_session(session_id=SAMPLE_SESSION_ID)
            updated_session = {**session, "session_name": "Updated Strength"}

            ownership_resp = MagicMock()
            ownership_resp.data = [block]
            session_resp = MagicMock()
            session_resp.data = [session]
            update_resp = MagicMock()
            update_resp.data = [updated_session]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [ownership_resp, session_resp, update_resp]

            resp = client.patch(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions/{SAMPLE_SESSION_ID}",
                json={"session_name": "Updated Strength"},
            )
            assert resp.status_code == 200
            assert resp.json()["session_name"] == "Updated Strength"

    def test_update_session_not_found(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)

            ownership_resp = MagicMock()
            ownership_resp.data = [block]
            session_resp = MagicMock()
            session_resp.data = []  # session not found

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [ownership_resp, session_resp]

            resp = client.patch(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions/{uuid4()}",
                json={"session_name": "Updated"},
            )
            assert resp.status_code == 404

    def test_update_session_exercises(self):
        with patch(BLOCKS_PATCH) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            block = _make_block(block_id=SAMPLE_BLOCK_ID)
            session = _make_block_session(session_id=SAMPLE_SESSION_ID)
            new_exercises = [
                {
                    "exercise_name": "Deadlift",
                    "exercise_category": "Strength",
                    "sets": 3,
                    "reps": 3,
                    "percent_1rm": 85.0,
                }
            ]
            updated_session = {**session, "exercises": new_exercises}

            ownership_resp = MagicMock()
            ownership_resp.data = [block]
            session_resp = MagicMock()
            session_resp.data = [session]
            update_resp = MagicMock()
            update_resp.data = [updated_session]

            table_mock = _chain_mock(mock_client)
            table_mock.execute.side_effect = [ownership_resp, session_resp, update_resp]

            resp = client.patch(
                f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions/{SAMPLE_SESSION_ID}",
                json={"exercises": new_exercises},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["exercises"]) == 1
            assert data["exercises"][0]["exercise_name"] == "Deadlift"
            # Verify None values are filtered (percent_1rm=85 is present, not None)
            assert data["exercises"][0]["percent_1rm"] == 85.0


# ──────────────────────────────────────────────────────────
# Additional Apply Tests
# ──────────────────────────────────────────────────────────


def test_apply_block_multiple_athletes():
    """Apply block to 2 athletes — created_count == 2, sessions_per_athlete == 1."""
    with patch(BLOCKS_PATCH) as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        block = _make_block(block_id=SAMPLE_BLOCK_ID)
        block_session = _make_block_session()
        # Plain weight exercise, no percent_1rm resolution needed
        block_session["exercises"][0]["weight_kg"] = 100.0
        block_session["exercises"][0]["percent_1rm"] = None

        athlete1 = _make_athlete(SAMPLE_ATHLETE_ID)
        athlete2 = _make_athlete(SAMPLE_ATHLETE_ID_2)

        session_id1 = str(uuid4())
        session_id2 = str(uuid4())
        app_id = str(uuid4())

        block_resp = MagicMock()
        block_resp.data = [block]
        athletes_resp = MagicMock()
        athletes_resp.data = [athlete1, athlete2]
        sessions_query_resp = MagicMock()
        sessions_query_resp.data = [block_session]
        created_sessions_resp = MagicMock()
        created_sessions_resp.data = [
            {"id": session_id1, "athlete_id": SAMPLE_ATHLETE_ID},
            {"id": session_id2, "athlete_id": SAMPLE_ATHLETE_ID_2},
        ]
        prescriptions_resp = MagicMock()
        prescriptions_resp.data = []
        app_resp = MagicMock()
        app_resp.data = [{"id": app_id}]

        table_mock = _chain_mock(mock_client)
        table_mock.execute.side_effect = [
            block_resp,             # verify block ownership
            athletes_resp,          # verify athletes
            sessions_query_resp,    # load block sessions
            created_sessions_resp,  # bulk insert sessions
            prescriptions_resp,     # bulk insert prescriptions
            app_resp,               # audit trail
        ]

        resp = client.post(
            f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
            json={
                "athlete_ids": [SAMPLE_ATHLETE_ID, SAMPLE_ATHLETE_ID_2],
                "start_date": "2026-03-16",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 2
        assert data["sessions_per_athlete"] == 1


def test_apply_block_circuit_exercises():
    """Apply block with circuit exercises — 2 rounds × 2 exercises = 4 prescriptions."""
    with patch(BLOCKS_PATCH) as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        block = _make_block(block_id=SAMPLE_BLOCK_ID)

        circuit_session = {
            "id": str(uuid4()),
            "block_id": SAMPLE_BLOCK_ID,
            "week_number": 1,
            "day_of_week": 1,
            "session_name": "Circuit Day",
            "training_type": "Conditioning",
            "notes": None,
            "exercises": [
                {
                    "exercise_name": "Burpees",
                    "exercise_category": "Circuit",
                    "sets": 2,
                    "reps": 10,
                },
                {
                    "exercise_name": "Box Jumps",
                    "exercise_category": "Circuit",
                    "sets": 2,
                    "reps": 8,
                },
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        athlete = _make_athlete(SAMPLE_ATHLETE_ID)
        session_id = str(uuid4())
        app_id = str(uuid4())

        block_resp = MagicMock()
        block_resp.data = [block]
        athletes_resp = MagicMock()
        athletes_resp.data = [athlete]
        sessions_query_resp = MagicMock()
        sessions_query_resp.data = [circuit_session]
        created_sessions_resp = MagicMock()
        created_sessions_resp.data = [{"id": session_id, "athlete_id": SAMPLE_ATHLETE_ID}]

        # Circuit exercises have no percent_1rm, so no VBT/maxes lookups needed.
        # The prescriptions insert is the next call.
        prescriptions_resp = MagicMock()
        prescriptions_resp.data = []
        app_resp = MagicMock()
        app_resp.data = [{"id": app_id}]

        table_mock = _chain_mock(mock_client)
        table_mock.execute.side_effect = [
            block_resp,
            athletes_resp,
            sessions_query_resp,
            created_sessions_resp,
            prescriptions_resp,
            app_resp,
        ]

        # Capture the prescriptions that were actually inserted
        inserted_prescriptions = []

        def capture_insert(rows):
            if isinstance(rows, list) and rows and "exercise_category" in rows[0]:
                inserted_prescriptions.extend(rows)
            table_mock.insert.return_value = table_mock
            return table_mock

        table_mock.insert.side_effect = capture_insert

        resp = client.post(
            f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/apply",
            json={
                "athlete_ids": [SAMPLE_ATHLETE_ID],
                "start_date": "2026-03-16",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 1
        # 2 rounds × 2 exercises = 4 prescriptions
        circuit_rows = [p for p in inserted_prescriptions if p.get("exercise_category") == "Circuit"]
        assert len(circuit_rows) == 4


def test_create_session_duplicate_409():
    """Create a session that triggers unique constraint violation -> 409."""
    with patch(BLOCKS_PATCH) as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        block = _make_block(block_id=SAMPLE_BLOCK_ID)
        block_resp = MagicMock()
        block_resp.data = [block]

        table_mock = _chain_mock(mock_client)

        def side_effect_fn():
            raise Exception("duplicate key value violates unique constraint")

        # First execute = ownership check (returns block), second = insert raises
        table_mock.execute.side_effect = [
            block_resp,
            Exception("duplicate key value violates unique constraint"),
        ]

        resp = client.post(
            f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions",
            json={
                "week_number": 1,
                "day_of_week": 1,
                "session_name": "Strength 1",
                "training_type": "Strength",
            },
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]


def test_duplicate_session_conflict_409():
    """Duplicate a session into a week that already has a matching session -> 409."""
    with patch(BLOCKS_PATCH) as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client

        block = _make_block(block_id=SAMPLE_BLOCK_ID)
        session = _make_block_session(session_id=SAMPLE_SESSION_ID)

        ownership_resp = MagicMock()
        ownership_resp.data = [block]
        session_resp = MagicMock()
        session_resp.data = [session]

        table_mock = _chain_mock(mock_client)
        table_mock.execute.side_effect = [
            ownership_resp,
            session_resp,
            Exception("duplicate key value violates unique constraint"),
        ]

        resp = client.post(
            f"/api/v1/training-blocks/{SAMPLE_BLOCK_ID}/sessions/{SAMPLE_SESSION_ID}/duplicate?target_week=2"
        )
        assert resp.status_code == 409
        assert "Cannot duplicate" in resp.json()["detail"]
