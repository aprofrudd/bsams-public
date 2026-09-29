"""Tests for CPET gas analysis parser."""

import csv
import io

import pytest

from app.services.cpet_parser import (
    ParsedSample,
    _average_stage,
    _build_column_mapping,
    _detect_interval,
    _detect_stages_cycling,
    _detect_stages_running,
    _find_header_row,
    parse_cpet_file,
    parse_time,
)


class TestParseTime:
    """Tests for time string parsing."""

    def test_seconds_float(self):
        assert parse_time("120.5") == 120.5

    def test_mmss_format(self):
        assert parse_time("2:30") == 150.0

    def test_hmmss_format(self):
        assert parse_time("1:02:30") == 3750.0

    def test_hmmss_with_ms(self):
        result = parse_time("0:01:30.500")
        assert result == pytest.approx(90.5)

    def test_mmss_with_ms(self):
        result = parse_time("1:30.5")
        assert result == pytest.approx(90.5)

    def test_empty_returns_none(self):
        assert parse_time("") is None

    def test_invalid_returns_none(self):
        assert parse_time("abc") is None

    def test_pure_int(self):
        assert parse_time("60") == 60.0


class TestColumnMapping:
    """Tests for flexible column alias mapping."""

    def test_standard_metasoft_headers(self):
        headers = ["t", "V'O2", "V'CO2", "RER", "V'E", "BF", "VT", "HR", "FAT", "CHO"]
        mapping = _build_column_mapping(headers)
        assert mapping["elapsed_s"] == "t"
        assert mapping["vo2_l_min"] == "V'O2"
        assert mapping["vco2_l_min"] == "V'CO2"
        assert mapping["rer"] == "RER"
        assert mapping["ve_l_min"] == "V'E"
        assert mapping["bf_per_min"] == "BF"
        assert mapping["hr_bpm"] == "HR"
        assert mapping["fat_gh"] == "FAT"

    def test_cosmed_headers(self):
        headers = ["time", "VO2 (L/min)", "VCO2 (L/min)", "HR (bpm)", "Work Rate (W)"]
        mapping = _build_column_mapping(headers)
        assert mapping["elapsed_s"] == "time"
        assert mapping["vo2_l_min"] == "VO2 (L/min)"
        assert mapping["hr_bpm"] == "HR (bpm)"
        assert mapping["work_rate_w"] == "Work Rate (W)"

    def test_case_insensitive(self):
        headers = ["T", "vo2", "hr"]
        mapping = _build_column_mapping(headers)
        assert "elapsed_s" in mapping
        assert "vo2_l_min" in mapping
        assert "hr_bpm" in mapping

    def test_no_time_column(self):
        mapping = _build_column_mapping(["speed", "power"])
        assert "elapsed_s" not in mapping


class TestFindHeaderRow:
    """Tests for header row auto-detection."""

    def test_header_at_row_0(self):
        rows = [["t", "V'O2", "HR"], ["60", "2.5", "130"]]
        assert _find_header_row(rows) == 0

    def test_header_after_metadata(self):
        rows = [
            ["Patient", "John Doe"],
            ["Date", "2024-01-15"],
            ["t", "V'O2", "HR"],
            ["60", "2.5", "130"],
        ]
        assert _find_header_row(rows) == 2

    def test_no_header_found(self):
        rows = [["speed", "power"], ["10", "200"]]
        assert _find_header_row(rows) is None


class TestDetectInterval:
    """Tests for interval auto-detection."""

    def test_30s_interval(self):
        samples = [ParsedSample(elapsed_s=i * 30) for i in range(10)]
        assert _detect_interval(samples) == 30

    def test_60s_interval(self):
        samples = [ParsedSample(elapsed_s=i * 60) for i in range(10)]
        assert _detect_interval(samples) == 60

    def test_single_sample(self):
        assert _detect_interval([ParsedSample(elapsed_s=0)]) == 30


class TestDetectStagesCycling:
    """Tests for cycling stage detection by work rate grouping."""

    def test_three_stages(self):
        samples = [
            ParsedSample(elapsed_s=0, work_rate_w=80),
            ParsedSample(elapsed_s=30, work_rate_w=80),
            ParsedSample(elapsed_s=60, work_rate_w=80),
            ParsedSample(elapsed_s=90, work_rate_w=120),
            ParsedSample(elapsed_s=120, work_rate_w=120),
            ParsedSample(elapsed_s=150, work_rate_w=160),
        ]
        stages = _detect_stages_cycling(samples)
        assert len(stages) == 3
        assert len(stages[0]) == 3
        assert len(stages[1]) == 2
        assert len(stages[2]) == 1
        assert stages[0][0].work_rate_w == 80
        assert stages[1][0].work_rate_w == 120

    def test_no_work_rate(self):
        samples = [ParsedSample(elapsed_s=0), ParsedSample(elapsed_s=30)]
        stages = _detect_stages_cycling(samples)
        assert len(stages) == 0

    def test_empty(self):
        assert _detect_stages_cycling([]) == []


