"""Tests for athlete signup flow and auth/me athlete_id."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client for auth router."""
    with patch("app.core.supabase_client.get_supabase_client") as mock_core, \
         patch("app.routers.auth.get_supabase_client") as mock_get, \
         patch("app.routers.auth.create_client") as mock_create:
        mock_client = MagicMock()
        mock_core.return_value = mock_client
        mock_get.return_value = mock_client
        # Fresh admin client for post-signup ops uses same mock
        mock_create.return_value = mock_client
        yield mock_client


@pytest.fixture
def valid_invite_data():
    """A valid, unused, non-expired invitation row."""
    return {
        "id": str(uuid4()),
        "athlete_id": str(uuid4()),
        "coach_id": str(uuid4()),
        "invite_code": "VALID123",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
        "used_at": None,
        "used_by": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class TestAthleteSignup:
    """Test POST /api/v1/auth/signup/athlete"""

    def test_athlete_signup_success(self, mock_supabase, valid_invite_data):
        """Should create athlete account, link athlete record, consume invite."""
        new_user_id = str(uuid4())

        # Mock auth.sign_up
        mock_user = MagicMock()
        mock_user.id = new_user_id
        mock_user.email = "athlete@example.com"
        mock_session = MagicMock()
        mock_session.access_token = "test-token-123"
        mock_auth_response = MagicMock()
        mock_auth_response.user = mock_user
        mock_auth_response.session = mock_session
        mock_supabase.auth.sign_up.return_value = mock_auth_response

        call_count = {"athlete_invitations": 0, "profiles": 0}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athlete_invitations":
                call_count["athlete_invitations"] += 1
                if call_count["athlete_invitations"] == 1:
                    # Validate invite code lookup
                    mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [
                        valid_invite_data
                    ]
                else:
                    # Consume invitation (update)
                    mock_table.update.return_value.eq.return_value.is_.return_value.execute.return_value.data = [
                        {**valid_invite_data, "used_at": datetime.now(timezone.utc).isoformat(), "used_by": new_user_id}
                    ]
            elif table_name == "profiles":
                mock_table.insert.return_value.execute.return_value.data = [
                    {"id": new_user_id, "email": "athlete@example.com", "role": "athlete"}
                ]
            elif table_name == "athletes":
                mock_table.update.return_value.eq.return_value.execute.return_value.data = [
                    {"id": valid_invite_data["athlete_id"], "user_id": new_user_id}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/auth/signup/athlete",
            json={
                "email": "athlete@example.com",
                "password": "Secure1234",
                "invite_code": "VALID123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == new_user_id
        assert data["email"] == "athlete@example.com"

    def test_athlete_signup_invalid_code(self, mock_supabase):
        """Should return 400 for non-existent invitation code."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = []

        response = client.post(
            "/api/v1/auth/signup/athlete",
            json={
                "email": "athlete@example.com",
                "password": "Secure1234",
                "invite_code": "INVALID1",
            },
        )

        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]

    def test_athlete_signup_expired_code(self, mock_supabase, valid_invite_data):
        """Should return 400 for expired invitation code."""
        expired_invite = {
            **valid_invite_data,
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = [
            expired_invite
        ]

        response = client.post(
            "/api/v1/auth/signup/athlete",
            json={
                "email": "athlete@example.com",
                "password": "Secure1234",
                "invite_code": "VALID123",
            },
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_athlete_signup_used_code(self, mock_supabase):
        """Should return 400 for already used invitation code (is_ filter returns empty)."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        # The is_("used_at", "null") filter means used codes won't be returned
        mock_table.select.return_value.eq.return_value.is_.return_value.execute.return_value.data = []

        response = client.post(
            "/api/v1/auth/signup/athlete",
            json={
                "email": "athlete@example.com",
                "password": "Secure1234",
                "invite_code": "USED1234",
            },
        )

        assert response.status_code == 400

    def test_athlete_signup_short_password(self):
        """Should return 422 for password shorter than 8 characters."""
        response = client.post(
            "/api/v1/auth/signup/athlete",
            json={
                "email": "athlete@example.com",
                "password": "short",
                "invite_code": "VALID123",
            },
        )

        assert response.status_code == 422


class TestAuthMeAthleteId:
    """Test GET /api/v1/auth/me with athlete role."""

    def test_auth_me_returns_athlete_id(self):
        """Should include athlete_id when user is an athlete."""
        from tests.conftest import TEST_ATHLETE_ID

        athlete_id = str(uuid4())

        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id=TEST_ATHLETE_ID, role="athlete"
        )

        with patch("app.routers.auth.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client
            mock_table = MagicMock()
            mock_client.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": athlete_id}
            ]

            athlete_client = TestClient(app)
            response = athlete_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "athlete"
        assert data["athlete_id"] == athlete_id

        if original:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)

    def test_auth_me_coach_no_athlete_id(self):
        """Should NOT include athlete_id for coach role."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "coach"
        assert "athlete_id" not in data

    def test_auth_me_admin_no_athlete_id(self):
        """Should NOT include athlete_id for admin role."""
        from tests.conftest import TEST_ADMIN_ID

        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id=TEST_ADMIN_ID, role="admin"
        )

        admin_client = TestClient(app)
        response = admin_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert "athlete_id" not in data

        if original:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)
