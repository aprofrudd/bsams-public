"""Tests for conditioning template features.

Tests cover:
- Session template category filter (gold-standard listing)
- Template description/category/tier fields
- Preview-targets endpoint
- Intensity range on exercise prescriptions
- Description on training sessions
- Intensity ranges on block apply
- Apply template conditioning fields propagation
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

COACH_ID = str(uuid4())
ADMIN_ID = str(uuid4())
ATHLETE_ID = str(uuid4())
TEMPLATE_ID = str(uuid4())


@pytest.fixture
def mock_supabase():
    """Fixture to mock Supabase client."""
    with patch("app.core.supabase_client.get_supabase_client") as mock:
        mock_client = MagicMock()
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def gold_standard_template():
    """Sample gold-standard conditioning template."""
    return {
        "id": TEMPLATE_ID,
        "coach_id": ADMIN_ID,
        "template_name": "Foundation Assault Bike",
        "training_type": "Conditioning",
        "description": "Low-intensity assault bike intervals",
        "notes": "Target: 40-60% of peak power",
        "template_category": "conditioning",
        "tier": "foundation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


@pytest.fixture
def conditioning_exercise():
    """Sample conditioning template exercise."""
    return {
        "id": str(uuid4()),
        "template_id": TEMPLATE_ID,
        "exercise_library_id": None,
        "exercise_name": "Assault Bike Intervals",
        "exercise_category": "Conditioning",
        "order_index": 1,
        "sets": 6,
        "reps": 1,
        "weight_kg": None,
        "tempo": None,
        "rest_seconds": 90,
        "duration_seconds": 30,
        "distance_meters": None,
        "intensity_type": "power_watts",
        "intensity_value": None,
        "rest_between_reps_seconds": None,
        "rest_between_reps": None,
        "rep_intensity_values": None,
        "notes": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


class TestCategoryFilter:
    """Test GET /api/v1/session-templates/?category=conditioning"""

    def test_list_gold_standard_templates(self, mock_supabase, gold_standard_template):
        """Should return conditioning templates from any coach when category=conditioning."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    gold_standard_template
                ]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get("/api/v1/session-templates/?category=conditioning")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["template_category"] == "conditioning"
        assert data[0]["tier"] == "foundation"
        assert data[0]["description"] == "Low-intensity assault bike intervals"

    def test_list_without_category_returns_own(self, mock_supabase):
        """Without category, returns only coach-owned templates."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []

        response = client.get("/api/v1/session-templates/")

        assert response.status_code == 200


class TestTemplateWithNewFields:
    """Test template CRUD with description, template_category, tier."""

    def test_create_template_with_category_and_tier(self, mock_supabase, gold_standard_template):
        """Should create template with all new fields."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.insert.return_value.execute.return_value.data = [gold_standard_template]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/session-templates/",
            json={
                "template_name": "Foundation Assault Bike",
                "training_type": "Conditioning",
                "description": "Low-intensity assault bike intervals",
                "template_category": "conditioning",
                "tier": "foundation",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Low-intensity assault bike intervals"
        assert data["template_category"] == "conditioning"
        assert data["tier"] == "foundation"

    def test_invalid_tier_rejected(self):
        """Should reject invalid tier value."""
        response = client.post(
            "/api/v1/session-templates/",
            json={
                "template_name": "Bad Tier",
                "training_type": "Conditioning",
                "tier": "elite",
            },
        )
        assert response.status_code == 422


class TestPreviewTargets:
    """Test GET /api/v1/session-templates/{id}/preview-targets"""

    def test_preview_with_metabolic_data(self, mock_supabase, gold_standard_template, conditioning_exercise):
        """Should resolve intensity targets from metabolic profile."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [gold_standard_template]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [conditioning_exercise]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": ATHLETE_ID}
                ]
            elif table_name == "metabolic_profiles":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"sprint_1_avg_power_w": 500.0}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/session-templates/{TEMPLATE_ID}/preview-targets?athlete_id={ATHLETE_ID}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tier"] == "foundation"
        assert len(data["exercises"]) == 1
        ex = data["exercises"][0]
        assert ex["exercise_name"] == "Assault Bike Intervals"
        assert ex["source"] == "metabolic_profile"
        # foundation: 0.4-0.6 * 500 = 200-300
        assert ex["intensity_min"] == 200.0
        assert ex["intensity_max"] == 300.0

    def test_preview_missing_data(self, mock_supabase, gold_standard_template, conditioning_exercise):
        """Should return 'missing' source when no athlete data."""
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [gold_standard_template]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [conditioning_exercise]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": ATHLETE_ID}
                ]
            elif table_name in ("metabolic_profiles", "air_bike_recordings", "air_bike_tests"):
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/session-templates/{TEMPLATE_ID}/preview-targets?athlete_id={ATHLETE_ID}"
        )

        assert response.status_code == 200
        data = response.json()
        ex = data["exercises"][0]
        assert ex["source"] == "missing"
        assert ex["intensity_min"] is None
        assert ex["intensity_max"] is None

    def test_preview_template_not_found(self, mock_supabase):
        """Should return 404 for nonexistent template."""
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.execute.return_value.data = []

        response = client.get(
            f"/api/v1/session-templates/{uuid4()}/preview-targets?athlete_id={ATHLETE_ID}"
        )

        assert response.status_code == 404

    def test_preview_without_tier(self, mock_supabase, conditioning_exercise):
        """Template without tier returns no_tier source."""
        template_no_tier = {
            "id": TEMPLATE_ID,
            "coach_id": COACH_ID,
            "template_name": "No Tier Template",
            "training_type": "Conditioning",
            "description": None,
            "notes": None,
            "template_category": "conditioning",
            "tier": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [template_no_tier]
                # Also handle ownership check
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [template_no_tier]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [conditioning_exercise]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": ATHLETE_ID}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.get(
            f"/api/v1/session-templates/{TEMPLATE_ID}/preview-targets?athlete_id={ATHLETE_ID}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exercises"][0]["source"] == "no_tier"


class TestIntensityRangeOnPrescription:
    """Test intensity_min/intensity_max on exercise prescriptions."""

    def test_create_prescription_with_intensity_range(self, mock_supabase):
        """Should accept intensity_min and intensity_max."""
        session_id = str(uuid4())
        athlete_id = ATHLETE_ID
        prescription_data = {
            "id": str(uuid4()),
            "session_id": session_id,
            "exercise_name": "Assault Bike",
            "exercise_category": "Conditioning",
            "set_number": 1,
            "reps": 1,
            "duration_seconds": 30,
            "rest_seconds": 90,
            "intensity_type": "power_watts",
            "intensity_min": 200.0,
            "intensity_max": 300.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "exercise_prescriptions":
                mock_table.insert.return_value.execute.return_value.data = [prescription_data]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": session_id, "athlete_id": athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/training/sessions/{session_id}/exercises/",
            json={
                "exercise_name": "Assault Bike",
                "exercise_category": "Conditioning",
                "set_number": 1,
                "reps": 1,
                "duration_seconds": 30,
                "rest_seconds": 90,
                "intensity_type": "power_watts",
                "intensity_min": 200.0,
                "intensity_max": 300.0,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["intensity_min"] == 200.0
        assert data["intensity_max"] == 300.0


class TestSessionDescription:
    """Test description field on training sessions."""

    def test_create_session_with_description(self, mock_supabase):
        """Should accept description field on session creation."""
        session_data = {
            "id": str(uuid4()),
            "athlete_id": str(uuid4()),
            "session_date": "2026-03-13",
            "training_type": "Conditioning",
            "description": "Foundation assault bike session",
            "notes": None,
            "duration_minutes": None,
            "rpe": None,
            "srpe": None,
            "metrics": {},
            "status": None,
            "created_by": COACH_ID,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": session_data["athlete_id"]}
                ]
            elif table_name == "training_sessions":
                mock_table.insert.return_value.execute.return_value.data = [session_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            "/api/v1/training/sessions/",
            json={
                "athlete_id": session_data["athlete_id"],
                "session_date": "2026-03-13",
                "training_type": "Conditioning",
                "description": "Foundation assault bike session",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Foundation assault bike session"


class TestApplyTemplateConditioningFields:
    """Test that apply_template propagates conditioning fields correctly."""

    def test_apply_includes_rep_durations_and_rest(self, mock_supabase):
        """Apply template should include rep_durations, rest_between_reps, notes."""
        from tests.conftest import TEST_USER_ID

        template_data = {
            "id": TEMPLATE_ID,
            "coach_id": str(TEST_USER_ID),
            "template_name": "Test",
            "training_type": "Conditioning",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        exercise_with_conditioning = {
            "id": str(uuid4()),
            "template_id": TEMPLATE_ID,
            "exercise_name": "Bike Intervals",
            "exercise_category": "Conditioning",
            "order_index": 1,
            "sets": 2,
            "reps": 3,
            "duration_seconds": 30,
            "rest_seconds": 60,
            "intensity_type": "power_watts",
            "intensity_value": 350,
            "rest_between_reps_seconds": 10,
            "rep_durations": [10, 20, 30],
            "rest_between_reps": [5, 10],
            "rep_intensity_values": [300, 350, 400],
            "notes": "Max effort",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        session_id = str(uuid4())
        athlete_id = str(uuid4())

        inserted_prescriptions = []

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [template_data]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    exercise_with_conditioning
                ]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": session_id, "athlete_id": athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            elif table_name == "exercise_prescriptions":
                def capture_insert(rows):
                    inserted_prescriptions.extend(rows)
                    mock_resp = MagicMock()
                    mock_resp.data = rows
                    return mock_resp
                mock_insert = MagicMock()
                mock_insert.execute = lambda: capture_insert(
                    mock_table._last_insert_data
                ) if hasattr(mock_table, '_last_insert_data') else MagicMock(data=[])
                def insert_with_capture(data):
                    mock_table._last_insert_data = data
                    inserted_prescriptions.clear()
                    inserted_prescriptions.extend(data)
                    result = MagicMock()
                    result.data = data
                    return result
                mock_table.insert.return_value.execute.side_effect = lambda: MagicMock(data=inserted_prescriptions)
                mock_table.insert.side_effect = lambda data: (
                    inserted_prescriptions.clear() or inserted_prescriptions.extend(data) or MagicMock(execute=lambda: MagicMock(data=data))
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/session-templates/{TEMPLATE_ID}/apply?session_id={session_id}"
        )

        assert response.status_code == 201
        # Verify that conditioning fields were included in the prescriptions
        assert len(inserted_prescriptions) == 2  # 2 sets
        p = inserted_prescriptions[0]
        assert p.get("rep_durations") == [10, 20, 30]
        assert p.get("rest_between_reps") == [5, 10]
        assert p.get("rep_intensity_values") == [300, 350, 400]
        assert p.get("notes") == "Max effort"
        assert p.get("intensity_type") == "power_watts"


class TestApplyGoldStandardTemplate:
    """Test that coaches can apply admin-owned conditioning templates."""

    def test_coach_apply_admin_conditioning_template(self, mock_supabase, gold_standard_template, conditioning_exercise):
        """Coach applying admin-owned gold-standard conditioning template succeeds."""
        session_id = str(uuid4())
        athlete_id = str(uuid4())

        inserted_prescriptions = []

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                # Load by ID (no coach_id filter)
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [gold_standard_template]
            elif table_name == "template_exercises":
                mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value.data = [
                    conditioning_exercise
                ]
            elif table_name == "training_sessions":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                    {"id": session_id, "athlete_id": athlete_id}
                ]
            elif table_name == "athletes":
                mock_table.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
                    {"id": athlete_id}
                ]
            elif table_name == "metabolic_profiles":
                mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"sprint_1_avg_power_w": 500.0}
                ]
            elif table_name == "exercise_prescriptions":
                mock_table.insert.side_effect = lambda data: (
                    inserted_prescriptions.clear() or inserted_prescriptions.extend(data) or MagicMock(execute=lambda: MagicMock(data=data))
                )
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/session-templates/{TEMPLATE_ID}/apply?session_id={session_id}"
        )

        assert response.status_code == 201
        # Should have created prescriptions (6 sets from conditioning_exercise)
        assert len(inserted_prescriptions) == 6
        # Should have resolved intensity targets (foundation: 0.4-0.6 * 500)
        p = inserted_prescriptions[0]
        assert p.get("intensity_min") == 200.0
        assert p.get("intensity_max") == 300.0

    def test_coach_apply_other_coach_template_404(self, mock_supabase):
        """Coach applying another coach's non-conditioning template returns 404."""
        other_coach_id = str(uuid4())
        template_data = {
            "id": TEMPLATE_ID,
            "coach_id": other_coach_id,
            "template_name": "Other Coach Template",
            "training_type": "Strength",
            "description": None,
            "notes": None,
            "template_category": None,
            "tier": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        session_id = str(uuid4())

        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "session_templates":
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [template_data]
            return mock_table

        mock_supabase.table.side_effect = table_side_effect

        response = client.post(
            f"/api/v1/session-templates/{TEMPLATE_ID}/apply?session_id={session_id}"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Template not found"
