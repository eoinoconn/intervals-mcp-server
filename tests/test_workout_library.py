"""
Unit tests for the workout library MCP tools.

These tests use monkeypatching to mock API responses and verify
formatting / output of each workout-library tool function:
- get_workout_folders
- list_workouts
- get_workout
- create_workout
- update_workout
"""

import asyncio
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")


def _get_tool(name: str):
    """Return the tool function from the current (possibly re-imported) workout_library module.

    test_server_config.py clears ``sys.modules`` and re-imports the server, so
    function references captured at import time may point to stale module
    globals. This helper always resolves through ``sys.modules`` so
    monkeypatching works regardless of test ordering.
    """
    mod = sys.modules.get("intervals_mcp_server.tools.workout_library")
    if mod is None:
        import intervals_mcp_server.tools.workout_library as mod  # noqa: PLW0621
    return getattr(mod, name)


# Trigger initial import so the module is in sys.modules
import intervals_mcp_server.server  # noqa: E402, F401


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_FOLDER = {
    "id": 10,
    "name": "Sweet Spot Plans",
    "type": "PLAN",
    "num_workouts": 5,
    "visibility": "PRIVATE",
    "description": "Base building plans",
    "activity_types": ["Ride"],
    "athlete_id": "i1",
    "children": [{"id": 99, "name": "should be stripped"}],
}

SAMPLE_WORKOUT_A = {
    "id": 1,
    "name": "Tempo 2x20",
    "type": "Ride",
    "folder_id": 10,
    "moving_time": 3600,
    "icu_training_load": 80,
    "tags": ["tempo"],
    "description": "Two 20-minute tempo intervals",
    "distance": 40000,
    "indoor": True,
    "color": "#ff0000",
    "updated": "2025-06-01T12:00:00Z",
    "workout_doc": {"steps": [{"duration": 1200}]},
}

SAMPLE_WORKOUT_B = {
    "id": 2,
    "name": "Endurance",
    "type": "Ride",
    "folder_id": 20,
    "moving_time": 7200,
    "icu_training_load": 60,
    "tags": [],
    "workout_doc": {"steps": []},
}


SAMPLE_SHARED_FOLDER = {
    "id": 30,
    "name": "Coach Shared Plan",
    "type": "PLAN",
    "num_workouts": 2,
    "visibility": "PUBLIC",
    "description": "Shared by coach",
    "activity_types": ["Run"],
    "athlete_id": "i_coach",
    "children": [
        {
            "id": 100,
            "name": "Shared Tempo Run",
            "type": "Run",
            "folder_id": 30,
            "moving_time": 2400,
            "icu_training_load": 50,
            "tags": ["tempo"],
        },
        {
            "id": 101,
            "name": "Shared Easy Run",
            "type": "Run",
            "folder_id": 30,
            "moving_time": 3600,
            "icu_training_load": 30,
            "tags": [],
        },
    ],
}


def _patch_workout_lib(monkeypatch, fake_request):
    """Patch make_intervals_request in the current workout_library module (handles reloads)."""
    mod = sys.modules.get("intervals_mcp_server.tools.workout_library")
    if mod is None:
        import intervals_mcp_server.tools.workout_library as mod  # noqa: PLW0621
    monkeypatch.setattr(mod, "make_intervals_request", fake_request)


# ---------------------------------------------------------------------------
# get_workout_folders
# ---------------------------------------------------------------------------


def test_get_workout_folders_success(monkeypatch):
    """Folders are returned with children stripped and shared flag."""
    async def fake_request(*_a, **_kw):
        return [SAMPLE_FOLDER, SAMPLE_SHARED_FOLDER]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout_folders")(athlete_id="i1"))
    folders = json.loads(result)
    assert len(folders) == 2
    assert folders[0]["id"] == 10
    assert "children" not in folders[0]
    assert folders[0]["name"] == "Sweet Spot Plans"
    assert folders[0]["shared"] is False
    # Shared folder owned by a different athlete
    assert folders[1]["id"] == 30
    assert folders[1]["shared"] is True


def test_get_workout_folders_empty(monkeypatch):
    """Empty list returns a human-readable message."""
    async def fake_request(*_a, **_kw):
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout_folders")(athlete_id="i1"))
    assert "No workout folders found" in result


def test_get_workout_folders_error(monkeypatch):
    """API error returns an error message."""
    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Unauthorized"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout_folders")(athlete_id="i1"))
    assert "Error fetching workout folders" in result


# ---------------------------------------------------------------------------
# list_workouts
# ---------------------------------------------------------------------------


def test_list_workouts_compact(monkeypatch):
    """Compact mode returns only compact fields; workout_doc is never present."""
    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1", compact=True))
    workouts = json.loads(result)
    assert len(workouts) == 2
    assert "workout_doc" not in workouts[0]
    assert workouts[0]["name"] == "Tempo 2x20"
    # Compact mode should not include full-mode extras
    assert "description" not in workouts[0]
    assert "distance" not in workouts[0]


