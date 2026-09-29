"""Tests for custom training types router."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app
from tests.conftest import (
    TEST_ATHLETE_ID,
    TEST_USER_ID,
    override_get_current_athlete,
    override_get_current_user,
)

client = TestClient(app)


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def sample_custom_type():
    """Sample custom training type data."""
    return {
        "id": str(uuid4()),
        "coach_id": str(TEST_USER_ID),
        "type_name": "Boxing",
        "display_order": 0,
        "created_at": datetime.now().isoformat(),
    }


class TestListTrainingTypes:
    """Test GET /api/v1/training/types/"""

    def test_list_types_returns_system_defaults_and_custom(self, mock_supabase, sample_custom_type):
        """Should return system defaults plus coach's custom types."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
            sample_custom_type
        ]

        response = client.get("/api/v1/training/types/")

        assert response.status_code == 200
        data = response.json()
        # 4 system defaults + 1 custom
        assert len(data) == 5

        # First 4 are system defaults
        assert data[0]["type_name"] == "Strength"
        assert data[0]["is_system"] is True
        assert data[0]["id"] is None
        assert data[1]["type_name"] == "Mobility"
        assert data[1]["is_system"] is True
        assert data[2]["type_name"] == "Conditioning"
        assert data[2]["is_system"] is True
        assert data[3]["type_name"] == "Circuit"
        assert data[3]["is_system"] is True

        # Last one is custom
        assert data[4]["type_name"] == "Boxing"
        assert data[4]["is_system"] is False
        assert data[4]["id"] == sample_custom_type["id"]

    def test_list_types_no_custom(self, mock_supabase):
        """Should return only system defaults when no custom types exist."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        response = client.get("/api/v1/training/types/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert all(item["is_system"] for item in data)

    def test_list_types_athlete_resolves_coach_id(self, mock_supabase, sample_custom_type):
        """Athlete should see their coach's training types."""
        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = override_get_current_athlete

        try:
            call_count = [0]

            def table_side_effect(table_name):
                mock_table = MagicMock()
                call_count[0] += 1
                if call_count[0] == 1:
                    # First call: athletes table lookup for coach_id
                    mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                        {"coach_id": str(TEST_USER_ID)}
                    ]
                else:
                    # Second call: custom_training_types
                    mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                        sample_custom_type
                    ]
                return mock_table

            mock_supabase.table.side_effect = table_side_effect

            response = client.get("/api/v1/training/types/")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 5
            assert data[4]["type_name"] == "Boxing"
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides[get_current_user] = override_get_current_user

    def test_list_types_athlete_not_found(self, mock_supabase):
        """Athlete with no athlete record should get 404."""
        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = override_get_current_athlete

        try:
            mock_table = MagicMock()
            mock_supabase.table.return_value = mock_table
            mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

            response = client.get("/api/v1/training/types/")

            assert response.status_code == 404
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides[get_current_user] = override_get_current_user

    def test_list_types_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get("/api/v1/training/types/")
        assert response.status_code == 503


class TestCreateTrainingType:
    """Test POST /api/v1/training/types/"""

    def test_create_custom_type_success(self, mock_supabase, sample_custom_type):
        """Should create and return a new custom training type."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value.data = [sample_custom_type]

        response = client.post(
            "/api/v1/training/types/",
            json={"type_name": "Boxing"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["type_name"] == "Boxing"
        assert data["coach_id"] == str(TEST_USER_ID)

    def test_create_duplicate_system_default_rejected(self, mock_supabase):
        """Should reject creating a type that matches a system default (case-insensitive)."""
        response = client.post(
            "/api/v1/training/types/",
            json={"type_name": "Strength"},
        )
        assert response.status_code == 409
        assert "system default" in response.json()["detail"]

    def test_create_duplicate_system_default_case_insensitive(self, mock_supabase):
        """Should reject case-insensitive matches to system defaults."""
        response = client.post(
            "/api/v1/training/types/",
            json={"type_name": "conditioning"},
        )
        assert response.status_code == 409

    def test_create_duplicate_custom_type_rejected(self, mock_supabase):
        """Should return 409 when custom type name already exists for this coach."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.insert.return_value.execute.side_effect = Exception(
            "duplicate key value violates unique constraint"
        )

        response = client.post(
            "/api/v1/training/types/",
            json={"type_name": "Boxing"},
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_type_athlete_forbidden(self, mock_supabase):
        """Athletes should not be able to create training types."""
        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = override_get_current_athlete

        try:
            response = client.post(
                "/api/v1/training/types/",
                json={"type_name": "Boxing"},
            )
            assert response.status_code == 403
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides[get_current_user] = override_get_current_user

    def test_create_type_empty_name_rejected(self):
        """Should return 422 for empty type name."""
        response = client.post(
            "/api/v1/training/types/",
            json={"type_name": "  "},
        )
        assert response.status_code == 422

    def test_create_type_name_too_long(self):
        """Should return 422 for type name exceeding 50 characters."""
        response = client.post(
            "/api/v1/training/types/",
            json={"type_name": "A" * 51},
        )
        assert response.status_code == 422

    def test_create_type_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                "/api/v1/training/types/",
                json={"type_name": "Boxing"},
            )
        assert response.status_code == 503


class TestDeleteTrainingType:
    """Test DELETE /api/v1/training/types/{type_id}"""

    def test_delete_custom_type_success(self, mock_supabase, sample_custom_type):
        """Should delete custom type and return 204."""
        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: verify ownership
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    sample_custom_type
                ]
            else:
                # Second call: delete
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/training/types/{sample_custom_type['id']}")

        assert response.status_code == 204

    def test_delete_nonexistent_type_404(self, mock_supabase):
        """Should return 404 when type not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/training/types/{uuid4()}")

        assert response.status_code == 404

    def test_delete_type_athlete_forbidden(self, mock_supabase):
        """Athletes should not be able to delete training types."""
        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = override_get_current_athlete

        try:
            response = client.delete(f"/api/v1/training/types/{uuid4()}")
            assert response.status_code == 403
        finally:
            if original:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides[get_current_user] = override_get_current_user

    def test_delete_type_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.delete(f"/api/v1/training/types/{uuid4()}")
        assert response.status_code == 503


class TestCustomTrainingTypeValidation:
    """Test schema validation for custom training types."""

    def test_type_name_stripped(self):
        """Type name should be stripped of whitespace."""
        from app.schemas.custom_training_type import CustomTrainingTypeCreate

        t = CustomTrainingTypeCreate(type_name="  Boxing  ")
        assert t.type_name == "Boxing"

    def test_type_name_required(self):
        """Should require type name."""
        from app.schemas.custom_training_type import CustomTrainingTypeCreate

        with pytest.raises(Exception):
            CustomTrainingTypeCreate(type_name="")
