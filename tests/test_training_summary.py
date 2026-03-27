"""
Unit tests for the get_training_summary tool.
"""

import asyncio
import json
import os
import pathlib
import sys
from datetime import datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server import get_training_summary  # noqa: E402
from intervals_mcp_server.tools.training_summary import (  # noqa: E402
    _build_by_sport,
    _build_period_totals,
    _build_planned_summary,
    _compute_weekly_compliance,
    _compute_weekly_wellness,
    _group_events_by_week,
    _round1,
    _round2,
)
from intervals_mcp_server.utils.formatting import set_if, strip_nulls  # noqa: E402


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

SAMPLE_SUMMARY_WEEKS = [
    # API returns reverse-chronological; tests pass pre-reversed (chronological)
    {
        "date": "2026-02-16",
        "count": 4,
        "fitness": 52.1,
        "fatigue": 48.3,
        "form": 3.8,
        "rampRate": None,
        "training_load": 380,
        "srpe": 1100,
        "time": 18000,
        "distance": 70000,
        "total_elevation_gain": 800,
        "byCategory": [
            {
                "category": "Ride",
                "count": 3,
                "training_load": 310,
                "time": 14400,
                "distance": 65000,
                "total_elevation_gain": 750,
                "eftp": None,
                "eftpPerKg": None,
            },
            {
                "category": "Run",
                "count": 1,
                "training_load": 70,
                "time": 3600,
                "distance": 5000,
                "total_elevation_gain": 50,
                "eftp": None,
                "eftpPerKg": None,
            },
        ],
    },
    {
        "date": "2026-02-23",
        "count": 5,
        "fitness": 54.2,
        "fatigue": 58.1,
        "form": -3.9,
        "rampRate": 1.2,
        "training_load": 420,
        "srpe": 1240,
        "time": 21600,
        "distance": 86000,
        "total_elevation_gain": 1000,
        "byCategory": [
            {
                "category": "Ride",
                "count": 3,
                "training_load": 310,
                "time": 14400,
                "distance": 72000,
                "total_elevation_gain": 900,
                "eftp": 255.0,
                "eftpPerKg": 2.88,
            },
            {
                "category": "Run",
                "count": 2,
                "training_load": 110,
                "time": 7200,
                "distance": 14000,
                "total_elevation_gain": 100,
                "eftp": None,
                "eftpPerKg": None,
            },
        ],
    },
    {
        "date": "2026-03-16",
        "count": 2,
        "fitness": 61.4,
        "fatigue": 74.2,
        "form": -12.8,
        "rampRate": 1.9,
        "training_load": 78,
        "srpe": 152,
        "time": 5774,
        "distance": 30000,
        "total_elevation_gain": 200,
        "byCategory": [
            {
                "category": "Ride",
                "count": 1,
                "training_load": 24,
                "time": 2734,
                "distance": 23000,
                "total_elevation_gain": 150,
                "eftp": 260.5,
                "eftpPerKg": 2.94,
            },
            {
                "category": "Workout",
                "count": 1,
                "training_load": 0,
                "time": 3040,
                "distance": 0,
                "total_elevation_gain": 0,
                "eftp": None,
                "eftpPerKg": None,
            },
        ],
    },
]


SAMPLE_ACTIVITIES = [
    {
        "start_date_local": "2026-02-17T08:00:00",
        "compliance": 92,
    },
    {
        "start_date_local": "2026-02-18T08:00:00",
        "compliance": 80,
    },
    {
        "start_date_local": "2026-02-23T08:00:00",
        "compliance": None,  # no linked workout
    },
    {
        "start_date_local": "2026-03-16T08:00:00",
        "compliance": 95,
    },
]


