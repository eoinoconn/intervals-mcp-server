"""
Unit tests for formatting utilities in intervals_mcp_server.utils.formatting.

These tests verify that the formatting functions produce expected output strings for activities, workouts, wellness entries, events, and intervals.
"""

import json
from intervals_mcp_server.utils.formatting import (
    format_activity_compact,
    format_activity_summary,
    format_workout,
    format_wellness_entry,
    format_event_summary,
    format_event_details,
    format_intervals,
)
from tests.sample_data import INTERVALS_DATA


def test_format_activity_summary():
    """
    Test that format_activity_summary returns a string containing the activity name and ID.
    """
    data = {
        "name": "Morning Ride",
        "id": 1,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }
    result = format_activity_summary(data)
    assert "Activity: Morning Ride" in result
    assert "ID: 1" in result


def test_format_activity_summary_omits_none_fields():
    """
    Test that format_activity_summary omits fields that have no data.
    """
    data = {
        "name": "Indoor Swim",
        "id": "s1",
        "type": "Swim",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 2000,
        "duration": 3600,
        "average_heartrate": 140,
        "max_heartrate": 165,
        # These should NOT appear in output since they are None/absent
        "icu_weighted_avg_watts": None,
        "average_temp": None,
        "power_meter": None,
    }
    result = format_activity_summary(data)
    assert "Activity: Indoor Swim" in result
    assert "Avg HR: 140 bpm" in result
    # None fields should be omitted entirely
    assert "Weighted" not in result
    assert "Temp" not in result
    assert "Power Meter" not in result
    assert "N/A" not in result


def test_format_activity_compact():
    """
    Test that format_activity_compact returns a concise single-line format.
    """
    data = {
        "name": "Evening Run",
        "id": "r1",
        "type": "Run",
        "startTime": "2024-03-15T18:00:00Z",
        "distance": 10000,
        "duration": 3000,
        "trainingLoad": 65,
        "average_heartrate": 155,
    }
    result = format_activity_compact(data)
    assert "Run: Evening Run" in result
    assert "10000m" in result
    assert "TL:65" in result
    assert "HR:155" in result
    # Should be a single line
    assert "\n" not in result


def test_format_workout():
    """
    Test that format_workout returns a string containing the workout name and interval count.
    """
    workout = {
        "name": "Workout1",
        "description": "desc",
        "sport": "Ride",
        "duration": 3600,
        "tss": 50,
        "intervals": [1, 2, 3],
    }
    result = format_workout(workout)
    assert "Workout: Workout1" in result
    assert "Intervals: 3" in result


def test_format_wellness_entry():
    """
    Test that format_wellness_entry returns a string containing the date and fitness (CTL).
    """
    with open("tests/ressources/wellness_entry.json", "r", encoding="utf-8") as f:
        entry = json.load(f)
    result = format_wellness_entry(entry)

    with open("tests/ressources/wellness_entry_formatted.txt", "r", encoding="utf-8") as f:
        expected_result = f.read()
    assert result == expected_result


def test_format_event_summary():
    """
    Test that format_event_summary returns a string containing the event date and type.
    """
    event = {
        "start_date_local": "2024-01-01",
        "id": "e1",
        "name": "Event1",
        "description": "desc",
        "race": True,
    }
    summary = format_event_summary(event)
    assert "Date: 2024-01-01" in summary
    assert "Type: Race" in summary


def test_format_event_details():
    """
    Test that format_event_details returns a string containing event and workout details.
    """
    event = {
        "id": "e1",
        "date": "2024-01-01",
        "name": "Event1",
        "description": "desc",
        "workout": {
            "id": "w1",
            "sport": "Ride",
            "duration": 3600,
            "tss": 50,
            "intervals": [1, 2],
        },
        "race": True,
        "priority": "A",
        "result": "1st",
        "calendar": {"name": "Main"},
    }
    details = format_event_details(event)
    assert "Event Details:" in details
    assert "Workout Information:" in details


def test_format_intervals():
    """
    Test that format_intervals returns a string containing interval analysis and the interval label.
    """
    result = format_intervals(INTERVALS_DATA)
    assert "Intervals Analysis:" in result
    assert "Rep 1" in result
