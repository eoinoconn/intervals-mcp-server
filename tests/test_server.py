"""
Unit tests for the main MCP server tool functions in intervals_mcp_server.server.

These tests use monkeypatching to mock API responses and verify the formatting and output of each tool function:
- get_activities
- get_activity_details
- get_activity_intervals
- get_activity_streams
- get_activity_messages
- add_activity_message
- get_events
- get_event_by_id
- add_or_update_event
- get_wellness_data

The tests ensure that the server's public API returns expected strings and handles data correctly.
"""

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server import (  # pylint: disable=wrong-import-position
    add_activity_message,
    add_or_update_event,
    get_activities,
    get_activity_details,
    get_activity_intervals,
    get_activity_messages,
    get_activity_streams,
    get_athlete_power_curves,
    get_athlete_zones,
    get_event_by_id,
    get_events,
    get_wellness_data,
    get_custom_items,
    get_custom_item_by_id,
    create_custom_item,
    update_custom_item,
    delete_custom_item,
)
from tests.sample_data import INTERVALS_DATA, POWER_CURVES_DATA, SPORT_SETTINGS_DATA  # pylint: disable=wrong-import-position


def test_get_activities(monkeypatch):
    """
    Test get_activities returns a formatted string containing activity details when given a sample activity.
    """
    sample = {
        "name": "Morning Ride",
        "id": 123,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }

    async def fake_request(*_args, **_kwargs):
        return [sample]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activities(athlete_id="1", limit=1, include_unnamed=True))
    assert "Morning Ride" in result
    assert "Activities:" in result


def test_get_activity_details(monkeypatch):
    """
    Test get_activity_details returns a formatted string with the activity name and details.
    """
    sample = {
        "name": "Morning Ride",
        "id": 123,
        "type": "Ride",
        "startTime": "2024-01-01T08:00:00Z",
        "distance": 1000,
        "duration": 3600,
    }

    async def fake_request(*_args, **_kwargs):
        return sample

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_details(123))
    assert "Activity: Morning Ride" in result


def test_get_activity_details_with_compliance(monkeypatch):
    """
    Test get_activity_details includes workout compliance when the activity is paired with a workout.
    """
    sample = {
        "name": "Threshold Workout",
        "id": 456,
        "type": "Ride",
        "startTime": "2024-06-01T07:00:00Z",
        "distance": 40000,
        "duration": 5400,
        "paired_event_id": 789,
        "compliance": 92.0,
    }

    async def fake_request(*_args, **_kwargs):
        return sample

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_details(456))
    assert "Workout Compliance:" in result
    assert "Paired Event ID: 789" in result
    assert "Compliance: 92.00%" in result


def test_get_activity_details_with_ignore_flags(monkeypatch):
    """
    Test get_activity_details includes data ignore flags when they are True.
    """
    sample = {
        "name": "Indoor Ride",
        "id": 789,
        "type": "Ride",
        "startTime": "2024-07-01T09:00:00Z",
        "distance": 30000,
        "duration": 3600,
        "icu_ignore_time": True,
        "icu_ignore_power": True,
        "icu_ignore_hr": False,
    }

    async def fake_request(*_args, **_kwargs):
        return sample

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_details(789))
    assert "Data Flags:" in result
    assert "Ignore Time: True" in result
    assert "Ignore Power: True" in result
    assert "Ignore HR" not in result


def test_get_activity_details_no_ignore_flags(monkeypatch):
    """
    Test get_activity_details omits Data Flags section when all flags are False.
    """
    sample = {
        "name": "Normal Ride",
        "id": 101,
        "type": "Ride",
        "startTime": "2024-08-01T10:00:00Z",
        "distance": 50000,
        "duration": 7200,
        "icu_ignore_time": False,
        "icu_ignore_power": False,
        "icu_ignore_hr": False,
    }

    async def fake_request(*_args, **_kwargs):
        return sample

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_details(101))
    assert "Data Flags:" not in result