SAMPLE_WELLNESS = [
    {"id": "2026-02-16", "hrvRMSSD": 55, "restingHR": 44, "sleepSecs": 27000, "fatigue": 3, "mood": 4},
    {"id": "2026-02-17", "hrvRMSSD": 57, "restingHR": 46, "sleepSecs": 28800, "fatigue": 4, "mood": 4},
    {"id": "2026-02-23", "hrvRMSSD": 50, "restingHR": 48, "sleepSecs": 25200, "fatigue": 5, "mood": 3},
    {"id": "2026-03-16", "hrvRMSSD": 49, "restingHR": 49, "sleepSecs": 24480, "fatigue": 6, "mood": 3},
]


SAMPLE_EVENTS = [
    {
        "id": "e1",
        "start_date_local": "2026-02-17T00:00:00",
        "type": "Ride",
        "category": "WORKOUT",
        "name": "Endurance Ride",
        "icu_training_load": 120,
        "moving_time": 5400,
        "distance": 40000,
    },
    {
        "id": "e2",
        "start_date_local": "2026-02-19T00:00:00",
        "type": "Run",
        "category": "WORKOUT",
        "name": "Easy Run",
        "icu_training_load": 60,
        "moving_time": 3600,
        "distance": 10000,
    },
    {
        "id": "e3",
        "start_date_local": "2026-02-24T00:00:00",
        "type": "Ride",
        "category": "WORKOUT",
        "name": "Sweet Spot",
        "icu_training_load": 150,
        "moving_time": 4800,
        "distance": 35000,
    },
    {
        "id": "e4",
        "start_date_local": "2026-03-16T00:00:00",
        "type": "Ride",
        "category": "WORKOUT",
        "name": "VO2max Intervals",
        "icu_training_load": 90,
        "moving_time": 3600,
        "distance": 25000,
    },
]


# ---------------------------------------------------------------------------
# Helper unit tests
# ---------------------------------------------------------------------------


def test_round1_basic():
    assert _round1(3.456) == 3.5
    assert _round1(0) == 0.0
    assert _round1(None) is None
    assert _round1("abc") is None


def test_round2_basic():
    assert _round2(1.215) == 1.22
    assert _round2(None) is None


def test_strip_nulls_removes_none_and_empty():
    d = {"a": 1, "b": None, "c": [], "d": {}, "e": 0, "f": "hello"}
    result = strip_nulls(d)
    assert result == {"a": 1, "e": 0, "f": "hello"}


def test_strip_nulls_preserves_zeros():
    d = {"tss": 0, "count": 0, "other": None}
    result = strip_nulls(d)
    assert result == {"tss": 0, "count": 0}


def test_set_if_sets_when_not_none():
    d: dict = {}
    set_if(d, "a", 42)
    assert d == {"a": 42}


def test_set_if_skips_none():
    d: dict = {}
    set_if(d, "a", None)
    assert d == {}


def test_set_if_positive_sets_when_positive():
    d: dict = {}
    set_if(d, "x", 5, positive=True)
    assert d == {"x": 5}


def test_set_if_positive_skips_zero():
    d: dict = {}
    set_if(d, "x", 0, positive=True)
    assert d == {}


def test_set_if_positive_skips_negative():
    d: dict = {}
    set_if(d, "x", -1, positive=True)
    assert d == {}


def test_set_if_with_transform():
    d: dict = {}
    set_if(d, "val", 3.456, transform=lambda v: round(v, 1))
    assert d == {"val": 3.5}


def test_set_if_transform_returning_none_skips():
    d: dict = {}
    set_if(d, "val", "bad", transform=lambda v: None)
    assert d == {}


def test_set_if_preserves_zero_without_positive_flag():
    d: dict = {}
    set_if(d, "count", 0)
    assert d == {"count": 0}


def test_set_if_with_string_value():
    d: dict = {}
    set_if(d, "name", "Ride")
    assert d == {"name": "Ride"}


def test_build_by_sport_zero_tss_preserved():
    """tss: 0 in by_sport entries must always be included, never omitted."""
    categories = [
        {"category": "Workout", "count": 1, "training_load": 0, "time": 3000, "distance": 0},
    ]
    by_sport = _build_by_sport(categories)
    assert "Workout" in by_sport
    assert by_sport["Workout"]["tss"] == 0.0


