"""Upload-related schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RowError(BaseModel):
    """Error information for a failed row."""

    row: int = Field(..., description="Row number (1-indexed)")
    reason: str = Field(..., description="Error description")


class CSVUploadResult(BaseModel):
    """Result of CSV upload processing."""

    processed: int = Field(..., description="Number of successfully processed rows")
    errors: List[RowError] = Field(default_factory=list, description="List of row errors")
    athlete_id: Optional[str] = Field(None, description="Athlete ID if single athlete upload")


class CSVColumnMapping(BaseModel):
    """Mapping configuration for CSV columns."""

    date_column: str = Field(default="Test Date", description="Column name for test date")
    mass_column: str = Field(default="Body Mass (kg)", description="Column name for body mass")
    athlete_column: Optional[str] = Field(default="Athlete", description="Column name for athlete name")
    first_name_column: Optional[str] = Field(default="First Name", description="Column for first name")
    surname_column: Optional[str] = Field(default="Surname", description="Column for surname")
    gender_column: Optional[str] = Field(default="Gender", description="Column for gender")

    # Metric mappings: CSV column name -> (test_type, metric_key)
    metric_columns: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {
            # Jump testing
            "CMJ Height (cm)": {"test_type": "CMJ", "metric_key": "height_cm"},
            "SJ Height (cm)": {"test_type": "SJ", "metric_key": "sj_height_cm"},
            "EUR (cm)": {"test_type": "CMJ", "metric_key": "eur_cm"},
            "RSI": {"test_type": "CMJ", "metric_key": "rsi"},
            "RSI Flight (ms)": {"test_type": "CMJ", "metric_key": "flight_time_ms"},
            "RSI Contact (ms)": {"test_type": "CMJ", "metric_key": "contraction_time_ms"},
            "CMJ RSI": {"test_type": "CMJ", "metric_key": "rsi"},
            "CMJ Flight Time (ms)": {"test_type": "CMJ", "metric_key": "flight_time_ms"},
            "CMJ Contraction Time (ms)": {"test_type": "CMJ", "metric_key": "contraction_time_ms"},
            # 10-5 pogo test (separate keys so it never merges with CMJ RSI)
            "10-5 Pogo Flight Time (ms)": {"test_type": "Pogo", "metric_key": "pogo_flight_time_ms"},
            "10-5 Pogo Contact Time (ms)": {"test_type": "Pogo", "metric_key": "pogo_contact_time_ms"},
            "10-5 Pogo RSI": {"test_type": "Pogo", "metric_key": "pogo_rsi"},
            "Pogo Flight (ms)": {"test_type": "Pogo", "metric_key": "pogo_flight_time_ms"},
            "Pogo Contact (ms)": {"test_type": "Pogo", "metric_key": "pogo_contact_time_ms"},
            "Pogo RSI": {"test_type": "Pogo", "metric_key": "pogo_rsi"},
            # VBT — GymAware format
            "Mean Velocity (m/s)": {"test_type": "VBT", "metric_key": "mean_velocity_ms"},
            "Peak Velocity (m/s)": {"test_type": "VBT", "metric_key": "peak_velocity_ms"},
            "Mean Power (W)": {"test_type": "VBT", "metric_key": "mean_power_w"},
            "Peak Power (W)": {"test_type": "VBT", "metric_key": "peak_power_w"},
            "ROM (mm)": {"test_type": "VBT", "metric_key": "rom_mm"},
            "Rep Duration (ms)": {"test_type": "VBT", "metric_key": "rep_duration_ms"},
            # VBT — PUSH Band format
            "Mean Velocity": {"test_type": "VBT", "metric_key": "mean_velocity_ms"},
            "Peak Velocity": {"test_type": "VBT", "metric_key": "peak_velocity_ms"},
            "Average Power": {"test_type": "VBT", "metric_key": "mean_power_w"},
            "Peak Power": {"test_type": "VBT", "metric_key": "peak_power_w"},
            # VBT — Tendo format
            "Bar Speed (m/s)": {"test_type": "VBT", "metric_key": "bar_speed_ms"},
            "Average Velocity (m/s)": {"test_type": "VBT", "metric_key": "mean_velocity_ms"},
            "Power (W)": {"test_type": "VBT", "metric_key": "mean_power_w"},
            # Mobility
            "Shoulder IR (deg)": {"test_type": "Mobility", "metric_key": "shoulder_ir_deg"},
            "Shoulder ER (deg)": {"test_type": "Mobility", "metric_key": "shoulder_er_deg"},
            "Hip Flexion (deg)": {"test_type": "Mobility", "metric_key": "hip_flexion_deg"},
            "Ankle Dorsiflexion (deg)": {"test_type": "Mobility", "metric_key": "ankle_dorsiflexion_deg"},
            "Thoracic Rotation (deg)": {"test_type": "Mobility", "metric_key": "thoracic_rotation_deg"},
            # Isometric
            "Isometric Trunk Rotation Left (kg)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_left_kg"},
            "Isometric Trunk Rotation Right (kg)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_right_kg"},
            "Iso Trunk Rotation L (kg)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_left_kg"},
            "Iso Trunk Rotation R (kg)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_right_kg"},
            "Grip Strength Left (kg)": {"test_type": "Isometric", "metric_key": "grip_strength_left_kg"},
            "Grip Strength Right (kg)": {"test_type": "Isometric", "metric_key": "grip_strength_right_kg"},
            "Grip Strength L (kg)": {"test_type": "Isometric", "metric_key": "grip_strength_left_kg"},
            "Grip Strength R (kg)": {"test_type": "Isometric", "metric_key": "grip_strength_right_kg"},
            "Grip RFD Left (%)": {"test_type": "Isometric", "metric_key": "grip_rfd_left_pct"},
            "Grip RFD Right (%)": {"test_type": "Isometric", "metric_key": "grip_rfd_right_pct"},
            "Grip RFD L (%)": {"test_type": "Isometric", "metric_key": "grip_rfd_left_pct"},
            "Grip RFD R (%)": {"test_type": "Isometric", "metric_key": "grip_rfd_right_pct"},
            "Grip RFD Left (N/s)": {"test_type": "Isometric", "metric_key": "grip_rfd_left_n_s"},
            "Grip RFD Right (N/s)": {"test_type": "Isometric", "metric_key": "grip_rfd_right_n_s"},
            "Grip RFD L (N/s)": {"test_type": "Isometric", "metric_key": "grip_rfd_left_n_s"},
            "Grip RFD R (N/s)": {"test_type": "Isometric", "metric_key": "grip_rfd_right_n_s"},
            "Iso Trunk Rotation RFD Left (N/s)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_rfd_left_n_s"},
            "Iso Trunk Rotation RFD Right (N/s)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_rfd_right_n_s"},
            "Iso Trunk Rotation RFD L (N/s)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_rfd_left_n_s"},
            "Iso Trunk Rotation RFD R (N/s)": {"test_type": "Isometric", "metric_key": "iso_trunk_rotation_rfd_right_n_s"},
        },
        description="Mapping of CSV columns to metric structure",
    )
