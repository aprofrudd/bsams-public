"""Tests for account management endpoints (forgot/reset/change password, change email)."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app
from tests.conftest import TEST_USER_ID, override_get_current_user


@pytest.fixture
def client():
    """Standard test client with coach auth override."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)


@pytest.fixture
def unauth_client():
    """Test client with no auth override (for unauthenticated endpoints)."""
    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    if original:
        app.dependency_overrides[get_current_user] = original


# --- Forgot Password Tests ---

class TestForgotPassword:
    """Tests for POST /auth/forgot-password."""

    @patch("app.routers.auth.get_supabase_client")
    def test_returns_200_for_valid_email(self, mock_client, unauth_client):
        mock_db = MagicMock()
        mock_client.return_value = mock_db

        resp = unauth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "user@example.com"},
        )
        assert resp.status_code == 200
        assert "reset link has been sent" in resp.json()["message"]
        mock_db.auth.reset_password_email.assert_called_once()

    @patch("app.routers.auth.get_supabase_client")
    def test_returns_200_for_unknown_email(self, mock_client, unauth_client):
        """No email enumeration — same response for unknown emails."""
        mock_db = MagicMock()
        mock_db.auth.reset_password_email.side_effect = Exception("User not found")
        mock_client.return_value = mock_db

        resp = unauth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )
        assert resp.status_code == 200
        assert "reset link has been sent" in resp.json()["message"]

    @patch("app.routers.auth.get_supabase_client")
    def test_returns_200_on_supabase_error(self, mock_client, unauth_client):
        """No enumeration even on service errors."""
        mock_client.return_value = None

        resp = unauth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "user@example.com"},
        )
        assert resp.status_code == 200

    def test_returns_422_for_invalid_email(self, unauth_client):
        resp = unauth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422

    def test_returns_422_for_missing_email(self, unauth_client):
        resp = unauth_client.post(
            "/api/v1/auth/forgot-password",
            json={},
        )
        assert resp.status_code == 422


# --- Reset Password Tests ---

