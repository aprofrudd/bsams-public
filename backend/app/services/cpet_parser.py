"""CPET gas analysis file parser.

Parses Excel (.xlsx) and CSV files from metabolic carts (MetaSoft, COSMED, Cortex).
Handles time-series data extraction, stage detection, and per-stage averaging.
"""

import csv
import io
import logging
import re
from dataclasses import dataclass, field
from statistics import median
from typing import Optional

logger = logging.getLogger(__name__)

# Column aliases mapping canonical names to possible header variations
COLUMN_ALIASES: dict[str, list[str]] = {
    "elapsed_s": ["t", "time", "elapsed_s", "elapsed", "time_s"],
    "vo2_l_min": [
        "v'o2", "vo2", "v'o2 (l/min)", "vo2 (l/min)", "vo2_l_min", "vo2 l/min",
        "oxygen uptake",
    ],
    "vo2_ml_kg_min": [
        "v'o2/kg", "vo2/kg", "v'o2/kg (ml/min/kg)", "vo2/kg (ml/min/kg)",
        "vo2_ml_kg_min", "vo2 ml/kg/min", "v'o2 (ml/min/kg)",
        "relative oxygen uptake",
    ],
    "vco2_l_min": [
        "v'co2", "vco2", "v'co2 (l/min)", "vco2 (l/min)", "vco2_l_min", "vco2 l/min",
        "carbon dioxide output",
    ],
    "rer": ["rer", "r", "rq", "rer (ratio)", "respiratory exchange ratio"],
    "ve_l_min": [
        "v'e", "ve", "v'e (l/min)", "ve (l/min)", "ve_l_min", "ve l/min",
        "minute ventilation",
    ],
    "bf_per_min": [
        "bf", "bf (1/min)", "bf_per_min", "rr", "breathing frequency", "bf (rpm)",
    ],
    "vt_l": ["vt", "vt (l)", "vt_l", "tidal volume"],
    "hr_bpm": ["hr", "hr (bpm)", "hr_bpm", "heart rate", "hr (1/min)"],
    "fat_gh": [
        "fat", "fat (g/h)", "fat_gh", "fat g/h", "fat oxidation",
        "fat utilization rate",
    ],
    "cho_gh": [
        "cho", "cho (g/h)", "cho_gh", "cho g/h", "cho oxidation",
        "cho utilization rate",
    ],
    "ee_kcal_h": ["ee", "ee (kcal/h)", "ee_kcal_h", "energy expenditure"],
    "cho_ee_kcal_h": [
        "cho ee", "cho ee (kcal/h)", "cho_ee_kcal_h", "cho energy",
        "cho energy expenditure",
    ],
    "fat_ee_kcal_h": [
        "fat ee", "fat ee (kcal/h)", "fat_ee_kcal_h", "fat energy",
        "fat energy expenditure",
    ],
    "work_rate_w": [
        "work rate", "work rate (w)", "power", "power (w)", "work_rate_w",
        "watt", "watts", "w",
    ],
}