def test_build_by_sport_includes_eftp():
    categories = [
        {
            "category": "Ride",
            "count": 1,
            "training_load": 100,
            "time": 3600,
            "distance": 30000,
            "total_elevation_gain": 200,
            "eftp": 260.5,
            "eftpPerKg": 2.94,
        },
    ]
    by_sport = _build_by_sport(categories)
    assert by_sport["Ride"]["eftp_w"] == 260.5
    assert by_sport["Ride"]["eftp_w_kg"] == 2.9


def test_build_by_sport_no_eftp_when_null():
    categories = [
        {
            "category": "Run",
            "count": 2,
            "training_load": 80,
            "time": 7200,
            "distance": 14000,
            "eftp": None,
            "eftpPerKg": None,
        },
    ]
    by_sport = _build_by_sport(categories)
    assert "eftp_w" not in by_sport["Run"]
    assert "eftp_w_kg" not in by_sport["Run"]


def test_compute_weekly_compliance():
    """Average compliance across activities with non-null compliance."""
    compliance = _compute_weekly_compliance(SAMPLE_ACTIVITIES, "2026-02-16", "2026-02-22")
    assert compliance == 86  # (92 + 80) / 2 = 86


def test_compute_weekly_compliance_none_when_no_linked():
    """Weeks where no activities have compliance should return None."""
    compliance = _compute_weekly_compliance(SAMPLE_ACTIVITIES, "2026-02-23", "2026-03-01")
    assert compliance is None


def test_compute_weekly_wellness():
    wellness = _compute_weekly_wellness(SAMPLE_WELLNESS, "2026-02-16", "2026-02-22")
    # Two entries: 2026-02-16 and 2026-02-17
    assert wellness["hrv"] == 56.0  # (55+57)/2
    assert wellness["resting_hr_bpm"] == 45.0  # (44+46)/2
    assert wellness["sleep_hrs"] == 7.8  # (27000+28800)/2/3600 = 7.75 → 7.8
    assert wellness["fatigue"] == 3.5  # (3+4)/2
    assert wellness["mood"] == 4.0


def test_compute_weekly_wellness_empty():
    result = _compute_weekly_wellness([], "2026-02-16", "2026-02-22")
    assert result == {}


def test_build_period_totals():
    totals = _build_period_totals(SAMPLE_SUMMARY_WEEKS)
    assert totals["sessions"] == 11  # 4+5+2
    assert totals["duration_secs"] == 45374  # 18000+21600+5774
    assert totals["tss"] == 878.0  # 380+420+78
    assert "by_sport" in totals
    assert totals["by_sport"]["Ride"]["count"] == 7
    assert totals["by_sport"]["Workout"]["tss"] == 0.0  # zero TSS preserved
    assert "planned_totals" not in totals


# ---------------------------------------------------------------------------
# Integration-level test (mocking API calls)
# ---------------------------------------------------------------------------


def _make_fake_request(summary_response, activities_response, wellness_response,
                       events_response=None):
    """Create a fake make_intervals_request that routes based on URL."""
    if events_response is None:
        events_response = []

    async def fake_request(url="", **kwargs):
        if "athlete-summary" in url:
            return summary_response
        if "activities" in url:
            return activities_response
        if "wellness" in url:
            return wellness_response
        if "events" in url:
            return events_response
        return {"error": True, "message": "unexpected URL"}
    return fake_request


