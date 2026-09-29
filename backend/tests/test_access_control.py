"""Tests for centralized access control module and athlete role restrictions."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.access_control import get_athlete_coach_id, require_coach_or_admin, verify_athlete_access
from app.core.security import AuthenticatedUser, get_current_user
from app.main import app

ATHLETE_USER_ID = uuid4()
ATHLETE_LINKED_ATHLETE_ID = uuid4()
COACH_USER_ID = uuid4()


def get_athlete_user():
    return AuthenticatedUser(id=ATHLETE_USER_ID, role="athlete")


def get_coach_user():
    return AuthenticatedUser(id=COACH_USER_ID, role="coach")


@pytest.fixture
def athlete_client():
    """Provide a test client authenticated as athlete."""
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: get_athlete_user()
    client = TestClient(app)
    yield client
    if original:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)


# ─── Unit Tests for access_control module ─────────────────────────────────────


class TestVerifyAthleteAccess:
    """Unit tests for verify_athlete_access."""

    def test_coach_owns_athlete(self):
        """Coach should access their own athlete via coach_id."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": str(uuid4())}
        ]
        user = AuthenticatedUser(id=uuid4(), role="coach")
        assert verify_athlete_access(mock_client, uuid4(), user) is True

    def test_coach_not_owns_athlete(self):
        """Coach should not access another coach's athlete."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        user = AuthenticatedUser(id=uuid4(), role="coach")
        assert verify_athlete_access(mock_client, uuid4(), user) is False

    def test_athlete_linked_via_user_id(self):
        """Athlete user should access their own record via user_id."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": str(ATHLETE_LINKED_ATHLETE_ID)}
        ]
        user = AuthenticatedUser(id=ATHLETE_USER_ID, role="athlete")
        assert verify_athlete_access(mock_client, ATHLETE_LINKED_ATHLETE_ID, user) is True

    def test_athlete_not_linked(self):
        """Athlete user should not access another athlete's record."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        user = AuthenticatedUser(id=ATHLETE_USER_ID, role="athlete")
        assert verify_athlete_access(mock_client, uuid4(), user) is False

    def test_admin_owns_athlete(self):
        """Admin should access their athletes via coach_id."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": str(uuid4())}
        ]
        user = AuthenticatedUser(id=uuid4(), role="admin")
        assert verify_athlete_access(mock_client, uuid4(), user) is True


class TestRequireCoachOrAdmin:
    """Unit tests for require_coach_or_admin."""

    def test_coach_passes(self):
        """Coach role should not raise."""
        require_coach_or_admin(AuthenticatedUser(id=uuid4(), role="coach"))

    def test_admin_passes(self):
        """Admin role should not raise."""
        require_coach_or_admin(AuthenticatedUser(id=uuid4(), role="admin"))

    def test_athlete_forbidden(self):
        """Athlete role should raise 403."""
        with pytest.raises(HTTPException) as exc_info:
            require_coach_or_admin(AuthenticatedUser(id=uuid4(), role="athlete"))
        assert exc_info.value.status_code == 403