@dataclass
class ParsedSample:
    """A single parsed time-series data point."""

    elapsed_s: float
    vo2_l_min: Optional[float] = None
    vo2_ml_kg_min: Optional[float] = None
    vco2_l_min: Optional[float] = None
    rer: Optional[float] = None
    ve_l_min: Optional[float] = None
    bf_per_min: Optional[float] = None
    vt_l: Optional[float] = None
    hr_bpm: Optional[int] = None
    fat_gh: Optional[float] = None
    cho_gh: Optional[float] = None
    ee_kcal_h: Optional[float] = None
    cho_ee_kcal_h: Optional[float] = None
    fat_ee_kcal_h: Optional[float] = None
    work_rate_w: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dict, omitting None values."""
        d: dict = {"elapsed_s": self.elapsed_s}
        for key in [
            "vo2_l_min", "vo2_ml_kg_min", "vco2_l_min", "rer", "ve_l_min",
            "bf_per_min", "vt_l", "hr_bpm", "fat_gh", "cho_gh", "ee_kcal_h",
            "cho_ee_kcal_h", "fat_ee_kcal_h", "work_rate_w",
        ]:
            val = getattr(self, key)
            if val is not None:
                d[key] = val
        return d


@dataclass
class StageAverage:
    """Computed per-stage average metrics."""

    stage_number: int
    intensity_value: Optional[float] = None
    avg_vo2_l_min: Optional[float] = None
    avg_vo2_ml_kg_min: Optional[float] = None
    avg_vco2_l_min: Optional[float] = None
    avg_rer: Optional[float] = None
    avg_ve_l_min: Optional[float] = None
    avg_bf_per_min: Optional[float] = None
    avg_vt_l: Optional[float] = None
    avg_hr_bpm: Optional[float] = None
    avg_fat_gh: Optional[float] = None
    avg_cho_gh: Optional[float] = None
    avg_ee_kcal_h: Optional[float] = None
    avg_cho_ee_kcal_h: Optional[float] = None
    avg_fat_ee_kcal_h: Optional[float] = None
    data_point_count: int = 0

    def to_dict(self) -> dict:
        d: dict = {"stage_number": self.stage_number, "data_point_count": self.data_point_count}
        for key in [
            "intensity_value", "avg_vo2_l_min", "avg_vo2_ml_kg_min", "avg_vco2_l_min",
            "avg_rer", "avg_ve_l_min", "avg_bf_per_min", "avg_vt_l", "avg_hr_bpm",
            "avg_fat_gh", "avg_cho_gh", "avg_ee_kcal_h", "avg_cho_ee_kcal_h",
            "avg_fat_ee_kcal_h",
        ]:
            val = getattr(self, key)
            if val is not None:
                d[key] = val
        return d


@dataclass
class ParseResult:
    """Complete parse result."""

    samples: list[ParsedSample]
    stage_averages: list[StageAverage]
    interval_seconds: int
    column_mapping: dict[str, str]
    columns_detected: list[str]


def parse_time(value: str) -> Optional[float]:
    """Parse h:mm:ss.ms or mm:ss.ms or seconds into elapsed seconds."""
    value = value.strip()
    if not value:
        return None

    # Try pure numeric first
    try:
        return float(value)
    except ValueError:
        pass

    # Parse h:mm:ss.ms or mm:ss.ms or h:mm:ss
    match = re.match(r"^(\d+):(\d{1,2}):(\d{1,2})(?:\.(\d+))?$", value)
    if match:
        h, m, s = int(match.group(1)), int(match.group(2)), int(match.group(3))
        ms = int(match.group(4)) if match.group(4) else 0
        # Normalise ms: "5" -> 500ms, "50" -> 500ms, "500" -> 500ms
        ms_str = (match.group(4) or "0").ljust(3, "0")[:3]
        ms = int(ms_str)
        return h * 3600 + m * 60 + s + ms / 1000.0

    match = re.match(r"^(\d+):(\d{1,2})(?:\.(\d+))?$", value)
    if match:
        m, s = int(match.group(1)), int(match.group(2))
        ms_str = (match.group(3) or "0").ljust(3, "0")[:3]
        ms = int(ms_str)
        return m * 60 + s + ms / 1000.0

    return None


def _safe_float(value: str) -> Optional[float]:
    """Parse a string to float, returning None on failure."""
    if value is None:
        return None
    value = str(value).strip()
    if not value or value == "-" or value.lower() in ("nan", "n/a", ""):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: str) -> Optional[int]:
    """Parse a string to int, returning None on failure."""
    f = _safe_float(value)
    return int(round(f)) if f is not None else None


def _build_column_mapping(headers: list[str]) -> dict[str, str]:
    """Build mapping from canonical column names to actual header names."""
    mapping: dict[str, str] = {}
    normalised_headers = {h.strip().lower(): h.strip() for h in headers}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in normalised_headers:
                mapping[canonical] = normalised_headers[alias.lower()]
                break

    return mapping


def _find_header_row(rows: list[list[str]], max_scan: int = 50) -> Optional[int]:
    """Find the header row by scanning for the time column."""
    for i, row in enumerate(rows[:max_scan]):
        for cell in row:
            cell_str = str(cell).strip().lower()
            if cell_str in ("t", "time", "elapsed_s", "elapsed"):
                return i
    return None


def _detect_interval(samples: list[ParsedSample]) -> int:
    """Detect recording interval from median time delta."""
    if len(samples) < 2:
        return 30

    deltas = []
    for i in range(1, min(len(samples), 20)):
        delta = samples[i].elapsed_s - samples[i - 1].elapsed_s
        if delta > 0:
            deltas.append(delta)

    if not deltas:
        return 30

    med = median(deltas)
    # Round to nearest standard interval
    return 60 if med > 45 else 30


def _parse_row(row_data: dict[str, str], mapping: dict[str, str]) -> Optional[ParsedSample]:
    """Parse a single row using the column mapping."""
    time_col = mapping.get("elapsed_s")
    if not time_col or time_col not in row_data:
        return None

    elapsed = parse_time(str(row_data[time_col]))
    if elapsed is None:
        return None

    sample = ParsedSample(elapsed_s=elapsed)

    float_fields = [
        "vo2_l_min", "vo2_ml_kg_min", "vco2_l_min", "rer", "ve_l_min",
        "bf_per_min", "vt_l", "fat_gh", "cho_gh", "ee_kcal_h",
        "cho_ee_kcal_h", "fat_ee_kcal_h", "work_rate_w",
    ]
    for fld in float_fields:
        col = mapping.get(fld)
        if col and col in row_data:
            setattr(sample, fld, _safe_float(str(row_data[col])))

    # HR as int
    hr_col = mapping.get("hr_bpm")
    if hr_col and hr_col in row_data:
        sample.hr_bpm = _safe_int(str(row_data[hr_col]))

    return sample


def _detect_stages_cycling(samples: list[ParsedSample]) -> list[list[ParsedSample]]:
    """Detect stages for cycling by grouping consecutive rows with same work_rate_w."""
    if not samples:
        return []

    stages: list[list[ParsedSample]] = []
    current_power: Optional[float] = None
    current_group: list[ParsedSample] = []

    for s in samples:
        if s.work_rate_w is None:
            # Skip samples without power data
            if current_group:
                stages.append(current_group)
                current_group = []
                current_power = None
            continue

        if current_power is None or s.work_rate_w != current_power:
            if current_group:
                stages.append(current_group)
            current_group = [s]
            current_power = s.work_rate_w
        else:
            current_group.append(s)

    if current_group:
        stages.append(current_group)

    return stages


def _detect_stages_running(
    samples: list[ParsedSample],
    rest_start_seconds: int,
    stage_duration_seconds: int,
    rest_duration_seconds: int,
) -> list[list[ParsedSample]]:
    """Detect stages for running using time-boundary protocol config.

    Protocol: rest_start_seconds of initial rest, then repeating
    stage_duration_seconds exercise + rest_duration_seconds rest.
    """
    if not samples:
        return []

    stages: list[list[ParsedSample]] = []
    cycle_duration = stage_duration_seconds + rest_duration_seconds

    # Find max elapsed time
    max_time = max(s.elapsed_s for s in samples)

    # Calculate stage time windows
    stage_num = 0
    while True:
        stage_start = rest_start_seconds + stage_num * cycle_duration
        stage_end = stage_start + stage_duration_seconds
        if stage_start > max_time:
            break

        stage_samples = [s for s in samples if stage_start <= s.elapsed_s < stage_end]
        if stage_samples:
            stages.append(stage_samples)

        stage_num += 1

    return stages


def _average_stage(
    samples: list[ParsedSample],
    stage_number: int,
    averaging_method: str,
    interval_seconds: int,
    intensity_value: Optional[float] = None,
) -> StageAverage:
    """Compute averaged metrics for a stage."""
    if not samples:
        return StageAverage(stage_number=stage_number, intensity_value=intensity_value)

    # Apply averaging window
    if averaging_method == "last_60s" and len(samples) > 1:
        # Use last 60 seconds of stage data
        last_time = samples[-1].elapsed_s
        cutoff = last_time - 60
        window = [s for s in samples if s.elapsed_s > cutoff]
        if not window:
            window = samples
    else:
        window = samples

    n = len(window)
    avg = StageAverage(stage_number=stage_number, intensity_value=intensity_value, data_point_count=n)

    metric_fields = [
        ("vo2_l_min", "avg_vo2_l_min"),
        ("vo2_ml_kg_min", "avg_vo2_ml_kg_min"),
        ("vco2_l_min", "avg_vco2_l_min"),
        ("rer", "avg_rer"),
        ("ve_l_min", "avg_ve_l_min"),
        ("bf_per_min", "avg_bf_per_min"),
        ("vt_l", "avg_vt_l"),
        ("fat_gh", "avg_fat_gh"),
        ("cho_gh", "avg_cho_gh"),
        ("ee_kcal_h", "avg_ee_kcal_h"),
        ("cho_ee_kcal_h", "avg_cho_ee_kcal_h"),
        ("fat_ee_kcal_h", "avg_fat_ee_kcal_h"),
    ]

    for src, dst in metric_fields:
        vals = [getattr(s, src) for s in window if getattr(s, src) is not None]
        if vals:
            setattr(avg, dst, round(sum(vals) / len(vals), 2))

    # HR average
    hr_vals = [s.hr_bpm for s in window if s.hr_bpm is not None]
    if hr_vals:
        avg.avg_hr_bpm = round(sum(hr_vals) / len(hr_vals), 1)

    return avg


def _read_xlsx_rows(file_bytes: bytes) -> list[list[str]]:
    """Read all rows from the first sheet of an Excel file."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return []
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(c) if c is not None else "" for c in row])
    wb.close()
    return rows