def test_get_events(monkeypatch):
    """
    Test get_events returns a formatted string containing event details when given a sample event.
    """
    event = {
        "date": "2024-01-01",
        "id": "e1",
        "name": "Test Event",
        "description": "desc",
        "race": True,
    }

    async def fake_request(*_args, **_kwargs):
        return [event]

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake_request)
    result = asyncio.run(get_events(athlete_id="1", start_date="2024-01-01", end_date="2024-01-02"))
    assert "Test Event" in result
    assert "Events:" in result


def test_get_event_by_id(monkeypatch):
    """
    Test get_event_by_id returns a formatted string with event details for a given event ID.
    """
    event = {
        "id": "e1",
        "date": "2024-01-01",
        "name": "Test Event",
        "description": "desc",
        "race": True,
    }

    async def fake_request(*_args, **_kwargs):
        return event

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake_request)
    result = asyncio.run(get_event_by_id("e1", athlete_id="1"))
    assert "Event Details:" in result
    assert "Test Event" in result


def test_get_wellness_data(monkeypatch):
    """
    Test get_wellness_data returns a formatted string containing wellness data for a given athlete.
    """
    wellness = {
        "2024-01-01": {
            "id": "2024-01-01",
            "ctl": 75,
            "sleepSecs": 28800,
        }
    }

    async def fake_request(*_args, **_kwargs):
        return wellness

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.make_intervals_request", fake_request)
    result = asyncio.run(get_wellness_data(athlete_id="1"))
    assert "Wellness Data:" in result
    assert "2024-01-01" in result


def test_get_wellness_data_with_fields(monkeypatch):
    """
    Test that get_wellness_data filters sections when fields is provided.
    """
    wellness = [
        {"id": "2024-01-01", "ctl": 75, "sleepSecs": 28800, "weight": 70},
    ]

    async def fake_request(*_args, **_kwargs):
        return wellness

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.make_intervals_request", fake_request)
    result = asyncio.run(get_wellness_data(athlete_id="1", fields=["vital_signs"]))
    assert "Vital Signs:" in result
    assert "Training Metrics:" not in result
    assert "Sleep & Recovery:" not in result


def test_get_wellness_data_invalid_fields(monkeypatch):
    """
    Test that get_wellness_data rejects invalid field names.
    """
    result = asyncio.run(get_wellness_data(athlete_id="1", fields=["invalid_field"]))
    assert "Invalid field(s)" in result


def test_get_wellness_data_with_cadence(monkeypatch):
    """
    Test that cadence parameter returns every Nth entry.
    """
    wellness = [
        {"id": f"2024-01-{i:02d}", "ctl": i} for i in range(1, 15)
    ]

    async def fake_request(*_args, **_kwargs):
        return wellness

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.make_intervals_request", fake_request)
    result = asyncio.run(get_wellness_data(athlete_id="1", cadence=7))
    # 14 entries with cadence=7 -> entries at index 0 and 7 -> days 01 and 08
    assert "2024-01-01" in result
    assert "2024-01-08" in result
    assert "2024-01-02" not in result
    assert "2024-01-03" not in result


def test_get_wellness_data_cadence_invalid(monkeypatch):
    """
    Test that cadence < 1 returns an error message.
    """
    result = asyncio.run(get_wellness_data(athlete_id="1", cadence=0))
    assert "Cadence must be a positive integer" in result


def test_get_wellness_data_include_all_fields(monkeypatch):
    """
    Test get_wellness_data with include_all_fields=True returns a formatted string including additional fields.
    """
    wellness = [
        {
            "id": "2024-01-01",
            "ctl": 75,
            "sleepSecs": 28800,
            "customField": "custom_value",
        }
    ]

    async def fake_request(*_args, **_kwargs):
        return wellness

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr("intervals_mcp_server.tools.wellness.make_intervals_request", fake_request)
    result = asyncio.run(get_wellness_data(athlete_id="1", include_all_fields=True))
    assert "Wellness Data:" in result
    assert "2024-01-01" in result
    assert "Fitness (CTL): 75" in result
    assert "Other Fields:" in result
    assert "customField: custom_value" in result