def test_get_training_summary_integration(monkeypatch):
    """Full integration test with mocked API calls."""
    # API returns reverse-chronological
    reversed_weeks = list(reversed(SAMPLE_SUMMARY_WEEKS))
    fake = _make_fake_request(reversed_weeks, SAMPLE_ACTIVITIES, SAMPLE_WELLNESS,
                              SAMPLE_EVENTS)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(
            start_date="2026-02-15",
            end_date="2026-03-17",
            athlete_id="i1",
        )
    )
    result = json.loads(result_str)

    # Period
    assert result["period"]["start"] == "2026-02-15"
    assert result["period"]["end"] == "2026-03-17"

    # Load - start from oldest week
    assert result["load"]["start"]["ctl"] == 52.1
    assert result["load"]["end"]["ctl"] == 61.4
    assert "ac_ratio" in result["load"]

    # Period totals
    assert result["period_totals"]["sessions"] == 11
    assert "planned_totals" not in result["period_totals"]

    # Weeks structure: completed data is nested under 'completed'
    assert len(result["weeks"]) == 3
    assert result["weeks"][0]["week_start"] == "2026-02-16"
    assert result["weeks"][-1]["week_start"] == "2026-03-16"

    # Past weeks have 'completed' section
    week0 = result["weeks"][0]
    assert "completed" in week0
    assert week0["completed"]["sessions"] == 4

    # Past weeks with events have 'planned' section
    assert "planned" in week0
    assert week0["planned"]["sessions"] == 2  # e1 + e2

    # Compliance is under completed
    assert "compliance_pct" in week0["completed"]

    # Load metrics at week top level
    assert "ctl" in week0


def test_get_training_summary_compact_json(monkeypatch):
    """Output should be compact JSON with no whitespace."""
    reversed_weeks = list(reversed(SAMPLE_SUMMARY_WEEKS))
    fake = _make_fake_request(reversed_weeks, [], [])

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-03-17", athlete_id="i1")
    )
    # Compact JSON should have no spaces after : or ,
    assert " : " not in result_str
    # Verify it's valid JSON
    json.loads(result_str)


def test_get_training_summary_partial_week(monkeypatch):
    """A week that straddles today should be marked partial."""
    # Use today's date offset so that the week starts before today and ends after
    today = datetime.now()
    # Shift back 2 days so the 7-day week straddles today
    week_start = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    partial_week = {
        "date": week_start,
        "count": 1,
        "fitness": 50.0,
        "fatigue": 50.0,
        "form": 0.0,
        "rampRate": None,
        "training_load": 50,
        "srpe": 100,
        "time": 3600,
        "distance": 10000,
        "total_elevation_gain": 0,
        "byCategory": [],
    }
    fake = _make_fake_request([partial_week], [], [])

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-01-01", end_date="2027-01-01", athlete_id="i1")
    )
    result = json.loads(result_str)
    assert result["weeks"][0]["partial"] is True


def test_get_training_summary_default_dates(monkeypatch):
    """When dates are omitted, should default to 30 days back and 30 days forward."""
    from datetime import datetime, timedelta

    fake = _make_fake_request([], [], [])
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    now = datetime.now()
    result_str = asyncio.run(
        get_training_summary(athlete_id="i1")
    )
    result = json.loads(result_str)

    expected_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    expected_end = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    assert result["period"]["start"] == expected_start
    assert result["period"]["end"] == expected_end


def test_get_training_summary_error_no_athlete(monkeypatch):
    """Should return error when no athlete ID is available."""
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.config",
                        type("C", (), {"athlete_id": ""})())

    result = asyncio.run(
        get_training_summary(start_date="2026-01-01", end_date="2026-02-01")
    )
    assert "Error" in result


def test_get_training_summary_invalid_date(monkeypatch):
    """Should return error for invalid date format."""
    result = asyncio.run(
        get_training_summary(start_date="not-a-date", end_date="2026-02-01", athlete_id="i1")
    )
    assert "Error" in result


def test_get_training_summary_api_error(monkeypatch):
    """Should return error message when API returns an error."""
    async def fake_error(*args, **kwargs):
        return {"error": True, "message": "Unauthorized"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_error)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake_error)

    result = asyncio.run(
        get_training_summary(start_date="2026-01-01", end_date="2026-02-01", athlete_id="i1")
    )
    assert "Error" in result
    assert "Unauthorized" in result


