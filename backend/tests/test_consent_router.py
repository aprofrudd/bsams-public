"""Tests for consent router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_USER_ID

client = TestClient(app)


class TestGetConsent:
    """Test GET /consent endpoint."""

    def test_returns_default_when_no_consent_record(self):
        """Should return disabled consent when no record exists."""
        mock_result = MagicMock()
        mock_result.data = []

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = client.get("/api/v1/consent/")

        assert response.status_code == 200
        data = response.json()
        assert data["data_sharing_enabled"] is False
        assert "info_text" in data

    def test_returns_existing_consent(self):
        """Should return existing consent status."""
        mock_result = MagicMock()
        mock_result.data = [{
            "data_sharing_enabled": True,
            "consented_at": "2024-01-01T00:00:00Z",
            "revoked_at": None,
        }]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_result

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = client.get("/api/v1/consent/")

        assert response.status_code == 200
        data = response.json()
        assert data["data_sharing_enabled"] is True
        assert data["consented_at"] == "2024-01-01T00:00:00Z"

    def test_returns_503_when_db_not_configured(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get("/api/v1/consent/")

        assert response.status_code == 503


class TestUpdateConsent:
    """Test PUT /consent endpoint."""

    def test_creates_consent_when_none_exists(self):
        """Should create a new consent record when opting in."""
        mock_existing = MagicMock()
        mock_existing.data = []

        mock_insert_result = MagicMock()
        mock_insert_result.data = [{
            "data_sharing_enabled": True,
            "consented_at": "2024-01-01T00:00:00Z",
            "revoked_at": None,
        }]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_insert_result

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = client.put(
                "/api/v1/consent/",
                json={"data_sharing_enabled": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data_sharing_enabled"] is True

    def test_updates_existing_consent(self):
        """Should update existing consent record."""
        mock_existing = MagicMock()
        mock_existing.data = [{"id": "some-id"}]

        mock_update_result = MagicMock()
        mock_update_result.data = [{
            "data_sharing_enabled": False,
            "consented_at": "2024-01-01T00:00:00Z",
            "revoked_at": "2024-02-01T00:00:00Z",
        }]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_update_result

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = client.put(
                "/api/v1/consent/",
                json={"data_sharing_enabled": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data_sharing_enabled"] is False

    def test_returns_503_when_db_not_configured(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.put(
                "/api/v1/consent/",
                json={"data_sharing_enabled": True},
            )

        assert response.status_code == 503

    def test_revoke_then_regrant_consent(self):
        """Should be able to revoke and then re-grant consent."""
        # First: revoke (update existing to false)
        mock_existing = MagicMock()
        mock_existing.data = [{"id": "some-id"}]

        mock_revoke_result = MagicMock()
        mock_revoke_result.data = [{
            "data_sharing_enabled": False,
            "consented_at": "2024-01-01T00:00:00Z",
            "revoked_at": "2024-02-01T00:00:00Z",
        }]

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_revoke_result

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = client.put(
                "/api/v1/consent/",
                json={"data_sharing_enabled": False},
            )

        assert response.status_code == 200
        assert response.json()["data_sharing_enabled"] is False

        # Second: re-grant (update existing to true)
        mock_regrant_result = MagicMock()
        mock_regrant_result.data = [{
            "data_sharing_enabled": True,
            "consented_at": "2024-03-01T00:00:00Z",
            "revoked_at": None,
        }]

        mock_client2 = MagicMock()
        mock_client2.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_existing
        mock_client2.table.return_value.update.return_value.eq.return_value.execute.return_value = mock_regrant_result

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client2):
            response = client.put(
                "/api/v1/consent/",
                json={"data_sharing_enabled": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data_sharing_enabled"] is True
        assert data["revoked_at"] is None
