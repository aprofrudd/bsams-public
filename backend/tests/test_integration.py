"""Integration tests for BSAMS API."""

from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_returns_healthy(self):
        """Health endpoint should return healthy status when DB reachable."""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value.data = []

        with patch("app.main.get_supabase_client", return_value=mock_client):
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestAPIVersioning:
    """Test API versioning."""

    def test_athletes_endpoint_at_v1(self):
        """Athletes should be available at /api/v1/athletes."""
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = (
                []
            )

            response = client.get("/api/v1/athletes/")

        assert response.status_code == 200

    def test_events_endpoint_at_v1(self):
        """Events should be available at /api/v1/events."""
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock_client = MagicMock()
            mock.return_value = mock_client

            # Mock athlete verification
            def table_side_effect(table_name):
                mock_table = MagicMock()
                if table_name == "athletes":
                    mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                        {"id": str(uuid4())}
                    ]
                else:
                    mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = (
                        []
                    )
                return mock_table

            mock_client.table.side_effect = table_side_effect

            athlete_id = uuid4()
            response = client.get(f"/api/v1/events/athlete/{athlete_id}")

        assert response.status_code == 200


class TestEndToEndWorkflow:
    """Test complete workflow from athlete creation to event creation."""

    @pytest.fixture
    def mock_supabase_workflow(self):
        """Setup mock for complete workflow."""
        with patch("app.core.supabase_client.get_supabase_client") as athletes_mock, patch(
            "app.core.supabase_client.get_supabase_client"
        ) as events_mock:
            client_mock = MagicMock()
            athletes_mock.return_value = client_mock
            events_mock.return_value = client_mock
            yield client_mock

    def test_create_athlete_then_event(self, mock_supabase_workflow):
        """Should be able to create an athlete and then add events."""
        athlete_id = str(uuid4())
        coach_id = "00000000-0000-0000-0000-000000000001"
        now = datetime.now().isoformat()

        # Mock athlete creation
        athlete_data = {
            "id": athlete_id,
            "coach_id": coach_id,
            "name": "Integration Test Athlete",
            "gender": "male",
            "date_of_birth": "1995-01-01",
            "created_at": now,
            "updated_at": now,
        }
        mock_supabase_workflow.table.return_value.insert.return_value.execute.return_value.data = [
            athlete_data
        ]

        # Create athlete
        response = client.post(
            "/api/v1/athletes/",
            json={"name": "Integration Test Athlete", "gender": "male"},
        )
        assert response.status_code == 201
        created_athlete = response.json()
        assert created_athlete["name"] == "Integration Test Athlete"

        # Setup for event creation
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            else:
                event_data = {
                    "id": str(uuid4()),
                    "athlete_id": athlete_id,
                    "event_date": "2024-01-15",
                    "metrics": {"test_type": "CMJ", "height_cm": 45.5},
                    "created_at": now,
                    "updated_at": now,
                }
                mock_table.insert.return_value.execute.return_value.data = [event_data]
            return mock_table

        mock_supabase_workflow.table.side_effect = table_side_effect

        # Create event for athlete
        response = client.post(
            "/api/v1/events/",
            json={
                "athlete_id": athlete_id,
                "event_date": "2024-01-15",
                "metrics": {"test_type": "CMJ", "height_cm": 45.5},
            },
        )
        assert response.status_code == 201
        created_event = response.json()
        assert created_event["metrics"]["test_type"] == "CMJ"


