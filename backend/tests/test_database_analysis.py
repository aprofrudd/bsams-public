"""Tests for database-wide analysis (admin-only)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_ADMIN_ID, TEST_USER_ID


@pytest.fixture
def admin_client():
    """Provide test client authenticated as admin."""
    from app.core.security import AuthenticatedUser, get_current_user

    async def override():
        return AuthenticatedUser(id=TEST_ADMIN_ID, role="admin")

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override
    client = TestClient(app)
    yield client
    if original:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def coach_client():
    """Provide test client authenticated as coach (non-admin)."""
    from app.core.security import AuthenticatedUser, get_current_user

    async def override():
        return AuthenticatedUser(id=TEST_USER_ID, role="coach")

    original = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = override
    client = TestClient(app)
    yield client
    if original:
        app.dependency_overrides[get_current_user] = original
    else:
        app.dependency_overrides.pop(get_current_user, None)


# ── Auth tests ────────────────────────────────────────────────────────


class TestAuthGuards:
    """Verify admin-only access control."""

    def test_analyze_requires_admin(self, coach_client):
        """Coach should get 403 on analyze endpoint."""
        resp = coach_client.post("/api/v1/database-analysis/analyze", json={
            "domain": "performance",
        })
        assert resp.status_code == 403

    def test_domains_requires_admin(self, coach_client):
        """Coach should get 403 on domains endpoint."""
        resp = coach_client.get("/api/v1/database-analysis/domains")
        assert resp.status_code == 403

    def test_domain_metrics_requires_admin(self, coach_client):
        """Coach should get 403 on domain metrics endpoint."""
        resp = coach_client.get("/api/v1/database-analysis/domain/performance/metrics")
        assert resp.status_code == 403


class TestDomainsEndpoint:
    """Test GET /database-analysis/domains."""

    def test_returns_all_domains(self, admin_client):
        """Admin should get list of all 7 domains."""
        resp = admin_client.get("/api/v1/database-analysis/domains")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 7
        keys = [d["key"] for d in data]
        assert "performance" in keys
        assert "training" in keys
        assert "wellness" in keys
        assert "vbt" in keys
        assert "lactate" in keys
        assert "air_bike" in keys
        assert "assessments" in keys


class TestDomainMetricsEndpoint:
    """Test GET /database-analysis/domain/{domain}/metrics."""

    def test_performance_metrics(self, admin_client):
        """Should return metric registry entries for performance domain."""
        resp = admin_client.get("/api/v1/database-analysis/domain/performance/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain"] == "performance"
        keys = [m["key"] for m in data["metrics"]]
        assert "height_cm" in keys
        assert "rsi" in keys
        # Non-metric keys should be excluded
        assert "test_type" not in keys
        assert "body_mass_kg" not in keys

    def test_training_metrics(self, admin_client):
        """Should return training-specific metrics."""
        resp = admin_client.get("/api/v1/database-analysis/domain/training/metrics")
        assert resp.status_code == 200
        data = resp.json()
        keys = [m["key"] for m in data["metrics"]]
        assert "duration_minutes" in keys
        assert "rpe" in keys
        assert "srpe" in keys

    def test_wellness_metrics(self, admin_client):
        """Should return wellness-specific metrics."""
        resp = admin_client.get("/api/v1/database-analysis/domain/wellness/metrics")
        assert resp.status_code == 200
        data = resp.json()
        keys = [m["key"] for m in data["metrics"]]
        assert "sleep_quality" in keys
        assert "hooper_index" in keys

    def test_invalid_domain(self, admin_client):
        """Should return 422 for invalid domain."""
        resp = admin_client.get("/api/v1/database-analysis/domain/invalid/metrics")
        assert resp.status_code == 422


# ── Analysis engine unit tests ────────────────────────────────────────


class TestAnalysisEngine:
    """Test AnalysisEngine methods with mocked Supabase."""

    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_filter_athletes_boxing_science(self, mock_admin):
        """Should call get_admin_athletes for boxing_science source."""
        from app.schemas.database_analysis import DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [
            {"id": "a1", "gender": "male"},
            {"id": "a2", "gender": "female"},
        ]

        # Mock the chunked query for full athlete records
        mock_resp = MagicMock()
        mock_resp.data = [
            {"id": "a1", "gender": "male", "date_of_birth": None,
             "body_mass_kg": 75.0, "stature_cm": 180.0, "status": "professional"},
            {"id": "a2", "gender": "female", "date_of_birth": None,
             "body_mass_kg": 60.0, "stature_cm": 165.0, "status": "amateur"},
        ]
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_resp

        ids = AnalysisEngine.filter_athletes(mock_client, DataSource.BOXING_SCIENCE, None)
        assert len(ids) == 2
        mock_admin.assert_called_once_with(mock_client)

    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_filter_athletes_gender(self, mock_admin):
        """Should filter by gender."""
        from app.schemas.database_analysis import AthleteFilter, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [
            {"id": "a1", "gender": "male"},
            {"id": "a2", "gender": "female"},
        ]

        mock_resp = MagicMock()
        mock_resp.data = [
            {"id": "a1", "gender": "male", "date_of_birth": None,
             "body_mass_kg": 75.0, "stature_cm": None, "status": None},
            {"id": "a2", "gender": "female", "date_of_birth": None,
             "body_mass_kg": 60.0, "stature_cm": None, "status": None},
        ]
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_resp

        f = AthleteFilter(gender="male")
        ids = AnalysisEngine.filter_athletes(mock_client, DataSource.BOXING_SCIENCE, f)
        assert ids == ["a1"]

    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_filter_athletes_status(self, mock_admin):
        """Should filter by amateur/professional status."""
        from app.schemas.database_analysis import AthleteFilter, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}, {"id": "a2"}]

        mock_resp = MagicMock()
        mock_resp.data = [
            {"id": "a1", "gender": "male", "date_of_birth": None,
             "body_mass_kg": None, "stature_cm": None, "status": "amateur"},
            {"id": "a2", "gender": "male", "date_of_birth": None,
             "body_mass_kg": None, "stature_cm": None, "status": "professional"},
        ]
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_resp

        f = AthleteFilter(status="professional")
        ids = AnalysisEngine.filter_athletes(mock_client, DataSource.BOXING_SCIENCE, f)
        assert ids == ["a2"]

    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_filter_athletes_no_matches(self, mock_admin):
        """Should return empty list when no athletes match filters."""
        from app.schemas.database_analysis import AthleteFilter, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_resp = MagicMock()
        mock_resp.data = [
            {"id": "a1", "gender": "male", "date_of_birth": None,
             "body_mass_kg": None, "stature_cm": None, "status": None},
        ]
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_resp

        f = AthleteFilter(gender="female")
        ids = AnalysisEngine.filter_athletes(mock_client, DataSource.BOXING_SCIENCE, f)
        assert ids == []

    @patch("app.services.analysis_engine.get_opted_in_athletes")
    def test_filter_athletes_shared_pool(self, mock_opted):
        """Should call get_opted_in_athletes for shared_pool source."""
        from app.schemas.database_analysis import DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_opted.return_value = [{"id": "s1", "gender": "male"}]

        mock_resp = MagicMock()
        mock_resp.data = [
            {"id": "s1", "gender": "male", "date_of_birth": None,
             "body_mass_kg": None, "stature_cm": None, "status": None},
        ]
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_resp

        ids = AnalysisEngine.filter_athletes(mock_client, DataSource.SHARED_POOL, None)
        assert ids == ["s1"]
        mock_opted.assert_called_once_with(mock_client)

    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_filter_athletes_age_range(self, mock_admin):
        """Should filter by age range computed from DOB."""
        from app.schemas.database_analysis import AthleteFilter, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]

        mock_resp = MagicMock()
        mock_resp.data = [
            {"id": "a1", "gender": "male", "date_of_birth": "2000-01-01",
             "body_mass_kg": None, "stature_cm": None, "status": None},
            {"id": "a2", "gender": "male", "date_of_birth": "1990-01-01",
             "body_mass_kg": None, "stature_cm": None, "status": None},
            {"id": "a3", "gender": "male", "date_of_birth": None,
             "body_mass_kg": None, "stature_cm": None, "status": None},
        ]
        mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_resp

        # Only athletes aged 20-30 (a1 is ~26, a2 is ~36, a3 has no DOB)
        f = AthleteFilter(age_min=20, age_max=30)
        ids = AnalysisEngine.filter_athletes(mock_client, DataSource.BOXING_SCIENCE, f)
        assert "a1" in ids
        assert "a2" not in ids
        assert "a3" not in ids  # No DOB → excluded


class TestPerformanceAnalysis:
    """Test performance domain analysis."""

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_performance_basic(self, mock_admin, mock_query):
        """Should compute stats for performance metrics."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        # First call: athlete records for filtering
        athlete_records = [
            {"id": "a1", "gender": "male", "date_of_birth": None,
             "body_mass_kg": None, "stature_cm": None, "status": None},
        ]
        # Second call: performance events
        perf_events = [
            {"athlete_id": "a1", "metrics": {"height_cm": 35.0, "rsi": 1.5}, "event_date": "2024-01-01"},
            {"athlete_id": "a1", "metrics": {"height_cm": 37.0, "rsi": 1.7}, "event_date": "2024-02-01"},
        ]

        mock_query.side_effect = [athlete_records, perf_events]

        req = AnalysisRequest(domain="performance", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.domain == "performance"
        assert result.athlete_count == 1
        assert result.record_count == 2
        assert len(result.statistics) == 2

        # Check height_cm stats
        height_stat = next(s for s in result.statistics if s.metric == "height_cm")
        assert height_stat.count == 2
        assert height_stat.mean == 36.0
        assert height_stat.min_val == 35.0
        assert height_stat.max_val == 37.0

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_performance_no_data(self, mock_admin, mock_query):
        """Should return empty stats when no events found."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            [],
        ]

        req = AnalysisRequest(domain="performance", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.record_count == 0
        assert result.statistics == []

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_performance_metric_filter(self, mock_admin, mock_query):
        """Should only include requested metric keys."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource, PerformanceFilters
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            [{"athlete_id": "a1", "metrics": {"height_cm": 35.0, "rsi": 1.5}, "event_date": "2024-01-01"}],
        ]

        req = AnalysisRequest(
            domain="performance",
            data_source=DataSource.BOXING_SCIENCE,
            performance_filters=PerformanceFilters(metric_keys=["height_cm"]),
        )
        result = AnalysisEngine.run_analysis(mock_client, req)

        metric_keys = [s.metric for s in result.statistics]
        assert "height_cm" in metric_keys
        assert "rsi" not in metric_keys


