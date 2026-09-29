"""Tests for user consent tracking router (GDPR compliance)."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_consent():
    """Sample consent record data."""
    from tests.conftest import TEST_USER_ID

    return {
        "id": str(uuid4()),
        "user_id": str(TEST_USER_ID),
        "consent_type": "data_processing",
        "granted": True,
        "granted_at": datetime.now().isoformat(),
        "revoked_at": None,
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
    }


class TestGetConsents:
    """Test GET /api/v1/user-consents/"""

    def test_get_consents_empty(self, mock_supabase):
        """Should return empty list when no consents exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get("/api/v1/user-consents/")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_consents_returns_existing(self, mock_supabase, sample_consent):
        """Should return existing consent records for current user."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [
            sample_consent
        ]

        response = client.get("/api/v1/user-consents/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["consent_type"] == "data_processing"
        assert data[0]["granted"] is True


class TestUpdateConsent:
    """Test PUT /api/v1/user-consents/{consent_type}"""

    def test_grant_data_processing_consent(self, mock_supabase, sample_consent):
        """Should create new consent record when granting data_processing."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # No existing record
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        # Insert returns new record
        mock_table.insert.return_value.execute.return_value.data = [sample_consent]

        response = client.put(
            "/api/v1/user-consents/data_processing",
            json={"granted": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["consent_type"] == "data_processing"
        assert data["granted"] is True

    def test_revoke_consent(self, mock_supabase, sample_consent):
        """Should update existing consent to revoked."""
        revoked = {
            **sample_consent,
            "granted": False,
            "revoked_at": datetime.now().isoformat(),
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Existing record found
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_consent["id"]}
        ]

        # Update returns updated record
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            revoked
        ]

        response = client.put(
            "/api/v1/user-consents/data_processing",
            json={"granted": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["granted"] is False
        assert data["revoked_at"] is not None

    def test_invalid_consent_type_returns_400(self, mock_supabase):
        """Should return 400 for invalid consent type."""
        response = client.put(
            "/api/v1/user-consents/invalid_type",
            json={"granted": True},
        )

        assert response.status_code == 400
        assert "Invalid consent type" in response.json()["detail"]

    def test_update_existing_consent_grant_then_revoke(
        self, mock_supabase, sample_consent
    ):
        """Should update existing consent from granted to revoked."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Existing record
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": sample_consent["id"]}
        ]

        # First grant
        granted = {**sample_consent, "granted": True}
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            granted
        ]

        response = client.put(
            "/api/v1/user-consents/data_processing",
            json={"granted": True},
        )
        assert response.status_code == 200
        assert response.json()["granted"] is True

        # Then revoke
        revoked = {
            **sample_consent,
            "granted": False,
            "revoked_at": datetime.now().isoformat(),
        }
        mock_table.update.return_value.eq.return_value.execute.return_value.data = [
            revoked
        ]

        response = client.put(
            "/api/v1/user-consents/data_processing",
            json={"granted": False},
        )
        assert response.status_code == 200
        assert response.json()["granted"] is False

    def test_grant_marketing_consent(self, mock_supabase):
        """Should accept marketing as a valid consent type."""
        from tests.conftest import TEST_USER_ID

        consent_data = {
            "id": str(uuid4()),
            "user_id": str(TEST_USER_ID),
            "consent_type": "marketing",
            "granted": True,
            "granted_at": datetime.now().isoformat(),
            "revoked_at": None,
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
        }

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        mock_table.insert.return_value.execute.return_value.data = [consent_data]

        response = client.put(
            "/api/v1/user-consents/marketing",
            json={"granted": True},
        )

        assert response.status_code == 200
        assert response.json()["consent_type"] == "marketing"
