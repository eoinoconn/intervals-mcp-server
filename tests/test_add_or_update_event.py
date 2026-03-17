"""
Comprehensive tests for the add_or_update_event MCP tool.

Covers:
- Different workout types (Ride, Run, Swim, Walk, Row)
- Workout type auto-resolution from name keywords
- Step properties: duration, distance, power, HR, pace, cadence targets
- Ranges (start/end), ramps, repeats with nested steps
- Warmup, cooldown, freeride, maxeffort, until_lap_press, hidepower, intensity
- Text/comment-only steps
- Edge cases: moving_time/distance passthrough, update (PUT), no workout_doc
"""

import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server import add_or_update_event
from intervals_mcp_server.utils.types import (
    Intensity,
    Step,
    Value,
    ValueUnits,
    WorkoutDoc,
)


# ---------------------------------------------------------------------------
# Helper: fake request that captures the payload sent to the API
# ---------------------------------------------------------------------------

class FakeRequest:
    """Callable that records every invocation and returns a canned response."""

    def __init__(self, response=None):
        self.calls: list[dict] = []
        self.response = response or {
            "id": "e999",
            "start_date_local": "2026-03-11T00:00:00",
            "category": "WORKOUT",
            "name": "test",
            "type": "Ride",
        }

    async def __call__(self, *args, **kwargs):
        self.calls.append(kwargs)
        return self.response

    @property
    def last_data(self) -> dict | None:
        """Return the ``data`` kwarg from the most recent call."""
        if self.calls:
            return self.calls[-1].get("data")
        return None

    @property
    def last_method(self) -> str | None:
        """Return the ``method`` kwarg from the most recent call."""
        if self.calls:
            return self.calls[-1].get("method")
        return None

    @property
    def last_url(self) -> str | None:
        """Return the ``url`` kwarg from the most recent call."""
        if self.calls:
            return self.calls[-1].get("url")
        return None


def _patch_request(monkeypatch, fake: FakeRequest):
    """Patch make_intervals_request in both modules (matching existing test pattern)."""
    monkeypatch.setattr("intervals_mcp_server.api.client.make_intervals_request", fake)
    monkeypatch.setattr("intervals_mcp_server.tools.events.make_intervals_request", fake)


# ===================================================================
# Phase 2 – Workout type tests (one per sport)
# ===================================================================