class TestTrainingAnalysis:
    """Test training domain analysis."""

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_training_basic(self, mock_admin, mock_query):
        """Should compute stats for training metrics."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            [
                {"athlete_id": "a1", "duration_minutes": 60, "rpe": 7, "srpe": 420, "training_type": "boxing", "session_date": "2024-01-01"},
                {"athlete_id": "a1", "duration_minutes": 45, "rpe": 8, "srpe": 360, "training_type": "boxing", "session_date": "2024-01-02"},
            ],
        ]

        req = AnalysisRequest(domain="training", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.domain == "training"
        assert result.record_count == 2

        dur_stat = next(s for s in result.statistics if s.metric == "duration_minutes")
        assert dur_stat.mean == 52.5


class TestWellnessAnalysis:
    """Test wellness domain analysis."""

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_wellness_basic(self, mock_admin, mock_query):
        """Should compute stats for wellness scores."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            [
                {"athlete_id": "a1", "sleep_quality": 4, "fatigue": 3,
                 "muscle_soreness": 2, "stress_level": 3, "mood": 4,
                 "hooper_index": 12, "entry_date": "2024-01-01"},
            ],
        ]

        req = AnalysisRequest(domain="wellness", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.domain == "wellness"
        metric_keys = [s.metric for s in result.statistics]
        assert "sleep_quality" in metric_keys
        assert "hooper_index" in metric_keys


class TestVbtAnalysis:
    """Test VBT domain analysis."""

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_vbt_basic(self, mock_admin, mock_query):
        """Should compute stats for VBT sets."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            # VBT profiles
            [{"id": "p1", "athlete_id": "a1", "exercise_name": "Back Squat", "test_date": "2024-01-01"}],
            # VBT sets
            [
                {"profile_id": "p1", "load_kg": 80.0, "mean_velocity": 0.75},
                {"profile_id": "p1", "load_kg": 100.0, "mean_velocity": 0.50},
            ],
        ]

        req = AnalysisRequest(domain="vbt", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.domain == "vbt"
        assert result.record_count == 1  # 1 profile

        load_stat = next(s for s in result.statistics if s.metric == "load_kg")
        assert load_stat.count == 2
        assert load_stat.mean == 90.0


class TestLactateAnalysis:
    """Test lactate domain analysis."""

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_lactate_basic(self, mock_admin, mock_query):
        """Should compute stats for lactate thresholds."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            [
                {"id": "t1", "athlete_id": "a1", "test_date": "2024-01-01",
                 "test_type": "running", "lt1_speed": 10.0, "lt1_hr": 140,
                 "lt2_speed": 14.0, "lt2_hr": 170},
            ],
        ]

        req = AnalysisRequest(domain="lactate", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.domain == "lactate"
        metric_keys = [s.metric for s in result.statistics]
        assert "lt1_speed" in metric_keys
        assert "lt2_hr" in metric_keys


class TestAirBikeAnalysis:
    """Test air bike domain analysis."""

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_air_bike_basic(self, mock_admin, mock_query):
        """Should compute stats for air bike power metrics."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            # Air bike tests
            [{"id": "t1", "athlete_id": "a1", "test_date": "2024-01-01"}],
            # Air bike sprints
            [
                {"test_id": "t1", "sprint_duration_s": 7, "peak_power_w": 800, "avg_power_w": 600},
                {"test_id": "t1", "sprint_duration_s": 14, "peak_power_w": 700, "avg_power_w": 500},
            ],
        ]

        req = AnalysisRequest(domain="air_bike", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.domain == "air_bike"
        peak_stat = next(s for s in result.statistics if s.metric == "peak_power_w")
        assert peak_stat.count == 2
        assert peak_stat.mean == 750.0


class TestAssessmentAnalysis:
    """Test movement assessment domain analysis."""

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_assessment_prevalence(self, mock_admin, mock_query):
        """Should compute dysfunction prevalence from JSONB findings."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}, {"id": "a2"}]

        mock_query.side_effect = [
            [
                {"id": "a1", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
                {"id": "a2", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
            ],
            [
                {"athlete_id": "a1", "assessment_type": "overhead_squat",
                 "assessment_date": "2024-01-01",
                 "findings": {
                     "knees": {"valgus": {"observed": True, "severity": "mild"}},
                     "lphc": {"forward_lean": {"observed": True, "severity": "moderate"}},
                 }},
                {"athlete_id": "a2", "assessment_type": "overhead_squat",
                 "assessment_date": "2024-01-02",
                 "findings": {
                     "knees": {"valgus": {"observed": True, "severity": "significant"}},
                     "lphc": {"forward_lean": {"observed": False}},
                 }},
            ],
        ]

        req = AnalysisRequest(domain="assessments", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.domain == "assessments"
        assert result.athlete_count == 2
        assert result.record_count == 2
        assert len(result.dysfunction_prevalence) > 0

        # Both athletes had knee valgus
        valgus = next(d for d in result.dysfunction_prevalence
                      if d.region == "knees" and d.dysfunction == "valgus")
        assert valgus.count == 2
        assert valgus.total_assessed == 2
        assert valgus.prevalence_pct == 100.0

        # Only 1 had forward lean
        forward_lean = next(d for d in result.dysfunction_prevalence
                           if d.region == "lphc" and d.dysfunction == "forward_lean")
        assert forward_lean.count == 1
        assert forward_lean.prevalence_pct == 50.0


class TestEdgeCases:
    """Test edge cases."""

    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_empty_pool(self, mock_admin):
        """Should return zero counts when athlete pool is empty."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = []

        req = AnalysisRequest(domain="performance", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.athlete_count == 0
        assert result.record_count == 0
        assert result.statistics == []

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_single_value_sd_zero(self, mock_admin, mock_query):
        """Should handle single value (SD=0) gracefully."""
        from app.schemas.database_analysis import AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            [{"athlete_id": "a1", "metrics": {"height_cm": 35.0}, "event_date": "2024-01-01"}],
        ]

        req = AnalysisRequest(domain="performance", data_source=DataSource.BOXING_SCIENCE)
        result = AnalysisEngine.run_analysis(mock_client, req)

        stat = result.statistics[0]
        assert stat.count == 1
        assert stat.mean == 35.0
        assert stat.std_dev == 0.0
        assert stat.median == 35.0
        assert stat.min_val == 35.0
        assert stat.max_val == 35.0

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_combined_filters(self, mock_admin, mock_query):
        """Should apply multiple athlete filters simultaneously."""
        from app.schemas.database_analysis import AnalysisRequest, AthleteFilter, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]

        mock_query.side_effect = [
            [
                {"id": "a1", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": 75.0, "stature_cm": None, "status": "professional"},
                {"id": "a2", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": 60.0, "stature_cm": None, "status": "amateur"},
                {"id": "a3", "gender": "female", "date_of_birth": None,
                 "body_mass_kg": 75.0, "stature_cm": None, "status": "professional"},
            ],
            [{"athlete_id": "a1", "metrics": {"height_cm": 40.0}, "event_date": "2024-01-01"}],
        ]

        req = AnalysisRequest(
            domain="performance",
            data_source=DataSource.BOXING_SCIENCE,
            athlete_filter=AthleteFilter(gender="male", status="professional"),
        )
        result = AnalysisEngine.run_analysis(mock_client, req)

        # Only a1 matches (male + professional)
        assert result.athlete_count == 1


class TestAggregationModes:
    """Test per-athlete aggregation logic."""

    def test_apply_aggregation_all_records(self):
        """ALL_RECORDS should flatten all inner lists."""
        from app.schemas.database_analysis import AggregationMode
        from app.services.analysis_engine import _apply_aggregation

        athlete_dists = {
            "height_cm": {
                "a1": [30.0, 32.0, 34.0],
                "a2": [40.0, 42.0],
            },
        }
        result = _apply_aggregation(athlete_dists, AggregationMode.ALL_RECORDS)
        assert sorted(result["height_cm"]) == [30.0, 32.0, 34.0, 40.0, 42.0]

    def test_apply_aggregation_mean(self):
        """MEAN_PER_ATHLETE should compute per-athlete means."""
        from app.schemas.database_analysis import AggregationMode
        from app.services.analysis_engine import _apply_aggregation

        athlete_dists = {
            "height_cm": {
                "a1": [30.0, 32.0, 34.0],  # mean=32.0
                "a2": [40.0, 42.0],          # mean=41.0
            },
        }
        result = _apply_aggregation(athlete_dists, AggregationMode.MEAN_PER_ATHLETE)
        assert sorted(result["height_cm"]) == [32.0, 41.0]

    def test_apply_aggregation_median(self):
        """MEDIAN_PER_ATHLETE should compute per-athlete medians."""
        from app.schemas.database_analysis import AggregationMode
        from app.services.analysis_engine import _apply_aggregation

        athlete_dists = {
            "height_cm": {
                "a1": [30.0, 32.0, 40.0],  # median=32.0
                "a2": [40.0, 42.0],          # median=41.0
            },
        }
        result = _apply_aggregation(athlete_dists, AggregationMode.MEDIAN_PER_ATHLETE)
        assert sorted(result["height_cm"]) == [32.0, 41.0]

    def test_apply_aggregation_peak(self):
        """PEAK_PER_ATHLETE should take per-athlete max."""
        from app.schemas.database_analysis import AggregationMode
        from app.services.analysis_engine import _apply_aggregation

        athlete_dists = {
            "height_cm": {
                "a1": [30.0, 32.0, 34.0],  # peak=34.0
                "a2": [40.0, 42.0],          # peak=42.0
            },
        }
        result = _apply_aggregation(athlete_dists, AggregationMode.PEAK_PER_ATHLETE)
        assert sorted(result["height_cm"]) == [34.0, 42.0]

    def test_aggregation_single_record_per_athlete(self):
        """All modes should produce same result with single record per athlete."""
        from app.schemas.database_analysis import AggregationMode
        from app.services.analysis_engine import _apply_aggregation

        athlete_dists = {
            "rsi": {
                "a1": [1.5],
                "a2": [2.0],
            },
        }
        for mode in AggregationMode:
            result = _apply_aggregation(athlete_dists, mode)
            assert sorted(result["rsi"]) == [1.5, 2.0], f"Failed for {mode}"

    def test_aggregation_empty_values(self):
        """Should handle empty value lists gracefully."""
        from app.schemas.database_analysis import AggregationMode
        from app.services.analysis_engine import _apply_aggregation

        athlete_dists = {
            "height_cm": {
                "a1": [],
                "a2": [40.0],
            },
        }
        for mode in AggregationMode:
            result = _apply_aggregation(athlete_dists, mode)
            assert result["height_cm"] == [40.0], f"Failed for {mode}"

    def test_aggregation_empty_distributions(self):
        """Should return empty dict for empty input."""
        from app.schemas.database_analysis import AggregationMode
        from app.services.analysis_engine import _apply_aggregation

        result = _apply_aggregation({}, AggregationMode.MEAN_PER_ATHLETE)
        assert result == {}

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_performance_mean_per_athlete(self, mock_admin, mock_query):
        """Full integration: mean_per_athlete with 2 athletes, multiple records."""
        from app.schemas.database_analysis import AggregationMode, AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}, {"id": "a2"}]

        mock_query.side_effect = [
            # Athlete records
            [
                {"id": "a1", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
                {"id": "a2", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
            ],
            # Performance events — a1 has 3 records, a2 has 2
            [
                {"athlete_id": "a1", "metrics": {"height_cm": 30.0}, "event_date": "2024-01-01"},
                {"athlete_id": "a1", "metrics": {"height_cm": 32.0}, "event_date": "2024-02-01"},
                {"athlete_id": "a1", "metrics": {"height_cm": 34.0}, "event_date": "2024-03-01"},
                {"athlete_id": "a2", "metrics": {"height_cm": 40.0}, "event_date": "2024-01-01"},
                {"athlete_id": "a2", "metrics": {"height_cm": 42.0}, "event_date": "2024-02-01"},
            ],
        ]

        req = AnalysisRequest(
            domain="performance",
            data_source=DataSource.BOXING_SCIENCE,
            aggregation_mode=AggregationMode.MEAN_PER_ATHLETE,
        )
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.aggregation_mode == "mean_per_athlete"
        assert result.athlete_count == 2
        assert result.record_count == 5  # Total records still reported

        stat = next(s for s in result.statistics if s.metric == "height_cm")
        # a1 mean=32.0, a2 mean=41.0 → group mean = 36.5
        assert stat.count == 2  # 2 athletes
        assert stat.mean == 36.5

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_vbt_aggregation(self, mock_admin, mock_query):
        """VBT sets correctly mapped through profiles to athletes."""
        from app.schemas.database_analysis import AggregationMode, AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}, {"id": "a2"}]

        mock_query.side_effect = [
            # Athlete records
            [
                {"id": "a1", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
                {"id": "a2", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
            ],
            # VBT profiles
            [
                {"id": "p1", "athlete_id": "a1", "exercise_name": "Squat", "test_date": "2024-01-01"},
                {"id": "p2", "athlete_id": "a2", "exercise_name": "Squat", "test_date": "2024-01-01"},
            ],
            # VBT sets
            [
                {"profile_id": "p1", "load_kg": 80.0, "mean_velocity": 0.8},
                {"profile_id": "p1", "load_kg": 100.0, "mean_velocity": 0.6},
                {"profile_id": "p2", "load_kg": 90.0, "mean_velocity": 0.7},
                {"profile_id": "p2", "load_kg": 110.0, "mean_velocity": 0.5},
            ],
        ]

        req = AnalysisRequest(
            domain="vbt",
            data_source=DataSource.BOXING_SCIENCE,
            aggregation_mode=AggregationMode.PEAK_PER_ATHLETE,
        )
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.aggregation_mode == "peak_per_athlete"
        load_stat = next(s for s in result.statistics if s.metric == "load_kg")
        # a1 peak=100, a2 peak=110 → group mean=105
        assert load_stat.count == 2
        assert load_stat.mean == 105.0

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_air_bike_aggregation(self, mock_admin, mock_query):
        """Air bike sprints correctly mapped through tests to athletes."""
        from app.schemas.database_analysis import AggregationMode, AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}, {"id": "a2"}]

        mock_query.side_effect = [
            # Athlete records
            [
                {"id": "a1", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
                {"id": "a2", "gender": "male", "date_of_birth": None,
                 "body_mass_kg": None, "stature_cm": None, "status": None},
            ],
            # Air bike tests
            [
                {"id": "t1", "athlete_id": "a1", "test_date": "2024-01-01"},
                {"id": "t2", "athlete_id": "a2", "test_date": "2024-01-01"},
            ],
            # Sprints
            [
                {"test_id": "t1", "sprint_duration_s": 7, "peak_power_w": 800, "avg_power_w": 600},
                {"test_id": "t1", "sprint_duration_s": 14, "peak_power_w": 700, "avg_power_w": 500},
                {"test_id": "t2", "sprint_duration_s": 7, "peak_power_w": 900, "avg_power_w": 700},
            ],
        ]

        req = AnalysisRequest(
            domain="air_bike",
            data_source=DataSource.BOXING_SCIENCE,
            aggregation_mode=AggregationMode.MEAN_PER_ATHLETE,
        )
        result = AnalysisEngine.run_analysis(mock_client, req)

        assert result.aggregation_mode == "mean_per_athlete"
        peak_stat = next(s for s in result.statistics if s.metric == "peak_power_w")
        # a1 mean peak=(800+700)/2=750, a2 mean peak=900 → group mean=825
        assert peak_stat.count == 2
        assert peak_stat.mean == 825.0

    @patch("app.services.analysis_engine._chunked_in_query")
    @patch("app.services.analysis_engine.get_admin_athletes")
    def test_aggregation_mode_in_response(self, mock_admin, mock_query):
        """Response should include the aggregation_mode field."""
        from app.schemas.database_analysis import AggregationMode, AnalysisRequest, DataSource
        from app.services.analysis_engine import AnalysisEngine

        mock_client = MagicMock()
        mock_admin.return_value = [{"id": "a1"}]

        mock_query.side_effect = [
            [{"id": "a1", "gender": "male", "date_of_birth": None,
              "body_mass_kg": None, "stature_cm": None, "status": None}],
            [{"athlete_id": "a1", "metrics": {"height_cm": 35.0}, "event_date": "2024-01-01"}],
        ]

        req = AnalysisRequest(
            domain="performance",
            data_source=DataSource.BOXING_SCIENCE,
            aggregation_mode=AggregationMode.MEDIAN_PER_ATHLETE,
        )
        result = AnalysisEngine.run_analysis(mock_client, req)
        assert result.aggregation_mode == "median_per_athlete"
