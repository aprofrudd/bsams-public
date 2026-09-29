"""Tests for admin router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_ADMIN_ID, TEST_USER_ID


class TestListSharedAthletes:
    """Test GET /admin/shared-athletes endpoint."""

    def test_non_admin_gets_403(self):
        """Non-admin users should get 403."""
        client = TestClient(app)
        with patch("app.core.supabase_client.get_supabase_client") as mock_get_client:
            response = client.get("/api/v1/admin/shared-athletes")

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"

    def test_admin_gets_anonymised_athletes(self, admin_client):
        """Admin should see anonymised athletes from opted-in coaches."""
        mock_consents = MagicMock()
        mock_consents.data = [{"coach_id": "coach-1", "data_sharing_enabled": True}]

        mock_admin_profiles = MagicMock()
        mock_admin_profiles.data = [{"id": "admin-1"}]

        mock_athletes = MagicMock()
        mock_athletes.data = [
            {"id": "athlete-1", "gender": "male", "coach_id": "coach-1"},
            {"id": "athlete-2", "gender": "female", "coach_id": "coach-1"},
        ]

        mock_client = MagicMock()

        def table_dispatch(name):
            m = MagicMock()
            if name == "coach_consents":
                m.select.return_value.execute.return_value = mock_consents
            elif name == "profiles":
                m.select.return_value.eq.return_value.execute.return_value = mock_admin_profiles
            elif name == "athletes":
                # N+1 fix: now uses .in_() instead of .eq() per coach
                m.select.return_value.in_.return_value.execute.return_value = mock_athletes
            return m

        mock_client.table.side_effect = table_dispatch

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = admin_client.get("/api/v1/admin/shared-athletes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["anonymous_name"] == "Athlete 001"
        assert data[1]["anonymous_name"] == "Athlete 002"
        # Names should never appear
        for athlete in data:
            assert "name" not in athlete

    def test_admin_gets_empty_when_no_opted_in(self, admin_client):
        """Admin should get empty list when no coaches opted in."""
        mock_consents = MagicMock()
        mock_consents.data = []

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.execute.return_value = mock_consents

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = admin_client.get("/api/v1/admin/shared-athletes")

        assert response.status_code == 200
        assert response.json() == []


class TestGetSharedAthleteEvents:
    """Test GET /admin/shared-athletes/{id}/events endpoint."""

    def test_non_admin_gets_403(self):
        """Non-admin users should get 403."""
        client = TestClient(app)
        response = client.get("/api/v1/admin/shared-athletes/00000000-0000-0000-0000-000000000001/events")
        assert response.status_code == 403

    def test_admin_gets_events_for_opted_in_athlete(self, admin_client):
        """Admin should see events for athletes of opted-in coaches."""
        mock_athlete = MagicMock()
        mock_athlete.data = [{"coach_id": "coach-1"}]

        mock_consent = MagicMock()
        mock_consent.data = [{"data_sharing_enabled": True}]

        mock_events = MagicMock()
        mock_events.data = [
            {
                "id": "event-1",
                "athlete_id": "athlete-1",
                "event_date": "2024-01-01",
                "metrics": {"height_cm": 45.5},
            }
        ]

        mock_client = MagicMock()

        def table_dispatch(name):
            m = MagicMock()
            if name == "athletes":
                m.select.return_value.eq.return_value.execute.return_value = mock_athlete
            elif name == "coach_consents":
                m.select.return_value.eq.return_value.execute.return_value = mock_consent
            elif name == "performance_events":
                m.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_events
            return m

        mock_client.table.side_effect = table_dispatch

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = admin_client.get(
                "/api/v1/admin/shared-athletes/00000000-0000-0000-0000-000000000001/events"
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["metrics"]["height_cm"] == 45.5

    def test_admin_gets_403_for_non_opted_in_coach(self, admin_client):
        """Admin should get 403 for athletes whose coach hasn't opted in."""
        mock_athlete = MagicMock()
        mock_athlete.data = [{"coach_id": "coach-1"}]

        mock_consent = MagicMock()
        mock_consent.data = []

        mock_client = MagicMock()

        def table_dispatch(name):
            m = MagicMock()
            if name == "athletes":
                m.select.return_value.eq.return_value.execute.return_value = mock_athlete
            elif name == "coach_consents":
                m.select.return_value.eq.return_value.execute.return_value = mock_consent
            return m

        mock_client.table.side_effect = table_dispatch

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = admin_client.get(
                "/api/v1/admin/shared-athletes/00000000-0000-0000-0000-000000000001/events"
            )

        assert response.status_code == 403

    def test_admin_gets_403_when_consent_is_false(self, admin_client):
        """Admin should get 403 when consent exists but data_sharing_enabled is False."""
        mock_athlete = MagicMock()
        mock_athlete.data = [{"coach_id": "coach-1"}]

        mock_consent = MagicMock()
        mock_consent.data = [{"data_sharing_enabled": False}]

        mock_client = MagicMock()

        def table_dispatch(name):
            m = MagicMock()
            if name == "athletes":
                m.select.return_value.eq.return_value.execute.return_value = mock_athlete
            elif name == "coach_consents":
                m.select.return_value.eq.return_value.execute.return_value = mock_consent
            return m

        mock_client.table.side_effect = table_dispatch

        with patch("app.core.supabase_client.get_supabase_client", return_value=mock_client):
            response = admin_client.get(
                "/api/v1/admin/shared-athletes/00000000-0000-0000-0000-000000000001/events"
            )

        assert response.status_code == 403