def test_get_training_summary_empty_response(monkeypatch):
    """Should handle empty API responses gracefully."""
    fake = _make_fake_request([], [], [])

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-01-01", end_date="2026-02-01", athlete_id="i1")
    )
    result = json.loads(result_str)
    assert result["period"]["start"] == "2026-01-01"


# ---------------------------------------------------------------------------
# New helper tests
# ---------------------------------------------------------------------------


def test_build_planned_summary_basic():
    """Planned summary should aggregate event fields."""
    events = [
        {"type": "Ride", "icu_training_load": 100, "moving_time": 3600, "distance": 30000},
        {"type": "Ride", "icu_training_load": 80, "moving_time": 2700, "distance": 20000},
        {"type": "Run", "icu_training_load": 60, "moving_time": 3000, "distance": 8000},
    ]
    result = _build_planned_summary(events)
    assert result["sessions"] == 3
    assert result["tss"] == 240.0
    assert result["duration_secs"] == 9300
    assert result["distance_m"] == 58000.0
    assert result["by_sport"]["Ride"]["count"] == 2
    assert result["by_sport"]["Run"]["count"] == 1


def test_build_planned_summary_missing_fields():
    """Events with missing optional fields should still aggregate."""
    events = [
        {"type": "Ride", "icu_training_load": 50, "moving_time": 1800},
        {"type": "Ride"},
    ]
    result = _build_planned_summary(events)
    assert result["sessions"] == 2
    assert result["tss"] == 50.0
    assert result["duration_secs"] == 1800
    assert "distance_m" not in result


def test_build_planned_summary_empty():
    """Empty events list should produce zero-value summary."""
    result = _build_planned_summary([])
    assert result["sessions"] == 0


def test_group_events_by_week():
    """Events should be grouped into the correct week buckets."""
    grouped = _group_events_by_week(SAMPLE_EVENTS, SAMPLE_SUMMARY_WEEKS)
    # e1 (Feb 17) and e2 (Feb 19) → week starting Feb 16
    assert len(grouped["2026-02-16"]) == 2
    # e3 (Feb 24) → week starting Feb 23
    assert len(grouped["2026-02-23"]) == 1
    # e4 (Mar 16) → week starting Mar 16
    assert len(grouped["2026-03-16"]) == 1


def test_group_events_by_week_no_events():
    """No events should produce empty lists for each week."""
    grouped = _group_events_by_week([], SAMPLE_SUMMARY_WEEKS)
    assert all(len(v) == 0 for v in grouped.values())


def test_future_week_has_no_completed(monkeypatch):
    """Future weeks should only have planned section, no completed."""
    from datetime import datetime, timedelta

    future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    future_week = {
        "date": future_date,
        "count": 0,
        "fitness": 65.0,
        "fatigue": 70.0,
        "form": -5.0,
        "rampRate": None,
        "training_load": 0,
        "srpe": 0,
        "time": 0,
        "distance": 0,
        "total_elevation_gain": 0,
        "byCategory": [],
    }
    future_events = [
        {
            "id": "e10",
            "start_date_local": f"{future_date}T00:00:00",
            "type": "Ride",
            "category": "WORKOUT",
            "name": "Future Ride",
            "icu_training_load": 100,
            "moving_time": 3600,
            "distance": 30000,
        },
    ]
    fake = _make_fake_request([future_week], [], [], future_events)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(
            start_date=future_date,
            end_date=(datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
            athlete_id="i1",
        )
    )
    result = json.loads(result_str)
    week = result["weeks"][0]

    # Future week should have planned but no completed
    assert "planned" in week
    assert week["planned"]["sessions"] == 1
    assert "completed" not in week
    # Should still have projected load metrics
    assert week["ctl"] == 65.0
    # Should not have partial flag (it's fully in the future)
    assert "partial" not in week