class TestOpenAPIDocumentation:
    """Test API documentation is available."""

    def test_openapi_schema_available(self):
        """OpenAPI schema should be available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "BSAMS API"
        assert schema["info"]["version"] == "1.0.0"

    def test_swagger_ui_available(self):
        """Swagger UI should be available at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self):
        """ReDoc should be available at /redoc."""
        response = client.get("/redoc")
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling across the API."""

    def test_invalid_uuid_returns_422(self):
        """Invalid UUID should return 422."""
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            mock.return_value = MagicMock()
            response = client.get("/api/v1/athletes/not-a-uuid")
        assert response.status_code == 422

    def test_database_unavailable_returns_503(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get("/api/v1/athletes/")
        assert response.status_code == 503
        assert "Database not configured" in response.json()["detail"]

    def test_missing_required_field_returns_422(self):
        """Missing required field should return 422."""
        response = client.post(
            "/api/v1/athletes/",
            json={"gender": "male"},  # Missing 'name'
        )
        assert response.status_code == 422


class TestFullFlowIntegration:
    """Test complete workflow: CSV Upload → Select Athlete → Switch Reference Group → Verify Data."""

    @pytest.fixture
    def mock_full_workflow(self):
        """Setup comprehensive mock for full workflow testing."""
        with patch("app.core.supabase_client.get_supabase_client") as mock:
            client_mock = MagicMock()
            mock.return_value = client_mock
            yield client_mock

    def test_csv_upload_to_zscore_calculation(self, mock_full_workflow):
        """Test full flow from CSV upload through Z-score calculation with reference group changes."""
        coach_id = "00000000-0000-0000-0000-000000000001"
        athlete_id = str(uuid4())
        now = datetime.now().isoformat()

        # === Step 1: Create an athlete ===
        athlete_data = {
            "id": athlete_id,
            "coach_id": coach_id,
            "name": "John Doe",
            "gender": "male",
            "date_of_birth": "1995-06-15",
            "created_at": now,
            "updated_at": now,
        }
        mock_full_workflow.table.return_value.insert.return_value.execute.return_value.data = [
            athlete_data
        ]

        response = client.post(
            "/api/v1/athletes/",
            json={"name": "John Doe", "gender": "male", "date_of_birth": "1995-06-15"},
        )
        assert response.status_code == 201
        created_athlete = response.json()
        assert created_athlete["name"] == "John Doe"

        # === Step 2: Upload CSV with performance data ===
        csv_content = """Test Date,Athlete,CMJ Height (cm),Body Mass (kg)