class TestGetAthleteCoachId:
    """Unit tests for get_athlete_coach_id."""

    def test_returns_coach_id(self):
        """Should return coach_id when athlete is linked."""
        coach_id = str(uuid4())
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"coach_id": coach_id}
        ]
        user = AuthenticatedUser(id=uuid4(), role="athlete")
        assert get_athlete_coach_id(mock_client, user) == coach_id

    def test_raises_404_when_not_linked(self):
        """Should raise 404 when athlete has no linked record."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        user = AuthenticatedUser(id=uuid4(), role="athlete")
        with pytest.raises(HTTPException) as exc_info:
            get_athlete_coach_id(mock_client, user)
        assert exc_info.value.status_code == 404


# ─── Integration Tests (athlete role via test client) ──────────────────────────


class TestAthleteReadEvents:
    """Test that athlete can read own events."""

    def test_athlete_get_own_events(self, athlete_client):
        """Athlete should be able to GET events for their linked athlete."""
        athlete_id = str(ATHLETE_LINKED_ATHLETE_ID)
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            def table_side_effect(table_name):
                t = MagicMock()
                if table_name == "athletes":
                    t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {"id": athlete_id}
                    ]
                else:
                    t.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
                return t

            mock_client.table.side_effect = table_side_effect

            response = athlete_client.get(f"/api/v1/events/athlete/{athlete_id}")
            assert response.status_code == 200


class TestAthleteMutationsForbidden:
    """Test that athlete cannot perform mutation operations."""

    def test_athlete_create_event_forbidden(self, athlete_client):
        """Athlete should get 403 on POST /events/."""
        response = athlete_client.post(
            "/api/v1/events/",
            json={
                "athlete_id": str(ATHLETE_LINKED_ATHLETE_ID),
                "event_date": "2024-01-15",
                "metrics": {"height_cm": 45.5},
            },
        )
        assert response.status_code == 403

    def test_athlete_update_event_forbidden(self, athlete_client):
        """Athlete should get 403 on PATCH /events/{id}."""
        response = athlete_client.patch(
            f"/api/v1/events/{uuid4()}",
            json={"metrics": {"height_cm": 46.0}},
        )
        assert response.status_code == 403

    def test_athlete_delete_event_forbidden(self, athlete_client):
        """Athlete should get 403 on DELETE /events/{id}."""
        response = athlete_client.delete(f"/api/v1/events/{uuid4()}")
        assert response.status_code == 403

    def test_athlete_create_session_allowed(self, athlete_client):
        """Athlete should NOT get 403 on POST /training/sessions/ (allowed since Phase B)."""
        response = athlete_client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": str(ATHLETE_LINKED_ATHLETE_ID),
                "session_date": "2024-01-15",
                "training_type": "Strength",
                "duration_minutes": 60,
                "rpe": 7,
            },
        )
        # Should not be 403 — will be 503 (no DB) or another status, not forbidden
        assert response.status_code != 403

    def test_athlete_create_wellness_allowed(self, athlete_client):
        """Athlete should NOT get 403 on POST /wellness/ (allowed since Phase B)."""
        response = athlete_client.post(
            "/api/v1/wellness/",
            json={
                "athlete_id": str(ATHLETE_LINKED_ATHLETE_ID),
                "entry_date": "2024-01-15",
                "sleep": 5,
                "fatigue": 3,
                "stress": 2,
                "doms": 4,
            },
        )
        # Should not be 403 — will be 503 (no DB) or another status, not forbidden
        assert response.status_code != 403

    def test_athlete_create_athlete_forbidden(self, athlete_client):
        """Athlete should get 403 on POST /athletes/."""
        response = athlete_client.post(
            "/api/v1/athletes/",
            json={"name": "Test Athlete", "gender": "male"},
        )
        assert response.status_code == 403

    def test_athlete_get_exercise_library_allowed(self, athlete_client):
        """Athlete should be able to list their coach's exercise library."""
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            def table_side_effect(table_name):
                t = MagicMock()
                if table_name == "athletes":
                    t.select.return_value.eq.return_value.execute.return_value.data = [
                        {"coach_id": str(COACH_USER_ID)}
                    ]
                elif table_name == "exercise_library":
                    t.select.return_value.eq.return_value.ilike.return_value.order.return_value.execute.return_value.data = []
                    t.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
                return t

            mock_client.table.side_effect = table_side_effect

            response = athlete_client.get("/api/v1/exercise-library/")
            assert response.status_code == 200

    def test_athlete_create_exercise_library_forbidden(self, athlete_client):
        """Athlete should get 403 on POST /exercise-library/ (coach-only mutation)."""
        response = athlete_client.post(
            "/api/v1/exercise-library/",
            json={"exercise_name": "Test", "exercise_category": "Strength"},
        )
        assert response.status_code == 403

    def test_athlete_delete_exercise_library_forbidden(self, athlete_client):
        """Athlete should get 403 on DELETE /exercise-library/{id} (coach-only mutation)."""
        response = athlete_client.delete(f"/api/v1/exercise-library/{uuid4()}")
        assert response.status_code == 403

    def test_athlete_get_session_templates_allowed(self, athlete_client):
        """Athlete should be able to list their coach's templates (via coach lookup)."""
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            def table_side_effect(table_name):
                t = MagicMock()
                if table_name == "athletes":
                    t.select.return_value.eq.return_value.execute.return_value.data = [
                        {"coach_id": str(COACH_USER_ID)}
                    ]
                elif table_name == "session_templates":
                    t.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
                return t

            mock_client.table.side_effect = table_side_effect

            response = athlete_client.get("/api/v1/session-templates/")
            assert response.status_code == 200

    def test_athlete_upload_csv_forbidden(self, athlete_client):
        """Athlete should get 403 on POST /uploads/csv."""
        import io

        csv_content = b"Test Date,CMJ Height (cm)\n15/01/2024,45.5"
        response = athlete_client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert response.status_code == 403

    def test_athlete_get_consent_forbidden(self, athlete_client):
        """Athlete should get 403 on GET /consent/ (coach-only resource)."""
        response = athlete_client.get("/api/v1/consent/")
        assert response.status_code == 403


class TestAthleteReadTraining:
    """Test that athlete can read own training sessions."""

    def test_athlete_get_own_training_sessions(self, athlete_client):
        """Athlete should be able to GET training sessions for their linked athlete."""
        athlete_id = str(ATHLETE_LINKED_ATHLETE_ID)
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            def table_side_effect(table_name):
                t = MagicMock()
                if table_name == "athletes":
                    t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {"id": athlete_id}
                    ]
                else:
                    t.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
                return t

            mock_client.table.side_effect = table_side_effect

            response = athlete_client.get(f"/api/v1/training/sessions/athlete/{athlete_id}")
            assert response.status_code == 200


class TestAthleteReadWellness:
    """Test that athlete can read own wellness entries."""

    def test_athlete_get_own_wellness(self, athlete_client):
        """Athlete should be able to GET wellness entries for their linked athlete."""
        athlete_id = str(ATHLETE_LINKED_ATHLETE_ID)
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            def table_side_effect(table_name):
                t = MagicMock()
                if table_name == "athletes":
                    t.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {"id": athlete_id}
                    ]
                else:
                    t.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
                return t

            mock_client.table.side_effect = table_side_effect

            response = athlete_client.get(f"/api/v1/wellness/athlete/{athlete_id}")
            assert response.status_code == 200
