"""Tests for security module."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.security import AuthenticatedUser, get_current_user


def _make_request(cookies=None):
    """Create a mock Request object."""
    mock_request = MagicMock()
    mock_request.cookies = cookies or {}
    return mock_request


class TestGetCurrentUserBearerToken:
    """Test get_current_user with Authorization header."""

    @pytest.mark.asyncio
    async def test_missing_credentials_raises_401(self):
        """Should raise 401 when no credentials provided."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=_make_request(), credentials=None)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Not authenticated"

    @pytest.mark.asyncio
    async def test_valid_token_returns_authenticated_user(self):
        """Should return AuthenticatedUser for a valid token."""
        mock_creds = MagicMock()
        mock_creds.credentials = "valid-token"

        mock_user = MagicMock()
        mock_user.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_profile_result = MagicMock()
        mock_profile_result.data = [{"role": "coach"}]

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_response
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_profile_result

        with patch("app.core.security.get_supabase_client", return_value=mock_client):
            result = await get_current_user(request=_make_request(), credentials=mock_creds)
            assert isinstance(result, AuthenticatedUser)
            assert str(result.id) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            assert result.role == "coach"
            mock_client.auth.get_user.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        """Should raise 401 for an invalid token."""
        mock_creds = MagicMock()
        mock_creds.credentials = "bad-token"

        mock_client = MagicMock()
        mock_client.auth.get_user.side_effect = Exception("Invalid JWT")

        with patch("app.core.security.get_supabase_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request=_make_request(), credentials=mock_creds)
            assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_no_supabase_client_raises_503(self):
        """Should raise 503 when Supabase client not configured."""
        mock_creds = MagicMock()
        mock_creds.credentials = "some-token"

        with patch("app.core.security.get_supabase_client", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request=_make_request(), credentials=mock_creds)
            assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_null_user_raises_401(self):
        """Should raise 401 when Supabase returns null user."""
        mock_creds = MagicMock()
        mock_creds.credentials = "some-token"

        mock_response = MagicMock()
        mock_response.user = None

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_response

        with patch("app.core.security.get_supabase_client", return_value=mock_client):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(request=_make_request(), credentials=mock_creds)
            assert exc_info.value.status_code == 401


class TestGetCurrentUserCookie:
    """Test get_current_user with HttpOnly cookie."""

    @pytest.mark.asyncio
    async def test_reads_token_from_cookie(self):
        """Should read JWT from access_token cookie."""
        mock_user = MagicMock()
        mock_user.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_profile_result = MagicMock()
        mock_profile_result.data = [{"role": "admin"}]

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_response
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_profile_result

        request = _make_request(cookies={"access_token": "cookie-token"})

        with patch("app.core.security.get_supabase_client", return_value=mock_client):
            result = await get_current_user(request=request, credentials=None)
            assert isinstance(result, AuthenticatedUser)
            assert str(result.id) == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
            assert result.role == "admin"
            mock_client.auth.get_user.assert_called_once_with("cookie-token")

    @pytest.mark.asyncio
    async def test_cookie_takes_priority_over_header(self):
        """Cookie should be used even when header is present."""
        mock_creds = MagicMock()
        mock_creds.credentials = "header-token"

        mock_user = MagicMock()
        mock_user.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_response

        request = _make_request(cookies={"access_token": "cookie-token"})

        with patch("app.core.security.get_supabase_client", return_value=mock_client):
            await get_current_user(request=request, credentials=mock_creds)
            mock_client.auth.get_user.assert_called_once_with("cookie-token")

    @pytest.mark.asyncio
    async def test_falls_back_to_header_when_no_cookie(self):
        """Should use Authorization header when no cookie present."""
        mock_creds = MagicMock()
        mock_creds.credentials = "header-token"

        mock_user = MagicMock()
        mock_user.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        mock_response = MagicMock()
        mock_response.user = mock_user

        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = mock_response

        with patch("app.core.security.get_supabase_client", return_value=mock_client):
            await get_current_user(request=_make_request(), credentials=mock_creds)
            mock_client.auth.get_user.assert_called_once_with("header-token")


# ───────────────────────────────────────────────────────────────
# Security Hardening Tests (Phase 1)
# ───────────────────────────────────────────────────────────────

from fastapi.testclient import TestClient
from app.main import app

_client = TestClient(app)


class TestPasswordValidation:
    """Test password strength requirements."""

    def test_short_password_rejected(self):
        """Password under 8 chars is rejected."""
        resp = _client.post("/api/v1/auth/signup", json={"email": "test@example.com", "password": "Abc123"})
        assert resp.status_code == 422

    def test_no_uppercase_rejected(self):
        """Password without uppercase is rejected."""
        resp = _client.post("/api/v1/auth/signup", json={"email": "test@example.com", "password": "abcdefg1"})
        assert resp.status_code == 422

    def test_no_digit_rejected(self):
        """Password without digit is rejected."""
        resp = _client.post("/api/v1/auth/signup", json={"email": "test@example.com", "password": "Abcdefgh"})
        assert resp.status_code == 422

    def test_valid_password_accepted(self):
        """Valid password passes validation (may fail at auth service level, but not 422)."""
        resp = _client.post("/api/v1/auth/signup", json={"email": "test@example.com", "password": "Abcdefg1"})
        # Should NOT be 422 (validation error) — may be 503 (no Supabase) or other
        assert resp.status_code != 422

    def test_login_accepts_weak_password(self):
        """Login should not enforce password strength (users may have legacy passwords)."""
        resp = _client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "abc"})
        # Should NOT be 422 — may be 503 (no Supabase) or 401, but not a validation error
        assert resp.status_code != 422

    def test_athlete_signup_short_password_rejected(self):
        """Athlete signup: password under 8 chars is rejected."""
        resp = _client.post("/api/v1/auth/signup/athlete", json={
            "email": "athlete@example.com",
            "password": "Abc1",
            "invite_code": "TESTCODE",
        })
        assert resp.status_code == 422

    def test_athlete_signup_no_uppercase_rejected(self):
        """Athlete signup: password without uppercase is rejected."""
        resp = _client.post("/api/v1/auth/signup/athlete", json={
            "email": "athlete@example.com",
            "password": "abcdefg1",
            "invite_code": "TESTCODE",
        })
        assert resp.status_code == 422

    def test_athlete_signup_no_digit_rejected(self):
        """Athlete signup: password without digit is rejected."""
        resp = _client.post("/api/v1/auth/signup/athlete", json={
            "email": "athlete@example.com",
            "password": "Abcdefgh",
            "invite_code": "TESTCODE",
        })
        assert resp.status_code == 422


class TestSecurityHeaders:
    """Test security response headers."""

    def test_security_headers_present(self):
        """Key security headers are set on responses."""
        resp = _client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in resp.headers.get("Permissions-Policy", "")

    def test_csp_header_present(self):
        """Content-Security-Policy header is set."""
        resp = _client.get("/health")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "default-src" in csp


class TestErrorSanitization:
    """Test that internal errors don't leak to clients."""

    def test_signup_error_sanitized(self):
        """Signup errors don't expose internal details."""
        # With no Supabase configured, should get 503 not a leaked error
        resp = _client.post("/api/v1/auth/signup", json={"email": "test@example.com", "password": "ValidPass1"})
        if resp.status_code >= 400:
            detail = resp.json().get("detail", "")
            assert "traceback" not in detail.lower()
            assert "exception" not in detail.lower()


class TestInvitationSanitization:
    """Test invitation validation doesn't leak coach info."""

    def test_validate_no_coach_email(self):
        """Validation response should not contain coach_email."""
        resp = _client.get("/api/v1/invitations/validate/FAKECODE")
        data = resp.json()
        assert "coach_email" not in data
