"""Tests for movement assessments router."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

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
def sample_athlete_id():
    """Sample athlete ID."""
    return str(uuid4())


@pytest.fixture
def sample_assessment_data(sample_athlete_id):
    """Sample movement assessment data for tests."""
    return {
        "id": str(uuid4()),
        "athlete_id": sample_athlete_id,
        "assessment_date": "2024-06-15",
        "assessment_type": "overhead_squat",
        "findings": {
            "knees": {
                "valgus": {"observed": True, "severity": "moderate", "side": "bilateral"}
            },
            "lphc": {
                "forward_lean": {"observed": True, "severity": "mild"}
            },
        },
        "notes": "Good effort, some compensations noted",
        "summary": "Overhead Squat: Bilateral knee valgus (moderate), forward lean (mild).",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _mock_athlete_ownership(mock_supabase, athlete_id, found=True):
    """Helper to set up athlete ownership verification mock."""
    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table
    mock_select = MagicMock()
    mock_table.select.return_value = mock_select
    mock_eq = MagicMock()
    mock_select.eq.return_value = mock_eq
    mock_eq2 = MagicMock()
    mock_eq.eq.return_value = mock_eq2
    mock_eq2.execute.return_value.data = [{"id": athlete_id}] if found else []
    return mock_table


class TestCreateAssessment:
    """Test POST /api/v1/assessments/"""

    def test_create_success(self, mock_supabase, sample_assessment_data, sample_athlete_id):
        """Should create and return new assessment."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        # Athlete ownership check
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        # Insert
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value.data = [sample_assessment_data]

        response = client.post(
            "/api/v1/assessments/",
            json={
                "athlete_id": sample_athlete_id,
                "assessment_date": "2024-06-15",
                "assessment_type": "overhead_squat",
                "findings": sample_assessment_data["findings"],
                "notes": "Good effort, some compensations noted",
                "summary": "Overhead Squat: Bilateral knee valgus (moderate), forward lean (mild).",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["assessment_type"] == "overhead_squat"
        assert data["findings"]["knees"]["valgus"]["observed"] is True

    def test_create_invalid_type(self, mock_supabase, sample_athlete_id):
        """Should return 400 for invalid assessment type."""
        response = client.post(
            "/api/v1/assessments/",
            json={
                "athlete_id": sample_athlete_id,
                "assessment_date": "2024-06-15",
                "assessment_type": "invalid_type",
                "findings": {},
            },
        )
        assert response.status_code == 400

    def test_create_athlete_not_found(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not found."""
        _mock_athlete_ownership(mock_supabase, sample_athlete_id, found=False)

        response = client.post(
            "/api/v1/assessments/",
            json={
                "athlete_id": sample_athlete_id,
                "assessment_date": "2024-06-15",
                "assessment_type": "overhead_squat",
                "findings": {},
            },
        )
        assert response.status_code == 404

    def test_create_duplicate(self, mock_supabase, sample_athlete_id):
        """Should return 409 for duplicate athlete+date+type."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table

        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq2 = MagicMock()
        mock_eq.eq.return_value = mock_eq2
        mock_eq2.execute.return_value.data = [{"id": sample_athlete_id}]

        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.side_effect = Exception("duplicate key value violates unique constraint")

        response = client.post(
            "/api/v1/assessments/",
            json={
                "athlete_id": sample_athlete_id,
                "assessment_date": "2024-06-15",
                "assessment_type": "overhead_squat",
                "findings": {},
            },
        )
        assert response.status_code == 409

    def test_create_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.post(
                "/api/v1/assessments/",
                json={
                    "athlete_id": str(uuid4()),
                    "assessment_date": "2024-06-15",
                    "assessment_type": "overhead_squat",
                    "findings": {},
                },
            )
        assert response.status_code == 503


class TestListAssessments:
    """Test GET /api/v1/assessments/athlete/{athlete_id}"""

    def test_list_success(self, mock_supabase, sample_athlete_id, sample_assessment_data):
        """Should return list of assessments."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": sample_athlete_id}
                ]
            elif table_name == "assessment_photos":
                mock_table.select.return_value.in_.return_value.execute.return_value.data = []
            else:
                mock_table.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = [
                    sample_assessment_data
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/assessments/athlete/{sample_athlete_id}")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["assessment_type"] == "overhead_squat"
        assert data[0]["photo_count"] == 0

    def test_list_athlete_not_found(self, mock_supabase, sample_athlete_id):
        """Should return 404 when athlete not found."""
        _mock_athlete_ownership(mock_supabase, sample_athlete_id, found=False)

        response = client.get(f"/api/v1/assessments/athlete/{sample_athlete_id}")
        assert response.status_code == 404

    def test_list_no_database(self):
        """Should return 503 when database not configured."""
        with patch("app.core.supabase_client.get_supabase_client", return_value=None):
            response = client.get(f"/api/v1/assessments/athlete/{uuid4()}")
        assert response.status_code == 503


class TestGetAssessment:
    """Test GET /api/v1/assessments/{assessment_id}"""

    def test_get_success(self, mock_supabase, sample_assessment_data, sample_athlete_id):
        """Should return single assessment with photos."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "movement_assessments":
                data_with_join = {
                    **sample_assessment_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
            elif table_name == "assessment_photos":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(f"/api/v1/assessments/{sample_assessment_data['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["assessment_type"] == "overhead_squat"
        assert data["photos"] == []

    def test_get_not_found(self, mock_supabase):
        """Should return 404 when assessment not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(f"/api/v1/assessments/{uuid4()}")
        assert response.status_code == 404


class TestUpdateAssessment:
    """Test PATCH /api/v1/assessments/{assessment_id}"""

    def test_update_success(self, mock_supabase, sample_assessment_data, sample_athlete_id):
        """Should update and return assessment."""
        from tests.conftest import TEST_USER_ID

        call_count = [0]

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "movement_assessments":
                data_with_join = {
                    **sample_assessment_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.update.return_value.eq.return_value.execute.return_value.data = [sample_assessment_data]
            elif table_name == "assessment_photos":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.patch(
            f"/api/v1/assessments/{sample_assessment_data['id']}",
            json={"notes": "Updated notes"},
        )

        assert response.status_code == 200

    def test_update_not_found(self, mock_supabase):
        """Should return 404 when assessment not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.patch(
            f"/api/v1/assessments/{uuid4()}",
            json={"notes": "Updated"},
        )
        assert response.status_code == 404

    def test_update_no_fields(self, mock_supabase, sample_assessment_data):
        """Should return 400 when no fields provided."""
        from tests.conftest import TEST_USER_ID

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        data_with_join = {
            **sample_assessment_data,
            "athletes": {"coach_id": str(TEST_USER_ID)},
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]

        response = client.patch(
            f"/api/v1/assessments/{sample_assessment_data['id']}",
            json={},
        )
        assert response.status_code == 400

    def test_update_invalid_type(self, mock_supabase, sample_assessment_data):
        """Should return 400 for invalid assessment type update."""
        from tests.conftest import TEST_USER_ID

        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        data_with_join = {
            **sample_assessment_data,
            "athletes": {"coach_id": str(TEST_USER_ID)},
        }
        mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]

        response = client.patch(
            f"/api/v1/assessments/{sample_assessment_data['id']}",
            json={"assessment_type": "invalid_type"},
        )
        assert response.status_code == 400


class TestDeleteAssessment:
    """Test DELETE /api/v1/assessments/{assessment_id}"""

    def test_delete_success(self, mock_supabase, sample_assessment_data, sample_athlete_id):
        """Should delete assessment and return 204."""
        from tests.conftest import TEST_USER_ID

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "movement_assessments":
                data_with_join = {
                    **sample_assessment_data,
                    "athletes": {"coach_id": str(TEST_USER_ID)},
                }
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [data_with_join]
                mock_table.delete.return_value.eq.return_value.execute.return_value = None
            elif table_name == "assessment_photos":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.delete(f"/api/v1/assessments/{sample_assessment_data['id']}")
        assert response.status_code == 204

    def test_delete_not_found(self, mock_supabase):
        """Should return 404 when assessment not found."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.delete(f"/api/v1/assessments/{uuid4()}")
        assert response.status_code == 404


class TestAssessmentSchemaValidation:
    """Test schema validation."""

    def test_valid_assessment_create(self):
        """All valid assessment types should be accepted."""
        from app.schemas.assessment import MovementAssessmentCreate

        for atype in ["overhead_squat", "single_leg_squat_left", "single_leg_squat_right"]:
            entry = MovementAssessmentCreate(
                athlete_id=uuid4(),
                assessment_date="2024-06-15",
                assessment_type=atype,
                findings={"knees": {"valgus": {"observed": True, "severity": "moderate"}}},
            )
            assert entry.assessment_type == atype

    def test_findings_default_empty(self):
        """Findings should default to empty dict."""
        from app.schemas.assessment import MovementAssessmentCreate

        entry = MovementAssessmentCreate(
            athlete_id=uuid4(),
            assessment_date="2024-06-15",
            assessment_type="overhead_squat",
        )
        assert entry.findings == {}

    def test_response_model(self):
        """Response model should accept all fields."""
        from app.schemas.assessment import MovementAssessmentResponse

        resp = MovementAssessmentResponse(
            id=uuid4(),
            athlete_id=uuid4(),
            assessment_date="2024-06-15",
            assessment_type="overhead_squat",
            findings={"knees": {"valgus": {"observed": True}}},
            notes="Test",
            summary="Test summary",
            photos=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert resp.assessment_type == "overhead_squat"
        assert resp.photos == []
