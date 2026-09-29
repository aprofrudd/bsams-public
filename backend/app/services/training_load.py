"""Training load analysis engine.

Calculates sRPE-based training load metrics:
- Daily load (sRPE = RPE x Duration)
- Weekly load (sum of daily loads over 7 days)
- Monotony (mean / SD of daily loads over 7 days)
- Strain (weekly load x monotony)
- ACWR (acute:chronic workload ratio - 7-day / 28-day rolling average)
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

from dataclasses import dataclass


@dataclass
class DailyLoad:
    """A single day's aggregated training load."""
    date: date
    total_srpe: int
    session_count: int


@dataclass
class LoadAnalysis:
    """Complete load analysis result for an athlete."""
    daily_loads: List[DailyLoad]
    weekly_load: Optional[int]
    monotony: Optional[float]
    strain: Optional[float]
    acwr: Optional[float]
    acute_load: Optional[float]
    chronic_load: Optional[float]


class TrainingLoadEngine:
    """Engine for training load calculations."""

    @staticmethod
    def calculate_daily_loads(
        sessions: List[Dict],
        start_date: date,
        end_date: date,
    ) -> List[DailyLoad]:
        """Aggregate session sRPE by date, including zero-load days."""
        # Group sessions by date
        load_by_date: Dict[date, DailyLoad] = {}
        for session in sessions:
            session_date = session["session_date"]
            if isinstance(session_date, str):
                session_date = date.fromisoformat(session_date)

            srpe = session.get("srpe") or 0
            if srpe == 0:
                # Fallback: compute from rpe * duration (handles None values)
                rpe = session.get("rpe") or 0
                duration = session.get("duration_minutes") or 0
                srpe = rpe * duration

            if session_date in load_by_date:
                load_by_date[session_date].total_srpe += srpe
                load_by_date[session_date].session_count += 1
            else:
                load_by_date[session_date] = DailyLoad(
                    date=session_date,
                    total_srpe=srpe,
                    session_count=1,
                )

        # Fill in zero-load days
        current = start_date
        while current <= end_date:
            if current not in load_by_date:
                load_by_date[current] = DailyLoad(
                    date=current,
                    total_srpe=0,
                    session_count=0,
                )
            current += timedelta(days=1)

        return sorted(load_by_date.values(), key=lambda d: d.date)

    @staticmethod
    def calculate_weekly_load(daily_loads: List[DailyLoad], target_date: date) -> Optional[int]:
        """Sum of daily loads over the 7 days ending on target_date."""
        week_start = target_date - timedelta(days=6)
        week_loads = [d for d in daily_loads if week_start <= d.date <= target_date]
        if not week_loads:
            return None
        return sum(d.total_srpe for d in week_loads)

    @staticmethod
    def calculate_monotony(daily_loads: List[DailyLoad], target_date: date) -> Optional[float]:
        """Monotony = mean / SD of daily loads over 7 days.

        High monotony (>2.0) indicates low variation in training load,
        which increases injury risk.
        """
        week_start = target_date - timedelta(days=6)
        week_loads = [d.total_srpe for d in daily_loads if week_start <= d.date <= target_date]

        if len(week_loads) < 7:
            return None

        mean = sum(week_loads) / len(week_loads)
        if mean == 0:
            return None

        variance = sum((x - mean) ** 2 for x in week_loads) / len(week_loads)
        sd = variance ** 0.5

        if sd == 0:
            return None

        return round(mean / sd, 2)

    @staticmethod
    def calculate_strain(weekly_load: Optional[int], monotony: Optional[float]) -> Optional[float]:
        """Strain = weekly load x monotony.

        Strain > 6000 is associated with increased illness risk.
        """
        if weekly_load is None or monotony is None:
            return None
        return round(weekly_load * monotony, 2)

    @staticmethod
    def calculate_acwr(daily_loads: List[DailyLoad], target_date: date) -> Optional[float]:
        """Acute:Chronic Workload Ratio.

        Acute = mean daily load over 7 days
        Chronic = mean daily load over 28 days
        ACWR = acute / chronic

        Optimal range: 0.8 - 1.3
        High risk: > 1.5
        """
        acute_start = target_date - timedelta(days=6)
        chronic_start = target_date - timedelta(days=27)

        acute_loads = [d.total_srpe for d in daily_loads if acute_start <= d.date <= target_date]
        chronic_loads = [d.total_srpe for d in daily_loads if chronic_start <= d.date <= target_date]

        if len(acute_loads) < 7 or len(chronic_loads) < 28:
            return None

        acute_mean = sum(acute_loads) / len(acute_loads)
        chronic_mean = sum(chronic_loads) / len(chronic_loads)

        if chronic_mean == 0:
            return None

        return round(acute_mean / chronic_mean, 2)

    @classmethod
    def analyze(
        cls,
        sessions: List[Dict],
        days: int = 28,
        target_date: Optional[date] = None,
    ) -> LoadAnalysis:
        """Run full load analysis for an athlete."""
        if target_date is None:
            target_date = date.today()

        start_date = target_date - timedelta(days=days - 1)
        daily_loads = cls.calculate_daily_loads(sessions, start_date, target_date)

        weekly_load = cls.calculate_weekly_load(daily_loads, target_date)
        monotony = cls.calculate_monotony(daily_loads, target_date)
        strain = cls.calculate_strain(weekly_load, monotony)
        acwr = cls.calculate_acwr(daily_loads, target_date)

        # Calculate acute and chronic for frontend display
        acute_start = target_date - timedelta(days=6)
        chronic_start = target_date - timedelta(days=27)

        acute_loads = [d.total_srpe for d in daily_loads if acute_start <= d.date <= target_date]
        chronic_loads = [d.total_srpe for d in daily_loads if chronic_start <= d.date <= target_date]

        acute_load = round(sum(acute_loads) / len(acute_loads), 2) if len(acute_loads) >= 7 else None
        chronic_load = round(sum(chronic_loads) / len(chronic_loads), 2) if len(chronic_loads) >= 28 else None

        return LoadAnalysis(
            daily_loads=daily_loads,
            weekly_load=weekly_load,
            monotony=monotony,
            strain=strain,
            acwr=acwr,
            acute_load=acute_load,
            chronic_load=chronic_load,
        )