class TestDetectStagesRunning:
    """Tests for running stage detection via time-boundary config."""

    def test_default_protocol(self):
        # rest_start=60, stage=180, rest=60 => cycle=240
        # Stage 1: 60-240, Stage 2: 300-480, Stage 3: 540-720
        samples = [ParsedSample(elapsed_s=t) for t in range(0, 730, 30)]
        stages = _detect_stages_running(samples, 60, 180, 60)
        assert len(stages) == 3
        # Stage 1: samples from 60 to <240
        for s in stages[0]:
            assert 60 <= s.elapsed_s < 240

    def test_no_rest_period(self):
        # rest_start=0, stage=180, rest=0 => cycle=180
        samples = [ParsedSample(elapsed_s=t) for t in range(0, 540, 30)]
        stages = _detect_stages_running(samples, 0, 180, 0)
        assert len(stages) == 3

    def test_empty(self):
        assert _detect_stages_running([], 60, 180, 60) == []


class TestAverageStage:
    """Tests for per-stage averaging."""

    def test_full_stage_average(self):
        samples = [
            ParsedSample(elapsed_s=0, vo2_l_min=2.0, hr_bpm=130),
            ParsedSample(elapsed_s=30, vo2_l_min=2.5, hr_bpm=140),
            ParsedSample(elapsed_s=60, vo2_l_min=3.0, hr_bpm=150),
        ]
        avg = _average_stage(samples, 1, "full_stage", 30, intensity_value=100.0)
        assert avg.avg_vo2_l_min == pytest.approx(2.5, abs=0.01)
        assert avg.avg_hr_bpm == pytest.approx(140.0, abs=0.1)
        assert avg.intensity_value == 100.0
        assert avg.data_point_count == 3

    def test_last_60s_averaging(self):
        samples = [
            ParsedSample(elapsed_s=0, vo2_l_min=1.0),
            ParsedSample(elapsed_s=30, vo2_l_min=1.5),
            ParsedSample(elapsed_s=60, vo2_l_min=2.0),
            ParsedSample(elapsed_s=90, vo2_l_min=2.5),
            ParsedSample(elapsed_s=120, vo2_l_min=3.0),
            ParsedSample(elapsed_s=150, vo2_l_min=3.5),
        ]
        avg = _average_stage(samples, 1, "last_60s", 30)
        # Last 60s: samples at 120, 150 (elapsed > 90)
        assert avg.avg_vo2_l_min == pytest.approx(3.25, abs=0.01)

    def test_empty_stage(self):
        avg = _average_stage([], 1, "full_stage", 30)
        assert avg.data_point_count == 0
        assert avg.avg_vo2_l_min is None


class TestParseCpetFile:
    """Integration tests for full file parsing."""

    def _make_csv_bytes(self, rows: list[list[str]]) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode("utf-8")

    def test_cycling_csv(self):
        csv_data = self._make_csv_bytes([
            ["t", "V'O2", "HR", "FAT", "CHO", "Work Rate (W)"],
            ["60", "2.0", "130", "20.0", "30.0", "80"],
            ["90", "2.1", "132", "21.0", "31.0", "80"],
            ["120", "2.2", "135", "22.0", "32.0", "80"],
            ["150", "2.5", "145", "18.0", "40.0", "120"],
            ["180", "2.6", "148", "17.0", "42.0", "120"],
            ["210", "2.7", "150", "16.0", "44.0", "120"],
            ["240", "3.0", "160", "12.0", "55.0", "160"],
            ["270", "3.1", "162", "11.0", "57.0", "160"],
            ["300", "3.2", "165", "10.0", "60.0", "160"],
        ])
        result = parse_cpet_file(csv_data, "test.csv", "cycling")
        assert result.interval_seconds == 30
        assert len(result.stage_averages) == 3
        assert result.stage_averages[0].intensity_value == 80
        assert result.stage_averages[1].intensity_value == 120
        assert result.stage_averages[2].intensity_value == 160
        assert result.stage_averages[0].avg_fat_gh is not None

    def test_running_csv_with_intensities(self):
        # rest_start=0, stage=90, rest=0 for simple test
        rows = [["t", "V'O2", "HR"]]
        for i in range(9):
            rows.append([str(i * 30), str(2.0 + i * 0.1), str(130 + i * 2)])
        csv_data = self._make_csv_bytes(rows)
        result = parse_cpet_file(
            csv_data, "test.csv", "running",
            stage_intensities=[10.0, 12.0, 14.0],
            rest_start_seconds=0,
            stage_duration_seconds=90,
            rest_duration_seconds=0,
        )
        assert len(result.stage_averages) >= 2
        assert result.stage_averages[0].intensity_value == 10.0

    def test_unsupported_file_type(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_cpet_file(b"data", "test.xml", "cycling")

    def test_empty_file(self):
        with pytest.raises(ValueError, match="empty"):
            parse_cpet_file(b"", "test.csv", "cycling")

    def test_no_header(self):
        csv_data = self._make_csv_bytes([["speed", "power"], ["10", "200"]])
        with pytest.raises(ValueError, match="header"):
            parse_cpet_file(csv_data, "test.csv", "cycling")