def test_get_activity_intervals(monkeypatch):
    """
    Test get_activity_intervals returns a formatted string with interval analysis for a given activity.
    """

    async def fake_request(*_args, **_kwargs):
        return INTERVALS_DATA

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_intervals("123"))
    assert "Intervals Analysis:" in result
    assert "Rep 1" in result


def test_get_activity_intervals_with_ignore_flags(monkeypatch):
    """
    Test get_activity_intervals includes data ignore flags when the activity has them set to True.
    """
    activity_data = {
        "id": "i1",
        "icu_ignore_time": True,
        "icu_ignore_power": False,
        "icu_ignore_hr": True,
    }

    async def fake_request(*_args, **kwargs):
        url = kwargs.get("url", _args[0] if _args else "")
        if "/intervals" in str(url):
            return INTERVALS_DATA
        return activity_data

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_intervals("i1"))
    assert "Data Flags:" in result
    assert "Ignore Time: True" in result
    assert "Ignore HR: True" in result
    assert "Ignore Power" not in result
    assert "Intervals Analysis:" in result
    assert "Rep 1" in result


def test_get_activity_intervals_no_ignore_flags(monkeypatch):
    """
    Test get_activity_intervals omits Data Flags section when all flags are False.
    """
    activity_data = {
        "id": "i1",
        "icu_ignore_time": False,
        "icu_ignore_power": False,
        "icu_ignore_hr": False,
    }

    async def fake_request(*_args, **kwargs):
        url = kwargs.get("url", _args[0] if _args else "")
        if "/intervals" in str(url):
            return INTERVALS_DATA
        return activity_data

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_intervals("i1"))
    assert "Data Flags:" not in result
    assert "Intervals Analysis:" in result


def test_get_activity_streams(monkeypatch):
    """
    Test get_activity_streams returns a formatted string with stream data for a given activity.
    """
    sample_streams = [
        {
            "type": "time",
            "name": "time",
            "data": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "data2": [],
            "valueType": "time_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
        {
            "type": "watts",
            "name": "watts",
            "data": [150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200],
            "data2": [],
            "valueType": "power_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
        {
            "type": "heartrate",
            "name": "heartrate",
            "data": [120, 125, 130, 135, 140, 145, 150, 155, 160, 165, 170],
            "data2": [],
            "valueType": "hr_units",
            "valueTypeIsArray": False,
            "anomalies": None,
            "custom": False,
        },
    ]

    async def fake_request(*_args, **_kwargs):
        return sample_streams

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_streams("i107537962"))
    assert "Activity Streams" in result
    assert "time" in result
    assert "watts" in result
    assert "heartrate" in result
    assert "Data Points: 11" in result


def test_add_or_update_event(monkeypatch):
    """
    Test add_or_update_event successfully posts an event and returns the response data.
    """
    expected_response = {
        "id": "e123",
        "start_date_local": "2024-01-15T00:00:00",
        "category": "WORKOUT",
        "name": "Test Workout",
        "type": "Ride",
    }

    async def fake_post_request(*_args, **_kwargs):
        return expected_response

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_post_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.events.make_intervals_request", fake_post_request
    )
    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1", start_date="2024-01-15", name="Test Workout", workout_type="Ride"
        )
    )
    assert "Successfully created event id:" in result
    assert "e123" in result


def test_get_activity_messages(monkeypatch):
    """Test get_activity_messages returns formatted messages for an activity."""
    sample_messages = [
        {
            "id": 1,
            "name": "Niko",
            "created": "2024-06-15T10:30:00Z",
            "type": "NOTE",
            "content": "Legs felt heavy today",
        },
        {
            "id": 2,
            "name": "Coach",
            "created": "2024-06-15T11:00:00Z",
            "type": "TEXT",
            "content": "Good effort despite that!",
        },
    ]

    async def fake_request(*_args, **_kwargs):
        return sample_messages

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_messages(activity_id="i123"))
    assert "Legs felt heavy today" in result
    assert "Good effort despite that!" in result
    assert "Niko" in result
    assert "Coach" in result


