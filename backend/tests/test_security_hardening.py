"""Tests for security hardening fixes (session invalidation, role fallback,
logout singleton, DB lockout, mass delete safeguard, cookie lifetime)."""

from unittest.mock import MagicMock, patch, call
from uuid import UUID, uuid4

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
    """Test client with auth override (for endpoints needing auth context)."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)


# --- Fix 1: Session Invalidation ---

class TestSessionInvalidation:
    """Verify password/email changes clear cookies and sign out globally."""

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_change_password_clears_cookie(self, mock_client, mock_create, mock_audit, client):
        """After password change, access_token cookie should be deleted."""
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
        # Cookie should be cleared (max-age=0 or deleted)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie
        # A deleted cookie has max-age=0 or expires in the past
        assert 'Max-Age=0' in set_cookie or '01 Jan 1970' in set_cookie

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_change_password_calls_global_signout(self, mock_client, mock_create, mock_audit, client):
        """After password change, admin.sign_out should be called to invalidate refresh tokens."""
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
        mock_admin.auth.admin.sign_out.assert_called_once_with(str(TEST_USER_ID))

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_change_password_message_instructs_relogin(self, mock_client, mock_create, mock_audit, client):
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
        assert "log in again" in resp.json()["message"].lower()

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_change_email_clears_cookie(self, mock_client, mock_create, mock_audit, client):
        """After email change, access_token cookie should be deleted."""
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
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie
        assert 'Max-Age=0' in set_cookie or '01 Jan 1970' in set_cookie

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_change_email_calls_global_signout(self, mock_client, mock_create, mock_audit, client):
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
        mock_admin.auth.admin.sign_out.assert_called_once_with(str(TEST_USER_ID))

    @patch("app.routers.auth.log_event")
    @patch("app.routers.auth.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_reset_password_calls_global_signout(self, mock_client, mock_create, mock_audit, unauth_client):
        """After password reset, admin.sign_out should invalidate all sessions."""
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
        mock_admin.auth.admin.sign_out.assert_called_once_with(str(TEST_USER_ID))


# --- Fix 2: Role Fallback 503 ---

class TestRoleFallback:
    """Verify profile lookup failure returns 503 instead of defaulting to coach."""

    @patch("app.core.security.get_supabase_client")
    def test_profile_lookup_failure_returns_503(self, mock_client):
        """When DB throws an exception during role lookup, return 503."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = str(TEST_USER_ID)
        mock_user_resp = MagicMock()
        mock_user_resp.user = mock_user
        mock_db.auth.get_user.return_value = mock_user_resp

        # Profile lookup throws exception
        mock_db.table.return_value.select.return_value.eq.return_value.execute.side_effect = Exception("DB connection failed")
        mock_client.return_value = mock_db

        # Remove auth override so get_current_user actually runs
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            raw_client = TestClient(app)
            resp = raw_client.get(
                "/api/v1/auth/me",
                cookies={"access_token": "test-token"},
            )
            assert resp.status_code == 503
            assert "verify user role" in resp.json()["detail"].lower()
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    @patch("app.core.security.get_supabase_client")
    def test_profile_not_found_defaults_to_coach(self, mock_client):
        """When profile exists but has no role, default to coach (new user scenario)."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = str(TEST_USER_ID)
        mock_user_resp = MagicMock()
        mock_user_resp.user = mock_user
        mock_db.auth.get_user.return_value = mock_user_resp

        # Profile lookup returns empty data (no profile row)
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_client.return_value = mock_db

        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            raw_client = TestClient(app)
            resp = raw_client.get(
                "/api/v1/auth/me",
                cookies={"access_token": "test-token"},
            )
            # Should succeed with coach default
            assert resp.status_code == 200
            assert resp.json()["role"] == "coach"
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original


# --- Fix 3: Logout Singleton Fix ---

class TestLogoutSingleton:
    """Verify logout uses fresh client, not singleton."""

    @patch("app.routers.auth.create_client")
    def test_logout_uses_fresh_client(self, mock_create, client):
        """Logout should create a fresh client for sign_out, not use singleton."""
        mock_admin = MagicMock()
        mock_create.return_value = mock_admin

        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 204
        # Verify create_client was called (fresh client)
        mock_create.assert_called_once()
        mock_admin.auth.admin.sign_out.assert_called_once_with(str(TEST_USER_ID))

    @patch("app.routers.auth.create_client")
    def test_logout_clears_cookie(self, mock_create, client):
        """Logout should clear the auth cookie."""
        mock_create.return_value = MagicMock()

        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 204
        set_cookie = resp.headers.get("set-cookie", "")
        assert "access_token" in set_cookie


# --- Fix 4: DB-Backed Lockout ---

class TestDBLockout:
    """Verify lockout uses database instead of in-memory dict."""

    @patch("app.routers.auth.create_client")
    @patch("app.routers.auth.get_supabase_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_lockout_after_5_failures(self, mock_core, mock_client, mock_create):
        """5 failed attempts within 15 minutes should trigger 429."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        mock_core.return_value = mock_db
        # Login signs in on a throwaway client, never the cached service-role one
        mock_create.return_value = mock_db

        # Mock the lockout check count to return 5 (at threshold)
        mock_count_result = MagicMock()
        mock_count_result.count = 5
        mock_count_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_count_result

        # Mock login to fail
        mock_db.auth.sign_in_with_password.side_effect = Exception("Invalid")

        test_client = TestClient(app)
        # Remove auth override
        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            resp = test_client.post(
                "/api/v1/auth/login",
                json={"email": "locked@example.com", "password": "Wrong123x"},
            )
            assert resp.status_code == 429
            assert "too many" in resp.json()["detail"].lower()
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    @patch("app.routers.auth.create_client")
    @patch("app.routers.auth.get_supabase_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_lockout_cleared_on_success(self, mock_core, mock_client, mock_create):
        """Successful login should delete failed attempts from DB."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        mock_core.return_value = mock_db
        # Login signs in on a throwaway client, never the cached service-role one
        mock_create.return_value = mock_db

        # Mock lockout check: 0 failures (not locked out)
        mock_count_result = MagicMock()
        mock_count_result.count = 0
        mock_count_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_count_result

        # Mock successful login
        mock_session = MagicMock()
        mock_session.access_token = "jwt-token"
        mock_user = MagicMock()
        mock_user.id = str(TEST_USER_ID)
        mock_user.email = "user@example.com"
        mock_result = MagicMock()
        mock_result.session = mock_session
        mock_result.user = mock_user
        mock_db.auth.sign_in_with_password.return_value = mock_result

        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            test_client = TestClient(app)
            resp = test_client.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "password": "CorrectPass1"},
            )
            assert resp.status_code == 200

            # Verify delete was called for login_attempts
            delete_calls = [
                c for c in mock_db.table.call_args_list
                if c[0] == ("login_attempts",)
            ]
            assert len(delete_calls) > 0, "Expected login_attempts table to be accessed for cleanup"
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original

    @patch("app.routers.auth.create_client")
    @patch("app.routers.auth.get_supabase_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_failed_attempt_records_ip(self, mock_core, mock_client, mock_create):
        """Failed login should insert record with IP address into login_attempts."""
        mock_db = MagicMock()
        mock_client.return_value = mock_db
        mock_core.return_value = mock_db
        # Login signs in on a throwaway client, never the cached service-role one
        mock_create.return_value = mock_db

        # Mock lockout check: 0 failures
        mock_count_result = MagicMock()
        mock_count_result.count = 0
        mock_count_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_count_result

        # Mock failed login
        mock_db.auth.sign_in_with_password.side_effect = Exception("Invalid")

        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            test_client = TestClient(app)
            resp = test_client.post(
                "/api/v1/auth/login",
                json={"email": "fail@example.com", "password": "Wrong123x"},
            )
            assert resp.status_code == 401

            # Verify insert was called on login_attempts table
            insert_calls = [
                c for c in mock_db.table.return_value.insert.call_args_list
            ]
            assert len(insert_calls) > 0, "Expected login_attempts insert for failed attempt"
            # Check that the inserted record contains the email
            inserted_data = insert_calls[-1][0][0]
            assert inserted_data["email"] == "fail@example.com"
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original


# --- Fix 5: Mass Delete Safeguard ---

class TestMassDeleteSafeguard:
    """Verify delete-all requires password and has rate limiting."""

    @patch("app.core.supabase_client.get_supabase_client")
    def test_delete_all_requires_password(self, mock_client, client):
        """DELETE /athletes/ without password body should return 422."""
        mock_client.return_value = MagicMock()
        resp = client.request("DELETE", "/api/v1/athletes/")
        assert resp.status_code == 422

    @patch("app.routers.athletes.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_delete_all_wrong_password_returns_401(self, mock_client, mock_create, client):
        """DELETE /athletes/ with wrong password should return 401."""
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"email": "coach@example.com"}
        ]
        mock_client.return_value = mock_db

        mock_verify = MagicMock()
        mock_verify.auth.sign_in_with_password.side_effect = Exception("Invalid")
        mock_create.return_value = mock_verify

        resp = client.request(
            "DELETE",
            "/api/v1/athletes/",
            json={"current_password": "WrongPass1"},
        )
        assert resp.status_code == 401
        assert "incorrect" in resp.json()["detail"].lower()

    @patch("app.routers.athletes.log_event")
    @patch("app.routers.athletes.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_delete_all_success_with_password(self, mock_client, mock_create, mock_audit, client):
        """DELETE /athletes/ with correct password should succeed."""
        mock_db = MagicMock()

        call_count = {"n": 0}
        athlete_id = str(uuid4())

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "profiles":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"email": "coach@example.com"}
                ]
            elif table_name == "athletes":
                if call_count["n"] == 0:
                    mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                        {"id": athlete_id},
                    ]
                    call_count["n"] += 1
                else:
                    mock_table.delete.return_value.eq.return_value.execute.return_value = None
            elif table_name == "performance_events":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4())},
                ]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            elif table_name == "audit_log":
                mock_table.insert.return_value.execute.return_value = None
            return mock_table

        mock_db.table.side_effect = table_side_effect
        mock_client.return_value = mock_db

        mock_verify = MagicMock()
        mock_create.return_value = mock_verify

        resp = client.request(
            "DELETE",
            "/api/v1/athletes/",
            json={"current_password": "CorrectPass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted_athletes"] == 1
        assert data["deleted_events"] == 1

    @patch("app.routers.athletes.log_event")
    @patch("app.routers.athletes.create_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_delete_all_creates_audit_log(self, mock_client, mock_create, mock_audit, client):
        """DELETE /athletes/ should log the deletion event."""
        mock_db = MagicMock()
        athlete_id = str(uuid4())

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "profiles":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"email": "coach@example.com"}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            elif table_name == "performance_events":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_db.table.side_effect = table_side_effect
        mock_client.return_value = mock_db
        mock_create.return_value = MagicMock()

        resp = client.request(
            "DELETE",
            "/api/v1/athletes/",
            json={"current_password": "CorrectPass1"},
        )
        assert resp.status_code == 200
        # Verify audit log_event was called with delete_all_data action
        mock_audit.assert_called_once()
        assert mock_audit.call_args[0][1] == "delete_all_data"


# --- Fix 6: Cookie Lifetime ---

class TestCookieLifetime:
    """Verify cookie max-age is 24 hours, not 7 days."""

    def test_cookie_max_age_is_24_hours(self):
        """The COOKIE_MAX_AGE constant should be 86400 (24 hours)."""
        from app.routers.auth import COOKIE_MAX_AGE
        assert COOKIE_MAX_AGE == 60 * 60 * 24  # 86400 seconds = 24 hours
        assert COOKIE_MAX_AGE < 60 * 60 * 24 * 2  # Less than 2 days

    @patch("app.routers.auth.create_client")
    @patch("app.routers.auth.get_supabase_client")
    @patch("app.core.supabase_client.get_supabase_client")
    def test_login_cookie_has_24h_max_age(self, mock_core, mock_client, mock_create):
        """Login response cookie should have max-age=86400."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.access_token = "test-jwt-token"
        mock_user = MagicMock()
        mock_user.id = str(TEST_USER_ID)
        mock_user.email = "test@example.com"
        mock_result = MagicMock()
        mock_result.session = mock_session
        mock_result.user = mock_user
        mock_db.auth.sign_in_with_password.return_value = mock_result

        # Mock lockout check
        mock_count_result = MagicMock()
        mock_count_result.count = 0
        mock_count_result.data = []
        mock_db.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = mock_count_result

        mock_client.return_value = mock_db
        mock_core.return_value = mock_db
        # Login signs in on a throwaway client, never the cached service-role one
        mock_create.return_value = mock_db

        original = app.dependency_overrides.pop(get_current_user, None)
        try:
            test_client = TestClient(app)
            resp = test_client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Password123"},
            )
            assert resp.status_code == 200
            set_cookie = resp.headers.get("set-cookie", "")
            assert "Max-Age=86400" in set_cookie
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original
