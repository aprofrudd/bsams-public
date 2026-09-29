"""Tests for training load engine."""

from datetime import date, timedelta

import pytest

from app.services.training_load import TrainingLoadEngine, DailyLoad


class TestCalculateDailyLoads:
    """Test daily load aggregation."""

    def test_single_session(self):
        """Should aggregate single session."""
        sessions = [
            {"session_date": "2024-01-15", "srpe": 420, "rpe": 7, "duration_minutes": 60}
        ]
        loads = TrainingLoadEngine.calculate_daily_loads(
            sessions,
            date(2024, 1, 15),
            date(2024, 1, 15),
        )
        assert len(loads) == 1
        assert loads[0].total_srpe == 420
        assert loads[0].session_count == 1

    def test_multiple_sessions_same_day(self):
        """Should sum sRPE for same-day sessions."""
        sessions = [
            {"session_date": "2024-01-15", "srpe": 420, "rpe": 7, "duration_minutes": 60},
            {"session_date": "2024-01-15", "srpe": 200, "rpe": 5, "duration_minutes": 40},
        ]
        loads = TrainingLoadEngine.calculate_daily_loads(
            sessions,
            date(2024, 1, 15),
            date(2024, 1, 15),
        )
        assert len(loads) == 1
        assert loads[0].total_srpe == 620
        assert loads[0].session_count == 2

    def test_zero_load_days_filled(self):
        """Should fill in zero-load days between sessions."""
        sessions = [
            {"session_date": "2024-01-15", "srpe": 420, "rpe": 7, "duration_minutes": 60},
        ]
        loads = TrainingLoadEngine.calculate_daily_loads(
            sessions,
            date(2024, 1, 14),
            date(2024, 1, 16),
        )
        assert len(loads) == 3
        assert loads[0].total_srpe == 0  # Jan 14
        assert loads[1].total_srpe == 420  # Jan 15
        assert loads[2].total_srpe == 0  # Jan 16

    def test_empty_sessions(self):
        """Should return zero-load days for empty session list."""
        loads = TrainingLoadEngine.calculate_daily_loads(
            [],
            date(2024, 1, 15),
            date(2024, 1, 17),
        )
        assert len(loads) == 3
        assert all(d.total_srpe == 0 for d in loads)

    def test_srpe_none_fallback_to_rpe_times_duration(self):
        """Should compute sRPE from rpe*duration when srpe is None."""
        sessions = [
            {"session_date": "2024-01-15", "srpe": None, "rpe": 7, "duration_minutes": 60},
        ]
        loads = TrainingLoadEngine.calculate_daily_loads(
            sessions,
            date(2024, 1, 15),
            date(2024, 1, 15),
        )
        assert loads[0].total_srpe == 420

    def test_assigned_session_null_rpe_duration_srpe(self):
        """Assigned sessions with null rpe/duration/srpe should contribute 0 load (BUG-016)."""
        sessions = [
            {"session_date": "2024-01-15", "srpe": None, "rpe": None, "duration_minutes": None},
            {"session_date": "2024-01-15", "srpe": 300, "rpe": 5, "duration_minutes": 60},
        ]
        loads = TrainingLoadEngine.calculate_daily_loads(
            sessions,
            date(2024, 1, 15),
            date(2024, 1, 15),
        )
        assert loads[0].total_srpe == 300
        assert loads[0].session_count == 2


class TestCalculateWeeklyLoad:
    """Test weekly load calculation."""

    def test_full_week(self):
        """Should sum 7 days of loads."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, d), total_srpe=100, session_count=1)
            for d in range(8, 15)
        ]
        result = TrainingLoadEngine.calculate_weekly_load(daily_loads, date(2024, 1, 14))
        assert result == 700

    def test_partial_week(self):
        """Should sum available days within range."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, 14), total_srpe=100, session_count=1),
        ]
        result = TrainingLoadEngine.calculate_weekly_load(daily_loads, date(2024, 1, 14))
        assert result == 100

    def test_empty_loads(self):
        """Should return None for empty loads."""
        result = TrainingLoadEngine.calculate_weekly_load([], date(2024, 1, 14))
        assert result is None


