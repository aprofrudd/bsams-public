"""Tests for invitation system router."""

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
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock_core, \
         patch("app.routers.invitations.get_supabase_client") as mock_router:
        mock_client = MagicMock()
        mock_core.return_value = mock_client
        mock_router.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_athlete_id():
    """Sample athlete ID."""
    return str(uuid4())


@pytest.fixture
def sample_invite_data(sample_athlete_id):
    """Sample invitation data as returned from DB."""
    from tests.conftest import TEST_USER_ID

    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "coach_id": str(TEST_USER_ID),
        "invite_code": "ABC12345",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "used_at": None,
        "used_by": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


class TestCreateInvitation:
    """Test POST /api/v1/invitations/"""

    def test_create_invitation_success(self, mock_supabase, sample_athlete_id, sample_invite_data):
        """Should create and return invitation."""
        from tests.conftest import TEST_USER_ID

        call_count = {"athlete_invitations": 0}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id, "user_id": None, "coach_id": str(TEST_USER_ID)}
                ]
            elif table_name == "athlete_invitations":
                call_count["athlete_invitations"] += 1
                if call_count["athlete_invitations"] == 1:
                    # Active invite check - none found
                    mock_table.select.return_value.eq.return_value.is_.return_value.gt.return_value.execute.return_value.data = []
                else:
                    # Insert
                    mock_table.insert.return_value.execute.return_value.data = [sample_invite_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/invitations/",
            json={"athlete_id": sample_athlete_id},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["athlete_id"] == sample_athlete_id
        assert data["invite_code"] == "ABC12345"

    def test_create_invitation_athlete_not_owned(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete belongs to different coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_athlete_id, "user_id": None, "coach_id": str(uuid4())}
        ]

        response = client.post(
            "/api/v1/invitations/",
            json={"athlete_id": sample_athlete_id},
        )

        assert response.status_code == 404

    def test_create_invitation_athlete_not_found(self, mock_supabase):
        """Should return 404 when athlete doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.post(
            "/api/v1/invitations/",
            json={"athlete_id": str(uuid4())},
        )

        assert response.status_code == 404

    def test_create_invitation_athlete_already_linked(self, mock_supabase, sample_athlete_id):
        """Should return 409 when athlete already has a linked user account."""
        from tests.conftest import TEST_USER_ID

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_athlete_id, "user_id": str(uuid4()), "coach_id": str(TEST_USER_ID)}
        ]

        response = client.post(
            "/api/v1/invitations/",
            json={"athlete_id": sample_athlete_id},
        )

        assert response.status_code == 409
        assert "linked account" in response.json()["detail"]

    def test_create_invitation_duplicate_active(self, mock_supabase, sample_athlete_id):
        """Should return 409 when active invitation already exists."""
        from tests.conftest import TEST_USER_ID

        call_count = {"athlete_invitations": 0}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id, "user_id": None, "coach_id": str(TEST_USER_ID)}
                ]
            elif table_name == "athlete_invitations":
                call_count["athlete_invitations"] += 1
                if call_count["athlete_invitations"] == 1:
                    # Active invite check - found one
                    mock_table.select.return_value.eq.return_value.is_.return_value.gt.return_value.execute.return_value.data = [
                        {"id": str(uuid4())}
                    ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/invitations/",
            json={"athlete_id": sample_athlete_id},
        )

        assert response.status_code == 409
        assert "Active invitation" in response.json()["detail"]

    def test_create_invitation_athlete_role_forbidden(self, sample_athlete_id):
        """Should return 403 when athlete role tries to create invitation."""
        from tests.conftest import TEST_ATHLETE_ID

        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id=TEST_ATHLETE_ID, role="athlete"
        )
        athlete_client = TestClient(app)

        response = athlete_client.post(
            "/api/v1/invitations/",
            json={"athlete_id": sample_athlete_id},
        )

        assert response.status_code == 403

        if original:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


class TestListInvitations:
    """Test GET /api/v1/invitations/"""

    def test_list_invitations(self, mock_supabase, sample_invite_data):
        """Should return list of invitations for the coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_invite_data
        ]

        response = client.get("/api/v1/invitations/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["invite_code"] == "ABC12345"

    def test_athlete_role_cannot_list(self):
        """Should return 403 when athlete role tries to list invitations."""
        from tests.conftest import TEST_ATHLETE_ID

        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(
            id=TEST_ATHLETE_ID, role="athlete"
        )
        athlete_client = TestClient(app)

        response = athlete_client.get("/api/v1/invitations/")

        assert response.status_code == 403

        if original:
            app.dependency_overrides[get_current_user] = original
        else:
            app.dependency_overrides.pop(get_current_user, None)


class TestValidateInvitation:
    """Test GET /api/v1/invitations/validate/{code}"""

    def test_validate_valid_code(self, mock_supabase, sample_invite_data):
        """Should return valid=True with athlete first name for valid code."""
        call_count = {"count": 0}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athlete_invitations":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    sample_invite_data
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"name": "John Doe"}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get("/api/v1/invitations/validate/ABC12345")

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["athlete_first_name"] == "John"
        assert "coach_email" not in data

    def test_validate_expired_code(self, mock_supabase, sample_invite_data):
        """Should return valid=False for expired invitation."""
        expired_invite = {
            **sample_invite_data,
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        }
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [expired_invite]

        response = client.get("/api/v1/invitations/validate/EXPIRED1")

        assert response.status_code == 200
        assert response.json()["valid"] is False

    def test_validate_used_code(self, mock_supabase, sample_invite_data):
        """Should return valid=False for already used invitation."""
        used_invite = {
            **sample_invite_data,
            "used_at": datetime.now(timezone.utc).isoformat(),
            "used_by": str(uuid4()),
        }
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [used_invite]

        response = client.get("/api/v1/invitations/validate/USED1234")

        assert response.status_code == 200
        assert response.json()["valid"] is False

    def test_validate_not_found(self, mock_supabase):
        """Should return valid=False for non-existent code."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get("/api/v1/invitations/validate/NOTFOUND")

        assert response.status_code == 200
        assert response.json()["valid"] is False


class TestRevokeInvitation:
    """Test DELETE /api/v1/invitations/{invitation_id}"""

    def test_revoke_invitation_success(self, mock_supabase, sample_invite_data):
        """Should delete unused invitation and return 204."""
        invitation_id = sample_invite_data["id"]

        call_count = {"athlete_invitations": 0}

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athlete_invitations":
                call_count["athlete_invitations"] += 1
                if call_count["athlete_invitations"] == 1:
                    # Select to verify ownership
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        sample_invite_data
                    ]
                else:
                    # Delete
                    mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/invitations/{invitation_id}")

        assert response.status_code == 204

    def test_revoke_invitation_not_owned(self, mock_supabase):
        """Should return 404 when invitation belongs to another coach."""
        invitation_id = str(uuid4())

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            {
                "id": invitation_id,
                "coach_id": str(uuid4()),  # Different coach
                "used_at": None,
            }
        ]

        response = client.delete(f"/api/v1/invitations/{invitation_id}")

        assert response.status_code == 404

    def test_revoke_used_invitation(self, mock_supabase, sample_invite_data):
        """Should return 400 when trying to revoke a used invitation."""
        used_invite = {
            **sample_invite_data,
            "used_at": datetime.now(timezone.utc).isoformat(),
        }
        invitation_id = used_invite["id"]

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [used_invite]

        response = client.delete(f"/api/v1/invitations/{invitation_id}")

        assert response.status_code == 400
        assert "used invitation" in response.json()["detail"].lower()

    def test_revoke_not_found(self, mock_supabase):
        """Should return 404 when invitation doesn't exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/invitations/{uuid4()}")

        assert response.status_code == 404