def _read_csv_rows(file_bytes: bytes) -> list[list[str]]:
    """Read all rows from a CSV file."""
    text = file_bytes.decode("utf-8-sig")  # Handle BOM
    reader = csv.reader(io.StringIO(text))
    return [row for row in reader]


def parse_cpet_file(
    file_bytes: bytes,
    filename: str,
    test_type: str,
    stage_intensities: Optional[list[float]] = None,
    rest_start_seconds: int = 60,
    stage_duration_seconds: int = 180,
    rest_duration_seconds: int = 60,
    averaging_method: str = "last_60s",
) -> ParseResult:
    """Parse a CPET gas analysis file.

    Args:
        file_bytes: Raw file content
        filename: Original filename (for extension detection)
        test_type: 'running' or 'cycling'
        stage_intensities: Intensity values from lactate stages (for running mapping)
        rest_start_seconds: Initial rest period in seconds
        stage_duration_seconds: Exercise stage duration in seconds
        rest_duration_seconds: Rest between stages in seconds
        averaging_method: 'last_60s' or 'full_stage'

    Returns:
        ParseResult with samples, stage averages, interval, and column mapping.

    Raises:
        ValueError: If file cannot be parsed or has insufficient data.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "xlsx":
        rows = _read_xlsx_rows(file_bytes)
    elif ext == "csv":
        rows = _read_csv_rows(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Use .xlsx or .csv")

    if not rows:
        raise ValueError("File is empty")

    # Find header row
    header_idx = _find_header_row(rows)
    if header_idx is None:
        raise ValueError("Could not find header row (looking for time column: t, time, elapsed_s)")

    headers = [str(h).strip() for h in rows[header_idx]]
    mapping = _build_column_mapping(headers)

    if "elapsed_s" not in mapping:
        raise ValueError("Could not identify time column in file")

    # Parse data rows
    samples: list[ParsedSample] = []
    for row in rows[header_idx + 1:]:
        if len(row) < len(headers):
            row.extend([""] * (len(headers) - len(row)))
        row_dict = {headers[i]: row[i] for i in range(len(headers)) if i < len(row)}
        sample = _parse_row(row_dict, mapping)
        if sample is not None:
            samples.append(sample)

    if not samples:
        raise ValueError("No valid data rows found after header")

    # Detect interval
    interval = _detect_interval(samples)

    # Detect stages
    if test_type == "cycling":
        stage_groups = _detect_stages_cycling(samples)
    else:
        stage_groups = _detect_stages_running(
            samples, rest_start_seconds, stage_duration_seconds, rest_duration_seconds
        )

    if not stage_groups:
        raise ValueError("No stages detected in file")

    # Compute stage averages
    stage_averages: list[StageAverage] = []
    for i, group in enumerate(stage_groups):
        # For cycling, intensity is the work_rate_w of the group
        if test_type == "cycling":
            intensity = group[0].work_rate_w if group else None
        else:
            # For running, map to lactate stage intensities by stage number
            intensity = None
            if stage_intensities and i < len(stage_intensities):
                intensity = stage_intensities[i]

        avg = _average_stage(group, i + 1, averaging_method, interval, intensity)
        stage_averages.append(avg)

    columns_detected = [k for k in mapping.keys() if k != "elapsed_s"]

    return ParseResult(
        samples=samples,
        stage_averages=stage_averages,
        interval_seconds=interval,
        column_mapping=mapping,
        columns_detected=columns_detected,
    )