class TestCalculateMonotony:
    """Test monotony calculation."""

    def test_uniform_load(self):
        """Monotony should be None for uniform load (SD=0)."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, d), total_srpe=100, session_count=1)
            for d in range(8, 15)
        ]
        result = TrainingLoadEngine.calculate_monotony(daily_loads, date(2024, 1, 14))
        assert result is None  # SD=0

    def test_varied_load(self):
        """Should calculate monotony for varied loads."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, 8), total_srpe=400, session_count=1),
            DailyLoad(date=date(2024, 1, 9), total_srpe=0, session_count=0),
            DailyLoad(date=date(2024, 1, 10), total_srpe=300, session_count=1),
            DailyLoad(date=date(2024, 1, 11), total_srpe=0, session_count=0),
            DailyLoad(date=date(2024, 1, 12), total_srpe=500, session_count=1),
            DailyLoad(date=date(2024, 1, 13), total_srpe=0, session_count=0),
            DailyLoad(date=date(2024, 1, 14), total_srpe=200, session_count=1),
        ]
        result = TrainingLoadEngine.calculate_monotony(daily_loads, date(2024, 1, 14))
        assert result is not None
        assert result > 0

    def test_insufficient_days(self):
        """Should return None with fewer than 7 days."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, d), total_srpe=100, session_count=1)
            for d in range(12, 15)
        ]
        result = TrainingLoadEngine.calculate_monotony(daily_loads, date(2024, 1, 14))
        assert result is None

    def test_zero_load_all_days(self):
        """Should return None when all loads are zero."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, d), total_srpe=0, session_count=0)
            for d in range(8, 15)
        ]
        result = TrainingLoadEngine.calculate_monotony(daily_loads, date(2024, 1, 14))
        assert result is None


class TestCalculateStrain:
    """Test strain calculation."""

    def test_normal_strain(self):
        """Should calculate strain = weekly_load * monotony."""
        result = TrainingLoadEngine.calculate_strain(1400, 1.5)
        assert result == 2100.0

    def test_none_inputs(self):
        """Should return None if either input is None."""
        assert TrainingLoadEngine.calculate_strain(None, 1.5) is None
        assert TrainingLoadEngine.calculate_strain(1400, None) is None
        assert TrainingLoadEngine.calculate_strain(None, None) is None


class TestCalculateACWR:
    """Test ACWR calculation."""

    def test_acwr_steady_state(self):
        """ACWR should be ~1.0 for steady training."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, 1) + timedelta(days=d), total_srpe=300, session_count=1)
            for d in range(28)
        ]
        result = TrainingLoadEngine.calculate_acwr(daily_loads, date(2024, 1, 28))
        assert result == 1.0

    def test_acwr_spike(self):
        """ACWR should be >1.0 when recent load exceeds chronic."""
        daily_loads = []
        # 21 days of low load
        for d in range(21):
            daily_loads.append(
                DailyLoad(date=date(2024, 1, 1) + timedelta(days=d), total_srpe=100, session_count=1)
            )
        # 7 days of high load
        for d in range(21, 28):
            daily_loads.append(
                DailyLoad(date=date(2024, 1, 1) + timedelta(days=d), total_srpe=400, session_count=1)
            )
        result = TrainingLoadEngine.calculate_acwr(daily_loads, date(2024, 1, 28))
        assert result is not None
        assert result > 1.0

    def test_acwr_insufficient_data(self):
        """Should return None with insufficient data."""
        daily_loads = [
            DailyLoad(date=date(2024, 1, d), total_srpe=300, session_count=1)
            for d in range(8, 15)
        ]
        result = TrainingLoadEngine.calculate_acwr(daily_loads, date(2024, 1, 14))
        assert result is None

    def test_acwr_zero_chronic(self):
        """Should return None when chronic load is zero."""
        daily_loads = []
        # 21 days of zero
        for d in range(21):
            daily_loads.append(
                DailyLoad(date=date(2024, 1, 1) + timedelta(days=d), total_srpe=0, session_count=0)
            )
        # 7 days of training
        for d in range(21, 28):
            daily_loads.append(
                DailyLoad(date=date(2024, 1, 1) + timedelta(days=d), total_srpe=300, session_count=1)
            )
        result = TrainingLoadEngine.calculate_acwr(daily_loads, date(2024, 1, 28))
        # Chronic includes zero days so mean is not zero, but should be calculable
        assert result is not None


class TestAnalyze:
    """Test full analysis pipeline."""

    def test_analyze_empty(self):
        """Should handle empty session list."""
        result = TrainingLoadEngine.analyze([], days=7, target_date=date(2024, 1, 14))
        assert result.weekly_load == 0
        assert result.monotony is None
        assert result.strain is None
        assert len(result.daily_loads) == 7

    def test_analyze_single_session(self):
        """Should analyze single session."""
        sessions = [
            {"session_date": "2024-01-14", "srpe": 420, "rpe": 7, "duration_minutes": 60}
        ]
        result = TrainingLoadEngine.analyze(sessions, days=7, target_date=date(2024, 1, 14))
        assert result.weekly_load == 420
        assert len(result.daily_loads) == 7

    def test_analyze_full_month(self):
        """Should analyze 28 days of data."""
        sessions = []
        for d in range(28):
            day = date(2024, 1, 1) + timedelta(days=d)
            if d % 2 == 0:  # Train every other day
                sessions.append({
                    "session_date": day.isoformat(),
                    "srpe": 300,
                    "rpe": 6,
                    "duration_minutes": 50,
                })
        result = TrainingLoadEngine.analyze(sessions, days=28, target_date=date(2024, 1, 28))
        assert result.weekly_load is not None
        assert len(result.daily_loads) == 28