def test_past_week_has_planned_and_completed(monkeypatch):
    """Past weeks should have both planned and completed sections."""
    reversed_weeks = list(reversed(SAMPLE_SUMMARY_WEEKS))
    fake = _make_fake_request(reversed_weeks, SAMPLE_ACTIVITIES, SAMPLE_WELLNESS,
                              SAMPLE_EVENTS)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(
            start_date="2026-02-15",
            end_date="2026-03-17",
            athlete_id="i1",
        )
    )
    result = json.loads(result_str)

    # First week (Feb 16) should have both planned and completed
    week0 = result["weeks"][0]
    assert "planned" in week0
    assert "completed" in week0

    # Planned: e1 (Ride, TL=120) + e2 (Run, TL=60)
    assert week0["planned"]["sessions"] == 2
    assert week0["planned"]["tss"] == 180.0

    # Completed from athlete-summary
    assert week0["completed"]["sessions"] == 4
    assert week0["completed"]["tss"] == 380.0

    # Compliance is under completed
    assert "compliance_pct" in week0["completed"]
    assert week0["completed"]["compliance_pct"] == 86

    # by_sport under completed
    assert "by_sport" in week0["completed"]

    # Wellness at top level
    assert "wellness" in week0

    # Load at top level
    assert "ctl" in week0
    assert "atl" in week0


def test_get_training_summary_zero_tss_sport(monkeypatch):
    """Zero-TSS sports like Workout must always include tss: 0."""
    week_with_zero_tss = {
        "date": "2026-01-06",
        "count": 1,
        "fitness": 50.0,
        "fatigue": 50.0,
        "form": 0.0,
        "rampRate": None,
        "training_load": 0,
        "srpe": 200,
        "time": 3000,
        "distance": 0,
        "total_elevation_gain": 0,
        "byCategory": [
            {"category": "Workout", "count": 1, "training_load": 0, "time": 3000,
             "distance": 0, "total_elevation_gain": 0, "eftp": None, "eftpPerKg": None},
        ],
    }
    fake = _make_fake_request([week_with_zero_tss], [], [])

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-01-01", end_date="2026-01-12", athlete_id="i1")
    )
    result = json.loads(result_str)

    # Check period_totals by_sport
    assert result["period_totals"]["by_sport"]["Workout"]["tss"] == 0.0

    # Check week-level by_sport (now under completed)
    assert result["weeks"][0]["completed"]["by_sport"]["Workout"]["tss"] == 0.0


def test_get_training_summary_concurrent_calls(monkeypatch):
    """Verify that four API calls are made (we track call URLs)."""
    call_urls = []

    async def tracking_request(url="", **kwargs):
        call_urls.append(url)
        if "athlete-summary" in url:
            return []
        if "activities" in url:
            return []
        if "wellness" in url:
            return []
        if "events" in url:
            return []
        return {"error": True, "message": "unexpected"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", tracking_request)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", tracking_request)

    asyncio.run(
        get_training_summary(start_date="2026-01-01", end_date="2026-02-01", athlete_id="i1")
    )

    assert len(call_urls) == 4
    assert any("athlete-summary" in u for u in call_urls)
    assert any("activities" in u for u in call_urls)
    assert any("wellness" in u for u in call_urls)
    assert any("events" in u for u in call_urls)


def test_get_training_summary_ac_ratio(monkeypatch):
    """ac_ratio should be end ATL / end CTL, rounded to 2 d.p."""
    reversed_weeks = list(reversed(SAMPLE_SUMMARY_WEEKS))
    fake = _make_fake_request(reversed_weeks, [], [])

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-03-17", athlete_id="i1")
    )
    result = json.loads(result_str)
    expected_ac = round(74.2 / 61.4, 2)
    assert result["load"]["ac_ratio"] == expected_ac


def test_get_training_summary_wellness_in_weeks(monkeypatch):
    """Wellness metrics should be averaged per calendar week."""
    reversed_weeks = list(reversed(SAMPLE_SUMMARY_WEEKS))
    fake = _make_fake_request(reversed_weeks, SAMPLE_ACTIVITIES, SAMPLE_WELLNESS)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-03-17", athlete_id="i1")
    )
    result = json.loads(result_str)

    # First week (2026-02-16 to 2026-02-22) should have wellness data from 2 entries
    week0 = result["weeks"][0]
    assert "wellness" in week0
    assert week0["wellness"]["hrv"] == 56.0