15/01/2024,John Doe,45.5,72.5
22/01/2024,John Doe,46.2,72.8
"""

        # Setup mock for CSV upload - athlete lookup and event insertion
        def upload_table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            else:  # performance_events
                mock_table.insert.return_value.execute.return_value.data = [{"id": str(uuid4())}]
            return mock_table

        mock_full_workflow.table.side_effect = upload_table_side_effect

        # Upload CSV file
        from io import BytesIO
        csv_file = BytesIO(csv_content.encode("utf-8"))
        response = client.post(
            "/api/v1/uploads/csv",
            files={"file": ("test.csv", csv_file, "text/csv")},
        )
        assert response.status_code == 201
        upload_result = response.json()
        assert upload_result["processed"] == 2
        assert upload_result["errors"] == []

        # === Step 3: Get benchmarks for whole cohort ===
        # Setup mock for benchmark query
        cohort_events = [
            {"metrics": {"test_type": "CMJ", "height_cm": 45.5, "body_mass_kg": 72.5}},
            {"metrics": {"test_type": "CMJ", "height_cm": 46.2, "body_mass_kg": 72.8}},
            {"metrics": {"test_type": "CMJ", "height_cm": 44.0, "body_mass_kg": 68.0}},
            {"metrics": {"test_type": "CMJ", "height_cm": 48.0, "body_mass_kg": 85.0}},
        ]

        def benchmark_table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id, "gender": "male"},
                    {"id": str(uuid4()), "gender": "male"},
                    {"id": str(uuid4()), "gender": "female"},
                ]
            else:  # performance_events
                mock_table.select.return_value.in_.return_value.execute.return_value.data = cohort_events
            return mock_table

        mock_full_workflow.table.side_effect = benchmark_table_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )
        assert response.status_code == 200
        cohort_benchmarks = response.json()
        assert cohort_benchmarks["count"] == 4
        assert cohort_benchmarks["reference_group"] == "cohort"
        assert cohort_benchmarks["mean"] is not None

        # === Step 4: Get benchmarks for gender-specific (male) ===
        male_events = [
            {"metrics": {"test_type": "CMJ", "height_cm": 45.5, "body_mass_kg": 72.5}},
            {"metrics": {"test_type": "CMJ", "height_cm": 46.2, "body_mass_kg": 72.8}},
            {"metrics": {"test_type": "CMJ", "height_cm": 48.0, "body_mass_kg": 85.0}},
        ]

        def gender_benchmark_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id, "gender": "male"},
                    {"id": str(uuid4()), "gender": "male"},
                ]
            else:
                mock_table.select.return_value.in_.return_value.execute.return_value.data = male_events
            return mock_table

        mock_full_workflow.table.side_effect = gender_benchmark_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "gender", "gender": "male"},
        )
        assert response.status_code == 200
        gender_benchmarks = response.json()
        assert gender_benchmarks["reference_group"] == "gender"
        # Gender-specific mean should differ from cohort mean
        assert gender_benchmarks["count"] == 3

        # === Step 5: Get Z-score for athlete with cohort reference ===
        def zscore_cohort_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                # First call: verify athlete, second call: get reference group athletes
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id, "gender": "male"}
                ]
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id},
                    {"id": str(uuid4())},
                    {"id": str(uuid4())},
                ]
            else:  # performance_events
                # First call: get athlete's event, second call: get all events for reference
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"metrics": {"height_cm": 45.5, "body_mass_kg": 72.5}}
                ]
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"metrics": {"height_cm": 45.5, "body_mass_kg": 72.5}}
                ]
                mock_table.select.return_value.in_.return_value.execute.return_value.data = cohort_events
            return mock_table

        mock_full_workflow.table.side_effect = zscore_cohort_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscore",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )
        assert response.status_code == 200
        cohort_zscore = response.json()
        assert cohort_zscore["reference_group"] == "cohort"
        assert "z_score" in cohort_zscore
        cohort_z = cohort_zscore["z_score"]

        # === Step 6: Switch to gender reference group and verify Z-score changes ===
        def zscore_gender_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id, "gender": "male"}
                ]
                # Gender filter query
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id},
                    {"id": str(uuid4())},
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"metrics": {"height_cm": 45.5, "body_mass_kg": 72.5}}
                ]
                mock_table.select.return_value.in_.return_value.execute.return_value.data = male_events
            return mock_table

        mock_full_workflow.table.side_effect = zscore_gender_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscore",
            params={"metric": "height_cm", "reference_group": "gender"},
        )
        assert response.status_code == 200
        gender_zscore = response.json()
        assert "gender:male" in gender_zscore["reference_group"]
        gender_z = gender_zscore["z_score"]

        # The Z-scores should be different because reference groups have different means/SDs
        # (In reality, with different populations, they would differ)
        assert cohort_zscore["mean"] != gender_zscore["mean"] or cohort_zscore["std_dev"] != gender_zscore["std_dev"]

        # === Step 7: Switch to mass band reference group ===
        mass_band_events = [
            {"metrics": {"height_cm": 45.5, "body_mass_kg": 72.5}},
            {"metrics": {"height_cm": 46.2, "body_mass_kg": 72.8}},
        ]

        def zscore_mass_band_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id, "gender": "male"}
                ]
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id},
                    {"id": str(uuid4())},
                ]
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"metrics": {"height_cm": 45.5, "body_mass_kg": 72.5}}
                ]
                # All events, but mass band filtering happens in code
                mock_table.select.return_value.in_.return_value.execute.return_value.data = cohort_events
            return mock_table

        mock_full_workflow.table.side_effect = zscore_mass_band_side_effect

        response = client.get(
            f"/api/v1/analysis/athlete/{athlete_id}/zscore",
            params={"metric": "height_cm", "reference_group": "mass_band"},
        )
        assert response.status_code == 200
        mass_band_zscore = response.json()
        assert "mass_band:" in mass_band_zscore["reference_group"]
        assert "70-74.9kg" in mass_band_zscore["reference_group"]  # 72.5kg falls in this band

    def test_reference_group_changes_affect_benchmarks(self, mock_full_workflow):
        """Verify that changing reference groups produces different benchmark statistics."""
        # Setup different data for different reference groups
        all_events = [
            {"metrics": {"height_cm": 40.0, "body_mass_kg": 65.0}},  # Female, light
            {"metrics": {"height_cm": 42.0, "body_mass_kg": 67.0}},  # Female, light
            {"metrics": {"height_cm": 50.0, "body_mass_kg": 80.0}},  # Male, heavy
            {"metrics": {"height_cm": 52.0, "body_mass_kg": 82.0}},  # Male, heavy
        ]

        # Cohort benchmarks (all 4 events)
        def cohort_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "gender": "male"},
                    {"id": str(uuid4()), "gender": "female"},
                ]
            else:
                mock_table.select.return_value.in_.return_value.execute.return_value.data = all_events
            return mock_table

        mock_full_workflow.table.side_effect = cohort_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "cohort"},
        )
        assert response.status_code == 200
        cohort_result = response.json()

        # Mass band benchmarks (only 80-84.9kg events)
        heavy_events = [
            {"metrics": {"height_cm": 50.0, "body_mass_kg": 80.0}},
            {"metrics": {"height_cm": 52.0, "body_mass_kg": 82.0}},
        ]

        def mass_band_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": str(uuid4()), "gender": "male"},
                ]
            else:
                mock_table.select.return_value.in_.return_value.execute.return_value.data = all_events
            return mock_table

        mock_full_workflow.table.side_effect = mass_band_side_effect

        response = client.get(
            "/api/v1/analysis/benchmarks",
            params={"metric": "height_cm", "reference_group": "mass_band", "mass_band": "80-84.9kg"},
        )
        assert response.status_code == 200
        mass_band_result = response.json()

        # Cohort mean should be different from mass band mean
        # Cohort: (40+42+50+52)/4 = 46
        # Mass band 80-84.9kg: (50+52)/2 = 51
        assert cohort_result["mean"] != mass_band_result["mean"]
