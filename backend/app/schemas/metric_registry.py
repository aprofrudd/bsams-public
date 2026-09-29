"""Central metric registry — single source of truth for all metric definitions.

Used by:
- performance_event.py (validation)
- analysis.py (filtering non-metric keys)
- Frontend metricRegistry.ts mirrors this

Each metric definition includes:
- key: Database column/JSONB key
- label: Human-readable display label
- unit: Unit of measurement
- domain: Which section it belongs to (testing, training, wellness)
- group: Sub-category within domain (jump, vbt, mobility, metadata)
- range: (min, max) for validation (None = no numeric validation)
- higher_is_better: For Z-score coloring
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class MetricDefinition:
    key: str
    label: str
    unit: str
    domain: str  # "testing", "training", "wellness"
    group: str  # "jump", "vbt", "mobility", "metadata"
    range: Optional[Tuple[float, float]]  # (min, max), None for non-numeric
    higher_is_better: bool = True


# All metric definitions
METRIC_DEFINITIONS: list[MetricDefinition] = [
    # Jump testing metrics
    MetricDefinition("height_cm", "CMJ Height (cm)", "cm", "testing", "jump", (0, 200), True),
    MetricDefinition("sj_height_cm", "SJ Height (cm)", "cm", "testing", "jump", (0, 200), True),
    MetricDefinition("eur_cm", "Eccentric Utilisation Ratio (cm)", "cm", "testing", "jump", (-100, 200), True),
    MetricDefinition("rsi", "Reactive Strength Index", "", "testing", "jump", (0, 50), True),
    MetricDefinition("flight_time_ms", "Flight Time (ms)", "ms", "testing", "jump", (0, 2000), True),
    MetricDefinition("contraction_time_ms", "Contact Time (ms)", "ms", "testing", "jump", (0, 2000), False),
    # 10-5 pogo test metrics (distinct from CMJ-derived RSI above)
    MetricDefinition("pogo_flight_time_ms", "10-5 Pogo Flight Time (ms)", "ms", "testing", "jump", (0, 1500), True),
    MetricDefinition("pogo_contact_time_ms", "10-5 Pogo Contact Time (ms)", "ms", "testing", "jump", (0, 1500), False),
    MetricDefinition("pogo_rsi", "10-5 Pogo RSI", "", "testing", "jump", (0, 10), True),
    # VBT metrics
    MetricDefinition("mean_velocity_ms", "Mean Velocity (m/s)", "m/s", "testing", "vbt", (0, 5), True),
    MetricDefinition("peak_velocity_ms", "Peak Velocity (m/s)", "m/s", "testing", "vbt", (0, 10), True),
    MetricDefinition("mean_power_w", "Mean Power (W)", "W", "testing", "vbt", (0, 10000), True),
    MetricDefinition("peak_power_w", "Peak Power (W)", "W", "testing", "vbt", (0, 15000), True),
    MetricDefinition("bar_speed_ms", "Bar Speed (m/s)", "m/s", "testing", "vbt", (0, 5), True),
    MetricDefinition("rom_mm", "Range of Motion (mm)", "mm", "testing", "vbt", (0, 2000), True),
    MetricDefinition("time_to_peak_velocity_ms", "Time to Peak Velocity (ms)", "ms", "testing", "vbt", (0, 5000), False),
    MetricDefinition("rep_duration_ms", "Rep Duration (ms)", "ms", "testing", "vbt", (0, 10000), False),
    # Mobility metrics
    MetricDefinition("shoulder_ir_deg", "Shoulder Internal Rotation (deg)", "deg", "testing", "mobility", (0, 180), True),
    MetricDefinition("shoulder_er_deg", "Shoulder External Rotation (deg)", "deg", "testing", "mobility", (0, 180), True),
    MetricDefinition("hip_flexion_deg", "Hip Flexion (deg)", "deg", "testing", "mobility", (0, 180), True),
    MetricDefinition("ankle_dorsiflexion_deg", "Ankle Dorsiflexion (deg)", "deg", "testing", "mobility", (0, 90), True),
    MetricDefinition("thoracic_rotation_deg", "Thoracic Rotation (deg)", "deg", "testing", "mobility", (0, 90), True),
    # Isometric metrics
    MetricDefinition("iso_trunk_rotation_left_kg", "Iso Trunk Rotation Left (kg)", "kg", "testing", "isometric", (0, 500), True),
    MetricDefinition("iso_trunk_rotation_right_kg", "Iso Trunk Rotation Right (kg)", "kg", "testing", "isometric", (0, 500), True),
    MetricDefinition("grip_strength_left_kg", "Grip Strength Left (kg)", "kg", "testing", "isometric", (0, 200), True),
    MetricDefinition("grip_strength_right_kg", "Grip Strength Right (kg)", "kg", "testing", "isometric", (0, 200), True),
    MetricDefinition("grip_rfd_left_pct", "Grip RFD Left (%)", "%", "testing", "isometric", (0, 200), True),
    MetricDefinition("grip_rfd_right_pct", "Grip RFD Right (%)", "%", "testing", "isometric", (0, 200), True),
    # Rate of force development in N/s (optional — dynamometer may not report it).
    # Appended deliberately: testing/page.tsx defaults the Isometrics tab to ISOMETRIC_METRIC_KEYS[0].
    MetricDefinition("grip_rfd_left_n_s", "Grip RFD Left (N/s)", "N/s", "testing", "isometric", (0, 20000), True),
    MetricDefinition("grip_rfd_right_n_s", "Grip RFD Right (N/s)", "N/s", "testing", "isometric", (0, 20000), True),
    MetricDefinition("iso_trunk_rotation_rfd_left_n_s", "Iso Trunk Rotation RFD Left (N/s)", "N/s", "testing", "isometric", (0, 20000), True),
    MetricDefinition("iso_trunk_rotation_rfd_right_n_s", "Iso Trunk Rotation RFD Right (N/s)", "N/s", "testing", "isometric", (0, 20000), True),
    # Metadata (not used in benchmarks)
    MetricDefinition("body_mass_kg", "Body Mass (kg)", "kg", "testing", "metadata", (0, 500), False),
    MetricDefinition("test_type", "Test Type", "", "testing", "metadata", None, False),
]

# Derived lookup dicts
METRIC_BY_KEY = {m.key: m for m in METRIC_DEFINITIONS}
TESTING_METRICS = [m for m in METRIC_DEFINITIONS if m.domain == "testing"]
NON_METRIC_KEYS = {"test_type", "body_mass_kg"}

# For backwards compatibility with performance_event.py validation
ALLOWED_METRIC_KEYS = {
    m.key: m.range if m.range else (None, None)
    for m in METRIC_DEFINITIONS
    if m.domain == "testing"
}

METRIC_LABELS = {m.key: m.label for m in METRIC_DEFINITIONS}

# Group lookup for UI
METRIC_GROUPS = {}
for _m in METRIC_DEFINITIONS:
    if _m.group not in METRIC_GROUPS:
        METRIC_GROUPS[_m.group] = []
    METRIC_GROUPS[_m.group].append(_m)