def test_get_training_summary_compliance_in_weeks(monkeypatch):
    """Compliance should be computed per week under the completed section."""
    reversed_weeks = list(reversed(SAMPLE_SUMMARY_WEEKS))
    fake = _make_fake_request(reversed_weeks, SAMPLE_ACTIVITIES, SAMPLE_WELLNESS)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-03-17", athlete_id="i1")
    )
    result = json.loads(result_str)

    # First week should have compliance under completed
    week0 = result["weeks"][0]
    assert week0["completed"].get("compliance_pct") == 86  # (92+80)/2

    # Second week (2026-02-23) has only null compliance → should be omitted
    week1 = result["weeks"][1]
    assert "compliance_pct" not in week1["completed"]


def test_build_planned_summary_excludes_holiday_and_note():
    """HOLIDAY and NOTE events should not count as training sessions."""
    events = [
        {"type": "Ride", "category": "WORKOUT", "icu_training_load": 100, "moving_time": 3600},
        {"category": "HOLIDAY", "name": "Bank Holiday"},
        {"category": "NOTE", "name": "Recovery week"},
    ]
    result = _build_planned_summary(events)
    assert result["sessions"] == 1
    assert result["tss"] == 100.0
    assert "HOLIDAY" not in result.get("by_sport", {})
    assert "NOTE" not in result.get("by_sport", {})


def test_build_planned_summary_only_non_training():
    """If a week has only HOLIDAY/NOTE events, planned summary has zero sessions."""
    events = [
        {"category": "HOLIDAY", "name": "Vacation"},
        {"category": "NOTE", "name": "Deload"},
    ]
    result = _build_planned_summary(events)
    assert result["sessions"] == 0


def test_week_with_holiday_dates(monkeypatch):
    """A week containing HOLIDAY events should list their dates."""
    week_data = {
        "date": "2026-02-16",
        "count": 2, "fitness": 50.0, "fatigue": 50.0, "form": 0.0,
        "rampRate": None, "training_load": 100, "srpe": 200,
        "time": 7200, "distance": 30000, "total_elevation_gain": 0,
        "byCategory": [],
    }
    events_with_holiday = [
        {
            "id": "e1", "start_date_local": "2026-02-17T00:00:00",
            "type": "Ride", "category": "WORKOUT",
            "icu_training_load": 100, "moving_time": 3600,
        },
        {
            "id": "e_hol", "start_date_local": "2026-02-18T00:00:00",
            "category": "HOLIDAY", "name": "Bank Holiday",
        },
    ]
    fake = _make_fake_request([week_data], [], [], events_with_holiday)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-02-23", athlete_id="i1")
    )
    result = json.loads(result_str)
    week = result["weeks"][0]
    assert week["holiday"] == ["2026-02-18"]
    # Planned should only count the Ride, not the holiday
    assert week["planned"]["sessions"] == 1


def test_week_with_note(monkeypatch):
    """A week containing a NOTE event should have the note text attached."""
    week_data = {
        "date": "2026-02-16",
        "count": 1, "fitness": 50.0, "fatigue": 50.0, "form": 0.0,
        "rampRate": None, "training_load": 80, "srpe": 150,
        "time": 3600, "distance": 20000, "total_elevation_gain": 0,
        "byCategory": [],
    }
    events_with_note = [
        {
            "id": "e1", "start_date_local": "2026-02-17T00:00:00",
            "type": "Ride", "category": "WORKOUT",
            "icu_training_load": 80, "moving_time": 3600,
        },
        {
            "id": "e_note", "start_date_local": "2026-02-19T00:00:00",
            "category": "NOTE", "name": "Start of build phase",
        },
    ]
    fake = _make_fake_request([week_data], [], [], events_with_note)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-02-23", athlete_id="i1")
    )
    result = json.loads(result_str)
    week = result["weeks"][0]
    assert "notes" in week
    assert "Start of build phase" in week["notes"]
    # Should not have holiday flag
    assert "holiday" not in week


