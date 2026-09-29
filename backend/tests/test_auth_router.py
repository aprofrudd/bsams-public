"""Tests for auth router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client.

    Sign-in runs on a throwaway client (see `_auth_client`), so `create_client` is
    mocked to the same object as the cached singleton.
    """
    with patch("app.core.supabase_client.get_supabase_client") as mock_core, \
         patch("app.routers.auth.get_supabase_client") as mock_router, \
         patch("app.routers.auth.create_client") as mock_create:
        mock_client = MagicMock()
        mock_core.return_value = mock_client
        mock_router.return_value = mock_client
        mock_create.return_value = mock_client
        yield mock_client


class TestLogin:
    """Test POST /api/v1/auth/login."""

    def test_login_success(self, mock_supabase):
        """Should return user info and set HttpOnly cookie on successful login."""
        mock_session = MagicMock()
        mock_session.access_token = "test-jwt-token"
        mock_user = MagicMock()
        mock_user.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        mock_user.email = "test@example.com"

        mock_response = MagicMock()
        mock_response.session = mock_session
        mock_response.user = mock_user

        mock_supabase.auth.sign_in_with_password.return_value = mock_response

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "Password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" not in data
        assert data["user_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        assert data["email"] == "test@example.com"
        assert "access_token" in response.cookies

    def test_login_invalid_credentials(self, mock_supabase):
        """Should return 401 for invalid credentials."""
        mock_supabase.auth.sign_in_with_password.side_effect = Exception(
            "Invalid login"
        )

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "bad@example.com", "password": "Wrong123x"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    def test_login_missing_email(self):
        """Should return 422 for missing email."""
        response = client.post(
            "/api/v1/auth/login",
            json={"password": "Password123"},
        )
        assert response.status_code == 422

    def test_login_invalid_email_format(self):
        """Should return 422 for invalid email format."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "Password123"},
        )
        assert response.status_code == 422

    def test_login_no_supabase(self):
        """Should return 503 when Supabase not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Password123"},
            )
            assert response.status_code == 503


class TestSignup:
    """Test POST /api/v1/auth/signup."""

    def test_signup_success(self, mock_supabase):
        """Should return user info and set HttpOnly cookie on successful signup."""
        mock_session = MagicMock()
        mock_session.access_token = "new-jwt-token"
        mock_user = MagicMock()
        mock_user.id = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
        mock_user.email = "new@example.com"

        mock_response = MagicMock()
        mock_response.session = mock_session
        mock_response.user = mock_user

        mock_supabase.auth.sign_up.return_value = mock_response

        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "new@example.com", "password": "Password123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" not in data
        assert data["user_id"] == "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
        assert data["email"] == "new@example.com"
        assert "access_token" in response.cookies

    def test_signup_no_session(self, mock_supabase):
        """Should return 400 when signup requires email confirmation."""
        mock_response = MagicMock()
        mock_response.session = None

        mock_supabase.auth.sign_up.return_value = mock_response

        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "new@example.com", "password": "Password123"},
        )

        assert response.status_code == 400

    def test_signup_error(self, mock_supabase):
        """Should return 400 on signup failure."""
        mock_supabase.auth.sign_up.side_effect = Exception("User already exists")

        response = client.post(
            "/api/v1/auth/signup",
            json={"email": "existing@example.com", "password": "Password123"},
        )

        assert response.status_code == 400


class TestMe:
    """Test GET /api/v1/auth/me."""

    def test_me_returns_user_id(self):
        """Should return current user ID (dev mode)."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "00000000-0000-0000-0000-000000000001"


class TestLogout:
    """Test POST /api/v1/auth/logout."""

    def test_logout_success(self, mock_supabase):
        """Should return 204 on successful logout."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 204


class TestAuthRunsOnAThrowawayClient:
    """Signing a user in must never touch the cached service-role client.

    supabase 2.27.3 swaps a client's Authorization header to the signed-in user on
    SIGNED_IN (library client.py:334-346), so if login ran on the shared singleton
    every later query on that worker would run as the last person to log in, under
    their row-level security.
    """

    @staticmethod
    def _switching_singleton():
        """A stand-in for the cached client that mimics the library's header swap."""
        singleton = MagicMock()
        singleton.options.headers = {"Authorization": "Bearer service-role-key"}

        def _switch(*_args, **_kwargs):
            singleton.options.headers["Authorization"] = "Bearer signed-in-user-jwt"
            return TestAuthRunsOnAThrowawayClient._auth_result()

        singleton.auth.sign_in_with_password.side_effect = _switch
        singleton.auth.sign_up.side_effect = _switch
        return singleton

    @staticmethod
    def _auth_result():
        session = MagicMock()
        session.access_token = "user-jwt"
        user = MagicMock()
        user.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        user.email = "test@example.com"
        result = MagicMock()
        result.session = session
        result.user = user
        return result

    @staticmethod
    def _assert_single_request_client(mock_create):
        """The throwaway client lives for one request: no refresh loop, no stored session."""
        options = mock_create.call_args.kwargs["options"]
        assert options.auto_refresh_token is False
        assert options.persist_session is False

    def test_login_leaves_the_singleton_on_the_service_key(self):
        """Login authenticates on a fresh client, so the singleton keeps service-role access."""
        singleton = self._switching_singleton()
        auth_client = MagicMock()
        auth_client.auth.sign_in_with_password.return_value = self._auth_result()

        with patch("app.core.supabase_client.get_supabase_client", return_value=singleton), \
             patch("app.routers.auth.get_supabase_client", return_value=singleton), \
             patch("app.routers.auth.create_client", return_value=auth_client) as mock_create:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "test@example.com", "password": "Password123"},
            )

        assert response.status_code == 200
        singleton.auth.sign_in_with_password.assert_not_called()
        assert singleton.options.headers["Authorization"] == "Bearer service-role-key"
        auth_client.auth.sign_in_with_password.assert_called_once()
        self._assert_single_request_client(mock_create)

    def test_signup_leaves_the_singleton_on_the_service_key(self):
        """Signup authenticates on a fresh client, so the singleton keeps service-role access."""
        singleton = self._switching_singleton()
        auth_client = MagicMock()
        auth_client.auth.sign_up.return_value = self._auth_result()

        with patch("app.core.supabase_client.get_supabase_client", return_value=singleton), \
             patch("app.routers.auth.get_supabase_client", return_value=singleton), \
             patch("app.routers.auth.create_client", return_value=auth_client) as mock_create:
            response = client.post(
                "/api/v1/auth/signup",
                json={"email": "test@example.com", "password": "Password123"},
            )

        assert response.status_code == 200
        singleton.auth.sign_up.assert_not_called()
        assert singleton.options.headers["Authorization"] == "Bearer service-role-key"
        auth_client.auth.sign_up.assert_called_once()
        self._assert_single_request_client(mock_create)


class TestLoginRateLimit:
    """The login limit is a flood guard, not the brute-force guard."""

    def test_six_sign_ins_in_a_row_are_not_throttled(self, mock_supabase):
        """Every device reaches the API through one proxy address, so a room of iPads
        signing in shares one bucket. Per-account guessing stays with the email-keyed
        lockout, which is why the address limit can be loose."""
        mock_supabase.auth.sign_in_with_password.side_effect = Exception("Invalid login")

        statuses = [
            client.post(
                "/api/v1/auth/login",
                json={"email": f"ipad{i}@example.com", "password": "Wrong123x"},
            ).status_code
            for i in range(6)
        ]

        assert statuses == [401] * 6