def test_get_activity_messages_error(monkeypatch):
    """Test get_activity_messages handles API errors gracefully."""

    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Activity not found"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_messages(activity_id="i999"))
    assert "Error fetching activity messages" in result
    assert "Activity not found" in result


def test_get_activity_messages_empty(monkeypatch):
    """Test get_activity_messages returns appropriate message when no messages exist."""

    async def fake_request(*_args, **_kwargs):
        return []

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(get_activity_messages(activity_id="i123"))
    assert "No messages found" in result


def test_add_activity_message(monkeypatch):
    """Test add_activity_message posts a message and returns confirmation."""

    async def fake_request(*_args, **kwargs):
        assert kwargs.get("method") == "POST"
        assert kwargs.get("data") == {"content": "Great run!"}
        return {"id": 42, "new_chat": None}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i123", content="Great run!"))
    assert "Successfully added message" in result
    assert "42" in result


def test_add_activity_message_missing_id(monkeypatch):
    """Test add_activity_message warns when response has no ID."""

    async def fake_request(*_args, **_kwargs):
        return {"new_chat": None}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i123", content="Hello"))
    assert "appears to have been added" in result
    assert "verify manually" in result


def test_add_activity_message_unexpected_response(monkeypatch):
    """Test add_activity_message handles unexpected non-dict response."""

    async def fake_request(*_args, **_kwargs):
        return None

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i123", content="Hello"))
    assert "Unexpected response" in result


def test_add_activity_message_error(monkeypatch):
    """Test add_activity_message handles API errors."""

    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Not found"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.activities.make_intervals_request", fake_request
    )
    result = asyncio.run(add_activity_message(activity_id="i999", content="Hello"))
    assert "Error adding message" in result


def test_get_athlete_power_curves(monkeypatch):
    """
    Test get_athlete_power_curves returns formatted power curve data with both seasons.
    """

    async def fake_request(*_args, **_kwargs):
        return POWER_CURVES_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.power_curves.make_intervals_request", fake_request
    )
    result = asyncio.run(
        get_athlete_power_curves(
            activity_type="Ride",
            athlete_id="i1",
        )
    )
    assert "Power Curves (Ride):" in result
    assert "This season" in result
    assert "Last season" in result
    assert "5s:" in result
    assert "W/kg" in result
    assert "i100" in result


def test_get_athlete_power_curves_custom_durations(monkeypatch):
    """
    Test get_athlete_power_curves with custom durations returns only those durations.
    """

    async def fake_request(*_args, **_kwargs):
        return POWER_CURVES_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.power_curves.make_intervals_request", fake_request
    )
    result = asyncio.run(
        get_athlete_power_curves(
            activity_type="Ride",
            durations=[5, 60],
            athlete_id="i1",
        )
    )
    assert "5s:" in result
    assert "1m:" in result
    # Should not contain durations we didn't request
    assert "15s:" not in result
    assert "10m:" not in result


def test_get_athlete_power_curves_without_normalised(monkeypatch):
    """
    Test get_athlete_power_curves without normalised data excludes W/kg values.
    """

    async def fake_request(*_args, **_kwargs):
        return POWER_CURVES_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.power_curves.make_intervals_request", fake_request
    )
    result = asyncio.run(
        get_athlete_power_curves(
            activity_type="Ride",
            include_normalised=False,
            athlete_id="i1",
        )
    )
    assert "W/kg" not in result
    assert "780W" in result


