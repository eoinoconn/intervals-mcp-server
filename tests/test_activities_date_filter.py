"""
Unit tests for activity date filtering in intervals_mcp_server.tools.activities.
"""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.tools.activities import _filter_activities_by_date
from intervals_mcp_server.server import get_activities


def test_filter_activities_by_date_includes_matching():
    activities = [
        {"name": "Ride", "startTime": "2024-03-15T08:00:00Z"},
        {"name": "Run", "startTime": "2024-03-16T07:00:00Z"},
    ]
    result = _filter_activities_by_date(activities, "2024-03-15", "2024-03-16")
    assert len(result) == 2


def test_filter_activities_by_date_excludes_outside_range():
    activities = [
        {"name": "Ride", "startTime": "2024-03-10T08:00:00Z"},
        {"name": "Run", "startTime": "2024-03-15T07:00:00Z"},
        {"name": "Swim", "startTime": "2024-03-20T06:00:00Z"},
    ]
    result = _filter_activities_by_date(activities, "2024-03-14", "2024-03-16")
    assert len(result) == 1
    assert result[0]["name"] == "Run"


def test_filter_activities_by_date_single_day():
    activities = [
        {"name": "Ride", "startTime": "2024-04-01T08:00:00Z"},
        {"name": "Run", "startTime": "2024-04-02T07:00:00Z"},
        {"name": "Swim", "startTime": "2024-04-03T06:00:00Z"},
    ]
    result = _filter_activities_by_date(activities, "2024-04-02", "2024-04-02")
    assert len(result) == 1
    assert result[0]["name"] == "Run"


def test_filter_activities_by_date_uses_start_date_local():
    activities = [
        {"name": "Ride", "start_date_local": "2024-05-01T08:00:00"},
        {"name": "Run", "start_date_local": "2024-05-05T07:00:00"},
    ]
    result = _filter_activities_by_date(activities, "2024-05-01", "2024-05-03")
    assert len(result) == 1
    assert result[0]["name"] == "Ride"


def test_filter_activities_by_date_skips_no_date():
    activities = [
        {"name": "Ride"},
        {"name": "Run", "startTime": "2024-03-15T07:00:00Z"},
    ]
    result = _filter_activities_by_date(activities, "2024-03-01", "2024-03-31")
    assert len(result) == 1
    assert result[0]["name"] == "Run"


def test_get_activities_filters_by_date(monkeypatch):
    """End-to-end: only activities within the requested dates are returned."""
    sample_activities = [
        {"name": "In Range", "id": 1, "type": "Ride", "startTime": "2024-06-15T08:00:00Z", "distance": 100, "duration": 60},
        {"name": "Out of Range", "id": 2, "type": "Run", "startTime": "2024-06-10T07:00:00Z", "distance": 50, "duration": 30},
    ]

    async def fake_request(*_args, **_kwargs):
        return sample_activities

    monkeypatch.setattr("intervals_mcp_server.tools.activities.make_intervals_request", fake_request)

    result = asyncio.run(
        get_activities(athlete_id="1", start_date="2024-06-14", end_date="2024-06-16", limit=10, include_unnamed=True)
    )
    assert "In Range" in result
    assert "Out of Range" not in result


def test_get_activities_no_results_when_all_outside_range(monkeypatch):
    """When all API results are outside the date range, return 'no activities' message."""
    sample_activities = [
        {"name": "Old Ride", "id": 1, "type": "Ride", "startTime": "2024-01-01T08:00:00Z", "distance": 100, "duration": 60},
    ]

    async def fake_request(*_args, **_kwargs):
        return sample_activities

    monkeypatch.setattr("intervals_mcp_server.tools.activities.make_intervals_request", fake_request)

    result = asyncio.run(
        get_activities(athlete_id="1", start_date="2024-06-01", end_date="2024-06-30", limit=10, include_unnamed=True)
    )
    assert "No" in result and "activities" in result.lower()
