"""Tests for health check endpoint."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthCheck:
    """Test GET /health endpoint."""

    def test_healthy_when_db_reachable(self):
        """Should return healthy when database responds."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = [
            {"id": "some-id"}
        ]

        with patch("app.main.get_supabase_client", return_value=mock_client):
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_unhealthy_when_db_unreachable(self):
        """Should return 503 when database query fails."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.side_effect = Exception(
            "Connection refused"
        )

        with patch("app.main.get_supabase_client", return_value=mock_client):
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["reason"] == "Database unreachable"

    def test_unhealthy_when_db_not_configured(self):
        """Should return 503 when Supabase client is None."""
        with patch("app.main.get_supabase_client", return_value=None):
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["reason"] == "Database not configured"