def test_week_with_multiple_notes(monkeypatch):
    """Multiple NOTE events in one week should all appear in the notes list."""
    week_data = {
        "date": "2026-02-16",
        "count": 0, "fitness": 50.0, "fatigue": 50.0, "form": 0.0,
        "rampRate": None, "training_load": 0, "srpe": 0,
        "time": 0, "distance": 0, "total_elevation_gain": 0,
        "byCategory": [],
    }
    events_with_notes = [
        {
            "id": "n1", "start_date_local": "2026-02-16T00:00:00",
            "category": "NOTE", "name": "Recovery week",
        },
        {
            "id": "n2", "start_date_local": "2026-02-18T00:00:00",
            "category": "NOTE", "name": "Focus on mobility",
        },
    ]
    fake = _make_fake_request([week_data], [], [], events_with_notes)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-02-23", athlete_id="i1")
    )
    result = json.loads(result_str)
    week = result["weeks"][0]
    assert len(week["notes"]) == 2
    assert "Recovery week" in week["notes"]
    assert "Focus on mobility" in week["notes"]
    # No planned section since only notes exist
    assert "planned" not in week


def test_holiday_spanning_two_weeks(monkeypatch):
    """A holiday spanning two weeks should add dates to each week independently."""
    week1 = {
        "date": "2026-02-16",
        "count": 0, "fitness": 50.0, "fatigue": 50.0, "form": 0.0,
        "rampRate": None, "training_load": 0, "srpe": 0,
        "time": 0, "distance": 0, "total_elevation_gain": 0,
        "byCategory": [],
    }
    week2 = {
        "date": "2026-02-23",
        "count": 0, "fitness": 48.0, "fatigue": 40.0, "form": 8.0,
        "rampRate": None, "training_load": 0, "srpe": 0,
        "time": 0, "distance": 0, "total_elevation_gain": 0,
        "byCategory": [],
    }
    # Holiday events spanning Thu-Wed across two weeks
    holiday_events = [
        {"id": "h1", "start_date_local": "2026-02-19T00:00:00", "category": "HOLIDAY", "name": "Vacation"},
        {"id": "h2", "start_date_local": "2026-02-20T00:00:00", "category": "HOLIDAY", "name": "Vacation"},
        {"id": "h3", "start_date_local": "2026-02-21T00:00:00", "category": "HOLIDAY", "name": "Vacation"},
        {"id": "h4", "start_date_local": "2026-02-22T00:00:00", "category": "HOLIDAY", "name": "Vacation"},
        {"id": "h5", "start_date_local": "2026-02-23T00:00:00", "category": "HOLIDAY", "name": "Vacation"},
        {"id": "h6", "start_date_local": "2026-02-24T00:00:00", "category": "HOLIDAY", "name": "Vacation"},
        {"id": "h7", "start_date_local": "2026-02-25T00:00:00", "category": "HOLIDAY", "name": "Vacation"},
    ]
    # API returns reverse-chronological
    fake = _make_fake_request([week2, week1], [], [], holiday_events)

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.training_summary.make_intervals_request", fake)

    result_str = asyncio.run(
        get_training_summary(start_date="2026-02-15", end_date="2026-03-01", athlete_id="i1")
    )
    result = json.loads(result_str)

    # Week 1 (Feb 16-22): 4 holiday days
    w1 = result["weeks"][0]
    assert w1["holiday"] == ["2026-02-19", "2026-02-20", "2026-02-21", "2026-02-22"]

    # Week 2 (Feb 23-Mar 1): 3 holiday days
    w2 = result["weeks"][1]
    assert w2["holiday"] == ["2026-02-23", "2026-02-24", "2026-02-25"]

    # Neither week should have a planned section
    assert "planned" not in w1
    assert "planned" not in w2
