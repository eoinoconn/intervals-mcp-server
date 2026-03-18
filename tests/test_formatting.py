"""
Unit tests for formatting utilities in intervals_mcp_server.utils.formatting.

These tests verify that the formatting functions produce expected output strings for activities, workouts, wellness entries, events, and intervals.
"""

import json
from intervals_mcp_server.utils.formatting import (
    WELLNESS_FIELDS,
    format_activity_compact,
    format_activity_summary,
    format_workout,
    format_wellness_entry,
    format_event_summary,
    format_event_details,
    format_intervals,
    format_power_curves,
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


def test_format_activity_summary_with_compliance():
    """
    Test that format_activity_summary includes workout compliance when present.
    """
    data = {
        "name": "Threshold Intervals",
        "id": "a1",
        "type": "Ride",
        "startTime": "2024-06-01T07:00:00Z",
        "distance": 40000,
        "duration": 5400,
        "pairedEventId": 12345,
        "compliance": 0.85,
    }
    result = format_activity_summary(data)
    assert "Workout Compliance:" in result
    assert "Paired Event ID: 12345" in result
    assert "Compliance: 85%" in result


def test_format_activity_summary_omits_compliance_when_absent():
    """
    Test that format_activity_summary omits the compliance section when
    the activity has no paired workout.
    """
    data = {
        "name": "Easy Spin",
        "id": "a2",
        "type": "Ride",
        "startTime": "2024-06-02T08:00:00Z",
        "distance": 20000,
        "duration": 3600,
    }
    result = format_activity_summary(data)
    assert "Workout Compliance:" not in result
    assert "Paired Event ID" not in result
    assert "Compliance:" not in result


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


def test_format_wellness_entry_no_fields_matches_default():
    """Passing fields=None should produce the same output as the default."""
    with open("tests/ressources/wellness_entry.json", "r", encoding="utf-8") as f:
        entry = json.load(f)
    assert format_wellness_entry(entry) == format_wellness_entry(entry, fields=None)


def test_format_wellness_entry_single_field():
    """When a single field is requested, only that section appears."""
    entry = {
        "id": "2024-06-01",
        "ctl": 70,
        "atl": 90,
        "weight": 75,
        "sleepSecs": 28800,
        "soreness": 5,
        "steps": 10000,
    }
    result = format_wellness_entry(entry, fields={"vital_signs"})
    assert "Vital Signs:" in result
    assert "Weight: 75 kg" in result
    # Other sections should be absent
    assert "Training Metrics:" not in result
    assert "Sleep & Recovery:" not in result
    assert "Subjective Feelings:" not in result
    assert "Activity:" not in result


def test_format_wellness_entry_multiple_fields():
    """Multiple selected fields should all appear, others excluded."""
    entry = {
        "id": "2024-06-01",
        "ctl": 70,
        "atl": 90,
        "weight": 75,
        "sleepSecs": 28800,
        "soreness": 5,
        "steps": 10000,
    }
    result = format_wellness_entry(entry, fields={"training", "sleep"})
    assert "Training Metrics:" in result
    assert "Sleep & Recovery:" in result
    assert "Vital Signs:" not in result
    assert "Activity:" not in result


def test_wellness_fields_constant():
    """WELLNESS_FIELDS should contain the expected section names."""
    expected = {"training", "sport_info", "vital_signs", "sleep",
                "menstrual", "subjective", "nutrition", "activity"}
    assert WELLNESS_FIELDS == expected


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


def test_format_power_curves():
    """
    Test that format_power_curves returns a concise string with curve labels,
    power values, W/kg values, and activity IDs.
    """
    curves = [
        {
            "id": "s0",
            "label": "This season",
            "start": "2025-09-29T00:00:00",
            "end": "2026-03-14T00:00:00",
            "data_points": [
                {"secs": 5, "watts": 780, "activity_id": "i100", "watts_per_kg": 10.4, "wkg_activity_id": "i100"},
                {"secs": 60, "watts": 380, "activity_id": "i102", "watts_per_kg": 5.07, "wkg_activity_id": "i102"},
                {"secs": 3600, "watts": 210, "activity_id": "i107", "watts_per_kg": 2.8, "wkg_activity_id": "i107"},
            ],
        },
    ]
    result = format_power_curves(curves, "Ride", include_normalised=True)
    assert "Power Curves (Ride):" in result
    assert "This season" in result
    assert "5s: 780W" in result
    assert "10.40W/kg" in result
    assert "1m: 380W" in result
    assert "1h: 210W" in result
    assert "i100" in result
    assert "i107" in result


def test_format_power_curves_without_normalised():
    """
    Test that format_power_curves without normalised data does not include W/kg.
    """
    curves = [
        {
            "id": "s0",
            "label": "This season",
            "start": "",
            "end": "",
            "data_points": [
                {"secs": 5, "watts": 780, "activity_id": "i100"},
            ],
        },
    ]
    result = format_power_curves(curves, "Ride", include_normalised=False)
    assert "780W" in result
    assert "W/kg" not in result