def test_list_workouts_full(monkeypatch):
    """Full mode includes extra fields but still omits workout_doc."""
    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1", compact=False))
    workouts = json.loads(result)
    assert workouts[0]["description"] == "Two 20-minute tempo intervals"
    assert "workout_doc" not in workouts[0]


def test_list_workouts_folder_filter(monkeypatch):
    """folder_id filters own workouts client-side."""
    async def fake_request(*_a, **kw):
        if "/workouts" in kw.get("url", ""):
            return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B]
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1", folder_id=10))
    workouts = json.loads(result)
    assert len(workouts) == 1
    assert workouts[0]["id"] == 1


def test_list_workouts_folder_filter_no_match(monkeypatch):
    """folder_id that matches nothing in either endpoint returns human message."""
    async def fake_request(*_a, **kw):
        url = kw.get("url", "")
        if "/workouts" in url:
            return [SAMPLE_WORKOUT_A]
        if "/folders" in url:
            return [SAMPLE_FOLDER]  # folder 10, no folder 999
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1", folder_id=999))
    assert "No workouts found" in result
    assert "folder 999" in result


def test_list_workouts_shared_folder_fallback(monkeypatch):
    """Shared folder workouts are returned with shared indicator."""
    async def fake_request(*_a, **kw):
        url = kw.get("url", "")
        if "/workouts" in url:
            return [SAMPLE_WORKOUT_A]  # own workouts, none in folder 30
        if "/folders" in url:
            return [SAMPLE_SHARED_FOLDER]  # shared folder 30 with children
        return []

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1", folder_id=30))
    data = json.loads(result)
    assert data["shared"] is True
    workouts = data["workouts"]
    assert len(workouts) == 2
    assert workouts[0]["name"] == "Shared Tempo Run"
    assert workouts[1]["name"] == "Shared Easy Run"


def test_list_workouts_error(monkeypatch):
    """API error is surfaced."""
    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Forbidden"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1"))
    assert "Error fetching workouts" in result


def test_list_workouts_type_filter(monkeypatch):
    """workout_type filters workouts by activity type (case-insensitive)."""
    run_workout = {
        "id": 3,
        "name": "Easy Run",
        "type": "Run",
        "folder_id": 10,
        "moving_time": 2400,
        "icu_training_load": 40,
        "tags": ["easy"],
    }

    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B, run_workout]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1", workout_type="run"))
    workouts = json.loads(result)
    assert len(workouts) == 1
    assert workouts[0]["name"] == "Easy Run"


def test_list_workouts_type_filter_no_match(monkeypatch):
    """workout_type that matches nothing returns helpful message."""
    async def fake_request(*_a, **_kw):
        return [SAMPLE_WORKOUT_A, SAMPLE_WORKOUT_B]

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("list_workouts")(athlete_id="i1", workout_type="Swim"))
    assert "No workouts found" in result
    assert "type 'Swim'" in result


# ---------------------------------------------------------------------------
# get_workout
# ---------------------------------------------------------------------------


def test_get_workout_success(monkeypatch):
    """Full workout detail is returned including workout_doc."""
    async def fake_request(*_a, **_kw):
        return SAMPLE_WORKOUT_A

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout")(workout_id=1, athlete_id="i1"))
    data = json.loads(result)
    assert data["id"] == 1
    assert "workout_doc" in data


def test_get_workout_not_found(monkeypatch):
    """Non-existent workout returns helpful message."""
    async def fake_request(*_a, **_kw):
        return {}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout")(workout_id=999, athlete_id="i1"))
    assert "No workout found" in result


def test_get_workout_error(monkeypatch):
    """API error returns error message."""
    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Not Found"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("get_workout")(workout_id=1, athlete_id="i1"))
    assert "Error fetching workout" in result


# ---------------------------------------------------------------------------
# create_workout
# ---------------------------------------------------------------------------


def test_create_workout_success(monkeypatch):
    """Successful creation returns confirmation with JSON body."""
    captured: dict = {}

    async def fake_request(*_a, **kwargs):
        captured.update(kwargs)
        return {"id": 42, "name": "New Intervals", "type": "Ride", "folder_id": 10}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(
        _get_tool("create_workout")(
            name="New Intervals",
            workout_type="Ride",
            folder_id=10,
            athlete_id="i1",
            description="Test workout",
            moving_time=3600,
            tags=["sweet-spot"],
        )
    )
    assert "Successfully created workout" in result
    assert captured["method"] == "POST"
    body = captured["data"]
    assert body["name"] == "New Intervals"
    assert body["folder_id"] == 10
    assert body["tags"] == ["sweet-spot"]