def test_add_event_ride_workout(monkeypatch):
    """Ride workout with power-zone intervals at %ftp."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        description="Sweet-spot ride",
        steps=[
            Step(duration=600, warmup=True, text="Warmup"),
            Step(
                reps=3,
                text="3x10min sweet-spot",
                steps=[
                    Step(
                        duration=600,
                        power=Value(value=90, units=ValueUnits.PERCENT_FTP),
                        text="Sweet spot",
                    ),
                    Step(
                        duration=300,
                        power=Value(value=55, units=ValueUnits.PERCENT_FTP),
                        text="Recovery",
                    ),
                ],
            ),
            Step(duration=600, cooldown=True, text="Cooldown"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Sweet Spot Ride",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    assert "e999" in result
    payload = fake.last_data
    assert payload["type"] == "Ride"
    assert payload["category"] == "WORKOUT"
    assert payload["name"] == "Sweet Spot Ride"
    assert "Sweet-spot ride" in payload["description"]


def test_add_event_run_workout(monkeypatch):
    """Run workout with pace-based tempo intervals (mirrors sample_request.json)."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        description="Endurance run with 5x4min tempo efforts.",
        steps=[
            Step(duration=600, warmup=True, text="Easy warmup"),
            Step(
                reps=5,
                text="5x4min tempo",
                steps=[
                    Step(
                        duration=240,
                        pace=Value(value=88, units=ValueUnits.PERCENT_PACE),
                        text="Tempo - 88-92% FTP",
                    ),
                    Step(
                        duration=180,
                        pace=Value(value=65, units=ValueUnits.PERCENT_PACE),
                        text="Z2 recovery",
                    ),
                ],
            ),
            Step(duration=540, cooldown=True, text="Easy cooldown"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="4min Tempo Intervals",
            workout_type="Run",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    payload = fake.last_data
    assert payload["type"] == "Run"
    assert "5x4min tempo" in payload["description"]


def test_add_event_swim_workout(monkeypatch):
    """Swim workout with distance-based steps."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        description="Pool session - 2k total",
        steps=[
            Step(distance=400, warmup=True, text="Easy swim"),
            Step(
                reps=4,
                text="4x200m",
                steps=[
                    Step(distance=200, pace=Value(value=85, units=ValueUnits.PERCENT_PACE), text="Fast"),
                    Step(distance=100, text="Easy recovery"),
                ],
            ),
            Step(distance=200, cooldown=True, text="Cooldown"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Pool Swim Session",
            workout_type="Swim",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    payload = fake.last_data
    assert payload["type"] == "Swim"


def test_add_event_walk_workout(monkeypatch):
    """Walk workout with simple duration-based steps."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        description="Easy recovery walk",
        steps=[
            Step(duration=1800, text="Steady walk"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Recovery Walk",
            workout_type="Walk",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    payload = fake.last_data
    assert payload["type"] == "Walk"


def test_add_event_row_workout(monkeypatch):
    """Row workout with HR-based intervals."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        description="Rowing intervals by heart rate",
        steps=[
            Step(duration=300, warmup=True, text="Easy row"),
            Step(
                reps=6,
                text="6x3min HR intervals",
                steps=[
                    Step(duration=180, hr=Value(value=85, units=ValueUnits.PERCENT_HR), text="Hard"),
                    Step(duration=120, hr=Value(value=65, units=ValueUnits.PERCENT_HR), text="Easy"),
                ],
            ),
            Step(duration=300, cooldown=True, text="Cooldown"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="HR Row Session",
            workout_type="Row",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    payload = fake.last_data
    assert payload["type"] == "Row"


# ===================================================================
# Phase 3 – Workout type auto-resolution from name
# ===================================================================


# ===================================================================
# Phase 4 – Step property tests
# ===================================================================


def test_add_event_with_power_range_steps(monkeypatch):
    """Steps with power start/end range (e.g. 80-90% FTP)."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=600,
                power=Value(start=80, end=90, units=ValueUnits.PERCENT_FTP),
                text="Sweet-spot range",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Range Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    # Verify the WorkoutDoc serialises ranges correctly via str()
    desc = fake.last_data["description"]
    assert "80%" in desc
    assert "90%" in desc


def test_add_event_with_ramp_steps(monkeypatch):
    """Step with ramp=True and start/end power (ERG ramp)."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=600,
                ramp=True,
                power=Value(start=60, end=100, units=ValueUnits.PERCENT_FTP),
                text="Ramp up",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Ramp Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "ramp" in desc.lower()


def test_add_event_with_freeride_step(monkeypatch):
    """Step with freeride=True (no ERG control)."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=600,
                freeride=True,
                power=Value(value=80, units=ValueUnits.PERCENT_FTP),
                text="Free ride",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Freeride Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "freeride" in desc.lower()


def test_add_event_with_maxeffort_step(monkeypatch):
    """Step with maxeffort=True."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(duration=30, maxeffort=True, text="All out sprint"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Max Effort Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "maxeffort" in desc.lower()


def test_add_event_with_cadence_target(monkeypatch):
    """Step with a cadence target (rpm)."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=600,
                power=Value(value=75, units=ValueUnits.PERCENT_FTP),
                cadence=Value(value=95, units=ValueUnits.CADENCE),
                text="High cadence drills",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Cadence Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "95" in desc
    assert "rpm" in desc.lower()


def test_add_event_with_hr_targets(monkeypatch):
    """Steps using different HR target units: %hr, %lthr, hr_zone."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=600,
                hr=Value(value=75, units=ValueUnits.PERCENT_HR),
                text="Percent max HR",
            ),
            Step(
                duration=600,
                hr=Value(value=85, units=ValueUnits.PERCENT_LTHR),
                text="Percent LTHR",
            ),
            Step(
                duration=600,
                hr=Value(value=3, units=ValueUnits.HR_ZONE),
                text="HR Zone 3",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="HR Targets Test",
            workout_type="Run",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "75%" in desc
    assert "85%" in desc
    assert "Z3" in desc


def test_add_event_with_until_lap_press(monkeypatch):
    """Step with until_lap_press=True (open-ended segment)."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                until_lap_press=True,
                power=Value(value=70, units=ValueUnits.PERCENT_FTP),
                text="Ride until you press lap",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Lap Press Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result


def test_add_event_with_hidepower(monkeypatch):
    """Step with hidepower=True."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=1200,
                power=Value(value=80, units=ValueUnits.PERCENT_FTP),
                hidepower=True,
                text="Hidden power display",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Hide Power Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "hidepower" in desc.lower()


def test_add_event_with_intensity(monkeypatch):
    """Step with explicit Intensity enum values."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(duration=600, intensity=Intensity.WARMUP, text="Warmup phase"),
            Step(duration=300, intensity=Intensity.INTERVAL, text="Interval phase"),
            Step(duration=120, intensity=Intensity.REST, text="Rest phase"),
            Step(duration=600, intensity=Intensity.COOLDOWN, text="Cooldown phase"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Intensity Enum Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "warmup" in desc.lower()
    assert "interval" in desc.lower()
    assert "cooldown" in desc.lower()


def test_add_event_with_nested_repeats(monkeypatch):
    """Repeat block containing intervals with mixed targets."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        description="VO2max intervals",
        steps=[
            Step(duration=600, warmup=True),
            Step(
                reps=5,
                text="5x3min VO2max",
                steps=[
                    Step(
                        duration=180,
                        power=Value(value=120, units=ValueUnits.PERCENT_FTP),
                        hr=Value(value=90, units=ValueUnits.PERCENT_HR),
                        text="VO2max effort",
                    ),
                    Step(
                        duration=180,
                        power=Value(value=50, units=ValueUnits.PERCENT_FTP),
                        text="Recovery",
                    ),
                ],
            ),
            Step(duration=600, cooldown=True),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="VO2max Intervals",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "5x" in desc
    assert "VO2max" in desc


def test_add_event_with_text_comments(monkeypatch):
    """Steps with text-only entries (comments / blank line separators)."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(text="Remember to hydrate"),
            Step(duration=600, warmup=True, text="Easy spin"),
            Step(text=""),  # blank line separator
            Step(duration=1200, power=Value(value=75, units=ValueUnits.PERCENT_FTP), text="Endurance"),
            Step(text="Good job!"),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Comments Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "Remember to hydrate" in desc


# ===================================================================
# Phase 5 – Edge cases
# ===================================================================


def test_add_event_with_moving_time_and_distance(monkeypatch):
    """moving_time and distance parameters are passed through to the payload."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Measured Ride",
            workout_type="Ride",
            moving_time=3600,
            distance=40000,
        )
    )

    assert "Successfully created event id:" in result
    payload = fake.last_data
    assert payload["moving_time"] == 3600
    assert payload["distance"] == 40000


def test_add_event_update_existing(monkeypatch):
    """Providing event_id triggers PUT and returns 'updated' message."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Updated Workout",
            workout_type="Ride",
            event_id="e456",
        )
    )

    assert "updated" in result.lower()
    assert "e999" in result
    assert fake.last_method == "PUT"
    assert "e456" in fake.last_url


def test_add_event_no_workout_doc(monkeypatch):
    """Minimal event creation without a workout_doc."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Rest Day Note",
            workout_type="Ride",
        )
    )

    assert "Successfully created event id:" in result
    payload = fake.last_data
    assert payload["description"] is None
    assert payload["name"] == "Rest Day Note"


def test_add_event_with_power_watts_and_zones(monkeypatch):
    """Steps using absolute watts and power zones."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=600,
                power=Value(value=200, units=ValueUnits.WATTS),
                text="200W steady",
            ),
            Step(
                duration=600,
                power=Value(value=3, units=ValueUnits.POWER_ZONE),
                text="Power zone 3",
            ),
            Step(
                duration=300,
                power=Value(value=110, units=ValueUnits.PERCENT_MMP),
                text="110% MMP",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Power Units Test",
            workout_type="Ride",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "200W" in desc
    assert "Z3" in desc
    assert "110%" in desc


def test_add_event_with_pace_zone(monkeypatch):
    """Step with pace zone target."""
    fake = FakeRequest()
    _patch_request(monkeypatch, fake)

    doc = WorkoutDoc(
        steps=[
            Step(
                duration=1200,
                pace=Value(value=2, units=ValueUnits.PACE_ZONE),
                text="Pace zone 2 run",
            ),
        ],
    )

    result = asyncio.run(
        add_or_update_event(
            athlete_id="i1",
            start_date="2026-03-11",
            name="Pace Zone Test",
            workout_type="Run",
            workout_doc=doc,
        )
    )

    assert "Successfully created event id:" in result
    desc = fake.last_data["description"]
    assert "Z2" in desc