def test_get_athlete_power_curves_date_validation(monkeypatch):
    """
    Test get_athlete_power_curves validates date parameters.
    """

    async def fake_request(*_args, **_kwargs):
        return POWER_CURVES_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.power_curves.make_intervals_request", fake_request
    )
    # Only start_date without end_date should fail
    result = asyncio.run(
        get_athlete_power_curves(
            activity_type="Ride",
            start_date="2026-01-01",
            athlete_id="i1",
        )
    )
    assert "Error" in result
    assert "start_date and end_date must be provided together" in result


def test_get_athlete_power_curves_no_curves_selected(monkeypatch):
    """
    Test get_athlete_power_curves returns error when no curves selected.
    """

    async def fake_request(*_args, **_kwargs):
        return POWER_CURVES_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.power_curves.make_intervals_request", fake_request
    )
    result = asyncio.run(
        get_athlete_power_curves(
            activity_type="Ride",
            this_season=False,
            last_season=False,
            athlete_id="i1",
        )
    )
    assert "Error" in result
    assert "At least one curve must be selected" in result
def test_get_custom_items(monkeypatch):
    """
    Test get_custom_items returns a formatted string containing custom item details.
    """
    custom_items = [
        {"id": 1, "name": "HR Zones", "type": "ZONES", "description": "Heart rate zones"},
        {"id": 2, "name": "Power Chart", "type": "FITNESS_CHART", "description": None},
    ]

    async def fake_request(*_args, **_kwargs):
        return custom_items

    # Patch in both api.client and tools modules to ensure it works
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(get_custom_items(athlete_id="1"))
    assert "Custom Items:" in result
    assert "HR Zones" in result
    assert "ZONES" in result
    assert "Power Chart" in result


def test_get_custom_item_by_id(monkeypatch):
    """
    Test get_custom_item_by_id returns formatted details of a single custom item.
    """
    custom_item = {
        "id": 1,
        "name": "HR Zones",
        "type": "ZONES",
        "description": "Heart rate zones",
        "visibility": "PRIVATE",
        "index": 0,
    }

    async def fake_request(*_args, **_kwargs):
        return custom_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(get_custom_item_by_id(item_id=1, athlete_id="1"))
    assert "Custom Item Details:" in result
    assert "HR Zones" in result
    assert "ZONES" in result
    assert "Heart rate zones" in result
    assert "PRIVATE" in result


def test_create_custom_item(monkeypatch):
    """
    Test create_custom_item returns a success message with formatted item details.
    """
    created_item = {
        "id": 10,
        "name": "New Chart",
        "type": "FITNESS_CHART",
        "description": "A new fitness chart",
        "visibility": "PRIVATE",
    }

    async def fake_request(*_args, **_kwargs):
        return created_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(name="New Chart", item_type="FITNESS_CHART", athlete_id="1")
    )
    assert "Successfully created custom item:" in result
    assert "New Chart" in result
    assert "FITNESS_CHART" in result


def test_create_custom_item_with_string_content(monkeypatch):
    """
    Test create_custom_item correctly parses content when passed as a JSON string.
    """
    captured: dict = {}

    async def fake_request(*_args, **kwargs):
        captured["data"] = kwargs.get("data")
        return {
            "id": 11,
            "name": "Activity Field",
            "type": "ACTIVITY_FIELD",
            "content": {"expression": "icu_training_load"},
        }

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(
            name="Activity Field",
            item_type="ACTIVITY_FIELD",
            athlete_id="1",
            content='{"expression": "icu_training_load"}',  # type: ignore[arg-type]
        )
    )
    assert "Successfully created custom item:" in result
    # Verify the content was parsed from string to dict before being sent
    assert isinstance(captured["data"]["content"], dict)
    assert captured["data"]["content"]["expression"] == "icu_training_load"