class TestResetPassword:
    """Tests for POST /auth/reset-password."""

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_success_with_valid_token(self, mock_client, mock_create, mock_audit, unauth_client):
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = TEST_USER_ID
        mock_user.email = "user@example.com"
        mock_user_resp = MagicMock()
        mock_user_resp.user = mock_user
        mock_db.auth.get_user.return_value = mock_user_resp
        mock_client.return_value = mock_db

        mock_admin = MagicMock()
        mock_create.return_value = mock_admin

        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"access_token": "valid-token", "new_password": "NewPass1"},
        )
        assert resp.status_code == 200
        assert "reset successfully" in resp.json()["message"]
        mock_admin.auth.admin.update_user_by_id.assert_called_once()

    @patch("app.core.supabase_client.get_supabase_client")
    def test_invalid_token_returns_401(self, mock_client, unauth_client):
        mock_db = MagicMock()
        mock_db.auth.get_user.side_effect = Exception("Invalid token")
        mock_client.return_value = mock_db

        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"access_token": "bad-token", "new_password": "NewPass1"},
        )
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()

    def test_weak_password_returns_422(self, unauth_client):
        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"access_token": "valid-token", "new_password": "weak"},
        )
        assert resp.status_code == 422

    def test_missing_token_and_code_returns_422(self, unauth_client):
        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"new_password": "NewPass1"},
        )
        assert resp.status_code == 422

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_success_with_pkce_code(self, mock_client, mock_create, mock_audit, unauth_client):
        """PKCE flow: code is exchanged for session, then password is updated."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db

        # First create_client call: PKCE code exchange
        mock_pkce = MagicMock()
        mock_session = MagicMock()
        mock_session.access_token = "exchanged-token"
        mock_session_resp = MagicMock()
        mock_session_resp.session = mock_session
        mock_pkce.auth.exchange_code_for_session.return_value = mock_session_resp

        # Second create_client call: admin password update
        mock_admin = MagicMock()
        mock_create.side_effect = [mock_pkce, mock_admin]

        # Mock get_user with the exchanged token
        mock_user = MagicMock()
        mock_user.id = TEST_USER_ID
        mock_user.email = "user@example.com"
        mock_user_resp = MagicMock()
        mock_user_resp.user = mock_user
        mock_db.auth.get_user.return_value = mock_user_resp

        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"code": "pkce-auth-code", "new_password": "NewPass1"},
        )
        assert resp.status_code == 200
        assert "reset successfully" in resp.json()["message"]
        mock_pkce.auth.exchange_code_for_session.assert_called_once_with(
            {"auth_code": "pkce-auth-code"}
        )
        mock_db.auth.get_user.assert_called_once_with("exchanged-token")

    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_invalid_pkce_code_returns_401(self, mock_client, mock_create, unauth_client):
        mock_db = MagicMock()
        mock_client.return_value = mock_db

        mock_pkce = MagicMock()
        mock_pkce.auth.exchange_code_for_session.side_effect = Exception("Invalid code")
        mock_create.return_value = mock_pkce

        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"code": "bad-code", "new_password": "NewPass1"},
        )
        assert resp.status_code == 401

    @patch("app.core.supabase_client.get_supabase_client")
    def test_no_auth_cookie_on_success(self, mock_client, unauth_client):
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = TEST_USER_ID
        mock_user.email = "user@example.com"
        mock_user_resp = MagicMock()
        mock_user_resp.user = mock_user
        mock_db.auth.get_user.return_value = mock_user_resp
        mock_client.return_value = mock_db

        with patch("app.routers.auth.create_client") as mock_create:
            mock_create.return_value = MagicMock()
            resp = unauth_client.post(
                "/api/v1/auth/reset-password",
                json={"access_token": "valid-token", "new_password": "NewPass1"},
            )
        assert resp.status_code == 200
        # Should NOT set access_token cookie (force re-login)
        assert "access_token" not in resp.cookies

    @patch("app.core.supabase_client.get_supabase_client")
    def test_supabase_unavailable_returns_503(self, mock_client, unauth_client):
        mock_client.return_value = None

        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"access_token": "valid-token", "new_password": "NewPass1"},
        )
        assert resp.status_code == 503


# --- Change Password Tests ---

class TestChangePassword:
    """Tests for POST /auth/change-password."""

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_success_with_correct_password(self, mock_client, mock_create, mock_audit, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "coach@example.com"}
        ]
        mock_client.return_value = mock_db

        mock_verify = MagicMock()
        mock_admin = MagicMock()
        mock_create.side_effect = [mock_verify, mock_admin]

        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1", "new_password": "NewPass1"},
        )
        assert resp.status_code == 200
        assert "changed successfully" in resp.json()["message"]
        mock_verify.auth.sign_in_with_password.assert_called_once()
        mock_admin.auth.admin.update_user_by_id.assert_called_once()

    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_wrong_current_password_returns_401(self, mock_client, mock_create, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "coach@example.com"}
        ]
        mock_client.return_value = mock_db

        mock_verify = MagicMock()
        mock_verify.auth.sign_in_with_password.side_effect = Exception("Invalid")
        mock_create.return_value = mock_verify

        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "WrongPass1", "new_password": "NewPass1"},
        )
        assert resp.status_code == 401
        assert "incorrect" in resp.json()["detail"].lower()

    def test_weak_new_password_returns_422(self, client):
        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1", "new_password": "weak"},
        )
        assert resp.status_code == 422

    def test_unauthenticated_returns_401(self):
        """No auth override — should get 401."""
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            raw_client = TestClient(app)
            resp = raw_client.post(
                "/api/v1/auth/change-password",
                json={"current_password": "OldPass1", "new_password": "NewPass1"},
            )
            assert resp.status_code == 401
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_audit_log_created(self, mock_client, mock_create, mock_audit, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "coach@example.com"}
        ]
        mock_client.return_value = mock_db
        mock_create.return_value = MagicMock()

        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1", "new_password": "NewPass1"},
        )
        assert resp.status_code == 200
        mock_audit.assert_called_once()
        assert mock_audit.call_args[0][1] == "password_changed"

    @patch("app.core.supabase_client.get_supabase_client")
    def test_supabase_unavailable_returns_503(self, mock_client, client):
        mock_client.return_value = None

        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1", "new_password": "NewPass1"},
        )
        assert resp.status_code == 503


# --- Change Email Tests ---

class TestChangeEmail:
    """Tests for POST /auth/change-email."""

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_success_updates_auth_and_profiles(self, mock_client, mock_create, mock_audit, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "old@example.com"}
        ]
        mock_client.return_value = mock_db

        mock_verify = MagicMock()
        mock_admin = MagicMock()
        mock_create.side_effect = [mock_verify, mock_admin]

        resp = client.post(
            "/api/v1/auth/change-email",
            json={"current_password": "OldPass1", "new_email": "new@example.com"},
        )
        assert resp.status_code == 200
        assert "changed successfully" in resp.json()["message"]
        mock_admin.auth.admin.update_user_by_id.assert_called_once()

    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_wrong_password_returns_401(self, mock_client, mock_create, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "old@example.com"}
        ]
        mock_client.return_value = mock_db

        mock_verify = MagicMock()
        mock_verify.auth.sign_in_with_password.side_effect = Exception("Invalid")
        mock_create.return_value = mock_verify

        resp = client.post(
            "/api/v1/auth/change-email",
            json={"current_password": "WrongPass1", "new_email": "new@example.com"},
        )
        assert resp.status_code == 401

    def test_invalid_email_returns_422(self, client):
        resp = client.post(
            "/api/v1/auth/change-email",
            json={"current_password": "OldPass1", "new_email": "not-an-email"},
        )
        assert resp.status_code == 422

    def test_unauthenticated_returns_401(self):
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            raw_client = TestClient(app)
            resp = raw_client.post(
                "/api/v1/auth/change-email",
                json={"current_password": "OldPass1", "new_email": "new@example.com"},
            )
            assert resp.status_code == 401
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_profiles_table_updated(self, mock_client, mock_create, mock_audit, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "old@example.com"}
        ]
        # Track update calls
        update_chain = MagicMock()
        mock_db.table.return_value.update.return_value.eq.return_value.execute = update_chain
        mock_client.return_value = mock_db

        mock_create.return_value = MagicMock()

        resp = client.post(
            "/api/v1/auth/change-email",
            json={"current_password": "OldPass1", "new_email": "new@example.com"},
        )
        assert resp.status_code == 200
        # Verify profiles table was updated
        mock_db.table.return_value.update.assert_called()

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_audit_log_created(self, mock_client, mock_create, mock_audit, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "old@example.com"}
        ]
        mock_client.return_value = mock_db
        mock_create.return_value = MagicMock()

        resp = client.post(
            "/api/v1/auth/change-email",
            json={"current_password": "OldPass1", "new_email": "new@example.com"},
        )
        assert resp.status_code == 200
        mock_audit.assert_called_once()
        assert mock_audit.call_args[0][1] == "email_changed"

    @patch("app.core.supabase_client.get_supabase_client")
    def test_supabase_unavailable_returns_503(self, mock_client, client):
        mock_client.return_value = None

        resp = client.post(
            "/api/v1/auth/change-email",
            json={"current_password": "OldPass1", "new_email": "new@example.com"},
        )
        assert resp.status_code == 503


# --- /me Endpoint Tests ---

class TestMeEndpoint:
    """Tests for GET /auth/me email inclusion."""

    @patch("app.routers.auth.get_supabase_client")
    def test_returns_email_in_response(self, mock_client, client):
        mock_db = MagicMock()
        # Profile lookup
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "coach@example.com"}
        ]
        mock_client.return_value = mock_db

        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == "coach@example.com"

    @patch("app.routers.auth.get_supabase_client")
    def test_returns_empty_email_if_no_profile(self, mock_client, client):
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_client.return_value = mock_db

        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 200
        assert resp.json()["email"] == ""


# --- Schema Validation Tests ---

class TestSchemaValidation:
    """Test password strength validation on new schemas."""

    def test_reset_password_rejects_weak_password(self, unauth_client):
        resp = unauth_client.post(
            "/api/v1/auth/reset-password",
            json={"access_token": "some-token", "new_password": "nouppercaseordigit"},
        )
        assert resp.status_code == 422

    def test_change_password_rejects_no_digit(self, client):
        resp = client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1", "new_password": "NoDigitHere"},
        )
        assert resp.status_code == 422
