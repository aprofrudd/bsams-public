"""Performance event schemas."""

from datetime import date, datetime
from typing import Any, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.metric_registry import ALLOWED_METRIC_KEYS


def validate_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Validate metrics dict: only known keys, numeric values in range."""
    if not metrics:
        return metrics

    for key, value in metrics.items():
        if key not in ALLOWED_METRIC_KEYS:
            raise ValueError(f"Unknown metric key: '{key}'")

        bounds = ALLOWED_METRIC_KEYS[key]
        # test_type is a string field
        if key == "test_type":
            if not isinstance(value, str):
                raise ValueError("test_type must be a string")
            if len(value) > 50:
                raise ValueError("test_type must be 50 characters or fewer")
            continue

        # All other metrics must be numeric
        if not isinstance(value, (int, float)):
            raise ValueError(f"Metric '{key}' must be a number, got {type(value).__name__}")

        min_val, max_val = bounds
        if min_val is not None and value < min_val:
            raise ValueError(f"Metric '{key}' value {value} is below minimum {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"Metric '{key}' value {value} is above maximum {max_val}")

    return metrics


class PerformanceEventCreate(BaseModel):
    """Schema for creating a new performance event."""

    athlete_id: UUID
    event_date: date
    metrics: Dict[str, Any] = Field(
        ...,
        description="JSONB metrics data (e.g., {'test_type': 'CMJ', 'height_cm': 45.5})",
    )

    @field_validator("metrics")
    @classmethod
    def validate_metrics_field(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        return validate_metrics(v)


class PerformanceEventUpdate(BaseModel):
    """Schema for updating a performance event."""

    event_date: Optional[date] = None
    metrics: Optional[Dict[str, Any]] = None

    @field_validator("metrics")
    @classmethod
    def validate_metrics_field(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is not None:
            return validate_metrics(v)
        return v


class PerformanceEventResponse(BaseModel):
    """Schema for performance event responses. No metrics validation (DB may have legacy data)."""

    id: UUID
    athlete_id: UUID
    event_date: date
    metrics: Dict[str, Any] = Field(
        ...,
        description="JSONB metrics data",
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