def test_update_custom_item(monkeypatch):
    """
    Test update_custom_item returns a success message with formatted item details.
    """
    updated_item = {
        "id": 1,
        "name": "Updated Chart",
        "type": "FITNESS_CHART",
        "description": "Updated description",
        "visibility": "PUBLIC",
    }

    async def fake_request(*_args, **_kwargs):
        return updated_item

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        update_custom_item(item_id=1, name="Updated Chart", athlete_id="1")
    )
    assert "Successfully updated custom item:" in result
    assert "Updated Chart" in result
    assert "PUBLIC" in result


def test_delete_custom_item(monkeypatch):
    """
    Test delete_custom_item returns the API response.
    """

    async def fake_request(*_args, **_kwargs):
        return {}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(delete_custom_item(item_id=1, athlete_id="1"))
    assert "Successfully deleted" in result


def test_create_custom_item_with_invalid_json_content(monkeypatch):
    """
    Test create_custom_item returns an error message when content is an invalid JSON string.
    """

    async def fake_request(*_args, **_kwargs):
        return {}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.custom_items.make_intervals_request", fake_request
    )
    result = asyncio.run(
        create_custom_item(
            name="Bad Item",
            item_type="FITNESS_CHART",
            athlete_id="1",
            content="not valid json",  # type: ignore[arg-type]
        )
    )
    assert "Error: content must be valid JSON when passed as a string." in result


def test_get_athlete_zones_all_sports(monkeypatch):
    """
    Test get_athlete_zones returns zones for all sports when no sport filter is given.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1"))

    parsed = json.loads(result)
    assert len(parsed) == 3
    sports = [z["sport"] for z in parsed]
    assert "Ride" in sports
    assert "Run" in sports
    assert "Swim" in sports
    # All sports should have last_updated
    for z in parsed:
        assert "last_updated" in z


def test_get_athlete_zones_filter_by_sport(monkeypatch):
    """
    Test get_athlete_zones filters to a single sport when sport parameter is provided.
    Pace zones for Run should be in min/km format.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Run"))

    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["sport"] == "Run"
    assert "power_zones" in parsed[0]
    assert "hr_zones" in parsed[0]
    assert "pace_zones" in parsed[0]
    # Run pace zones should use min/km keys
    pz = parsed[0]["pace_zones"]
    assert "min_minkm" in pz[0]  # Zone 1 has fast boundary
    assert "max_minkm" not in pz[0]  # Zone 1 has no slow boundary
    assert "min_minkm" in pz[1]  # Zone 2 has both
    assert "max_minkm" in pz[1]


def test_get_athlete_zones_filter_unknown_sport(monkeypatch):
    """
    Test get_athlete_zones returns error message when filtering by a non-existent sport.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Ski"))
    assert "No zone settings found for sport 'Ski'" in result


def test_get_athlete_zones_omits_empty_zones(monkeypatch):
    """
    Test that zone types that are empty/not configured for a sport are omitted
    (e.g. no power zones or pace zones for Swim).
    Swim pace zones should use sec/100m format.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Swim"))

    parsed = json.loads(result)
    swim = parsed[0]
    # Swim has no FTP, so no power zones
    assert "power_zones" not in swim
    # Swim has HR zones
    assert "hr_zones" in swim
    # Swim has pace zones in sec/100m
    assert "pace_zones" in swim
    pz = swim["pace_zones"]
    assert "min_sec100m" in pz[0]
    assert "max_sec100m" not in pz[0]  # Zone 1 has no slow boundary
    assert "min_sec100m" in pz[1]
    assert "max_sec100m" in pz[1]


def test_get_athlete_zones_ride_no_pace(monkeypatch):
    """
    Test that Ride has no pace zones (threshold_pace is null for Ride).
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Ride"))

    parsed = json.loads(result)
    ride = parsed[0]
    assert "power_zones" in ride
    assert "hr_zones" in ride
    assert "pace_zones" not in ride


def test_get_athlete_zones_power_zone_values(monkeypatch):
    """
    Test that power zone watt values are correctly computed from FTP and percentages.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Ride"))

    parsed = json.loads(result)
    ride = parsed[0]
    pz = ride["power_zones"]
    # FTP=261, first zone upper = 55% of 261 = 143.55 → round to 144
    assert pz[0]["name"] == "Active Recovery"
    assert pz[0]["min_w"] == 0
    assert pz[0]["max_w"] == round(261 * 55 / 100)
    # Last zone (Neuromuscular, 999%) should have no max_w
    assert pz[-1]["name"] == "Neuromuscular"
    assert "max_w" not in pz[-1]