def test_create_workout_error(monkeypatch):
    """API error returns error message."""
    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Bad Request"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(
        _get_tool("create_workout")(name="X", workout_type="Run", folder_id=1, athlete_id="i1")
    )
    assert "Error creating workout" in result


def test_create_workout_no_athlete(monkeypatch):
    """Missing athlete ID returns helpful error."""
    mod = sys.modules.get("intervals_mcp_server.tools.workout_library")
    if mod is None:
        import intervals_mcp_server.tools.workout_library as mod  # noqa: PLW0621
    monkeypatch.setattr(mod, "config", type("C", (), {"athlete_id": ""})())
    result = asyncio.run(
        _get_tool("create_workout")(name="X", workout_type="Run", folder_id=1, athlete_id="")
    )
    assert "Error" in result


# ---------------------------------------------------------------------------
# update_workout
# ---------------------------------------------------------------------------


def test_update_workout_success(monkeypatch):
    """Successful update returns confirmation."""
    captured: dict = {}

    async def fake_request(*_a, **kwargs):
        captured.update(kwargs)
        return {"id": 1, "name": "Updated", "folder_id": 20}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(
        _get_tool("update_workout")(
            workout_id=1,
            athlete_id="i1",
            name="Updated",
            folder_id=20,
            tags=["new-tag"],
        )
    )
    assert "Successfully updated workout" in result
    assert captured["method"] == "PUT"
    body = captured["data"]
    assert body["name"] == "Updated"
    assert body["folder_id"] == 20
    assert body["tags"] == ["new-tag"]


def test_update_workout_partial(monkeypatch):
    """Only provided fields are included in the request body."""
    captured: dict = {}

    async def fake_request(*_a, **kwargs):
        captured.update(kwargs)
        return {"id": 1, "name": "Only name"}

    _patch_workout_lib(monkeypatch, fake_request)
    asyncio.run(_get_tool("update_workout")(workout_id=1, athlete_id="i1", name="Only name"))
    body = captured["data"]
    assert body == {"name": "Only name"}


def test_update_workout_error(monkeypatch):
    """API error returns error message."""
    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Server Error"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(_get_tool("update_workout")(workout_id=1, athlete_id="i1", name="X"))
    assert "Error updating workout" in result


# ---------------------------------------------------------------------------
# schedule_workout
# ---------------------------------------------------------------------------


def test_schedule_workout_success(monkeypatch):
    """Fetches workout and creates calendar event."""
    calls: list[dict] = []

    async def fake_request(*_a, **kwargs):
        calls.append(kwargs)
        url = kwargs.get("url", "")
        if "/workouts/" in url:
            return SAMPLE_WORKOUT_A
        # POST to /events
        return {"id": 500, "name": "Tempo 2x20", "start_date_local": "2025-07-01T00:00:00"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(
        _get_tool("schedule_workout")(workout_id=1, start_date="2025-07-01", athlete_id="i1")
    )
    assert "Successfully scheduled" in result
    assert "Tempo 2x20" in result
    assert "event id: 500" in result
    # Verify the event POST payload
    event_call = calls[1]
    assert event_call["method"] == "POST"
    body = event_call["data"]
    assert body["category"] == "WORKOUT"
    assert body["name"] == "Tempo 2x20"
    assert body["type"] == "Ride"
    assert body["moving_time"] == 3600
    assert "workout_doc" in body


def test_schedule_workout_invalid_date(monkeypatch):
    """Invalid date format returns error."""
    _patch_workout_lib(monkeypatch, lambda *a, **kw: None)
    result = asyncio.run(
        _get_tool("schedule_workout")(workout_id=1, start_date="not-a-date", athlete_id="i1")
    )
    assert "YYYY-MM-DD" in result


def test_schedule_workout_not_found(monkeypatch):
    """Non-existent workout returns error."""
    async def fake_request(*_a, **_kw):
        return {}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(
        _get_tool("schedule_workout")(workout_id=999, start_date="2025-07-01", athlete_id="i1")
    )
    assert "No workout found" in result


def test_schedule_workout_fetch_error(monkeypatch):
    """API error when fetching workout is surfaced."""
    async def fake_request(*_a, **_kw):
        return {"error": True, "message": "Not Found"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(
        _get_tool("schedule_workout")(workout_id=1, start_date="2025-07-01", athlete_id="i1")
    )
    assert "Error fetching workout" in result


def test_schedule_workout_event_creation_error(monkeypatch):
    """API error when creating calendar event is surfaced."""
    async def fake_request(*_a, **kwargs):
        url = kwargs.get("url", "")
        if "/workouts/" in url:
            return SAMPLE_WORKOUT_A
        return {"error": True, "message": "Server Error"}

    _patch_workout_lib(monkeypatch, fake_request)
    result = asyncio.run(
        _get_tool("schedule_workout")(workout_id=1, start_date="2025-07-01", athlete_id="i1")
    )
    assert "Error creating calendar event" in result