def test_get_athlete_zones_thresholds(monkeypatch):
    """
    Test that thresholds are correctly extracted, including converted pace values.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Run"))

    parsed = json.loads(result)
    run = parsed[0]
    assert run["thresholds"]["ftp_w"] == 455
    assert run["thresholds"]["lthr_bpm"] == 181
    assert run["thresholds"]["max_hr_bpm"] == 193
    assert run["thresholds"]["threshold_pace_ms"] == round(3.6363637, 2)
    assert run["thresholds"]["pace_units"] == "MINS_KM"
    # Converted threshold pace: 1000/3.6363637 ≈ 275s = 4:35/km
    assert run["thresholds"]["threshold_pace_minkm"] == "4:35"
    assert run["last_updated"] == "2026-03-07T21:47:41.692+00:00"


def test_get_athlete_zones_run_pace_values(monkeypatch):
    """
    Test that Run pace zones are correctly converted to min/km format.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Run"))

    parsed = json.loads(result)
    pz = parsed[0]["pace_zones"]
    # Zone 1 (77.5%): speed=3.6363637*0.775=2.8182 m/s → 1000/2.8182≈354.9s → 5:55/km
    assert pz[0]["name"] == "Zone 1"
    assert pz[0]["min_minkm"] == "5:55"
    assert "max_minkm" not in pz[0]
    # Last zone (999%) should have no min (no fast boundary), only max (slow boundary)
    assert "min_minkm" not in pz[-1]
    assert "max_minkm" in pz[-1]


def test_get_athlete_zones_swim_pace_values(monkeypatch):
    """
    Test that Swim pace zones are correctly converted to sec/100m format.
    """

    async def fake_request(*_args, **_kwargs):
        return SPORT_SETTINGS_DATA

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1", sport="Swim"))

    parsed = json.loads(result)
    swim = parsed[0]
    pz = swim["pace_zones"]
    # Zone 1 (77.5%): speed=0.9009009*0.775=0.6982 m/s → 100/0.6982≈143.2 sec/100m
    assert pz[0]["name"] == "Zone 1"
    assert pz[0]["min_sec100m"] == 143.2
    assert "max_sec100m" not in pz[0]
    # Swim threshold pace in sec/100m: 100/0.9009009≈111.0
    assert swim["thresholds"]["threshold_pace_sec100m"] == 111.0


def test_get_athlete_zones_api_error(monkeypatch):
    """
    Test get_athlete_zones handles API errors gracefully.
    """

    async def fake_request(*_args, **_kwargs):
        return {"error": True, "message": "Unauthorized"}

    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake_request)
    monkeypatch.setattr(
        "intervals_mcp_server.tools.athlete.make_intervals_request", fake_request
    )
    result = asyncio.run(get_athlete_zones(athlete_id="i1"))
    assert "Error fetching athlete zones" in result
    assert "Unauthorized" in result


def test_get_athlete_zones_no_athlete_id(monkeypatch):
    """
    Test get_athlete_zones returns error when no athlete ID is available.
    """
    from intervals_mcp_server import config as config_module

    original = config_module._config_instance
    monkeypatch.setattr(config_module, "_config_instance", None)
    monkeypatch.setenv("ATHLETE_ID", "")
    monkeypatch.setenv("API_KEY", "test")
    config_module._config_instance = config_module.load_config()

    try:
        result = asyncio.run(get_athlete_zones(athlete_id=None))
        assert "Error" in result or "No athlete ID" in result
    finally:
        config_module._config_instance = original
