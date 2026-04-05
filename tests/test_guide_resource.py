"""
Unit tests for the intervals.icu guide resource.

Validates that the coaching_context_protocol resource returns the expected structured
plain-text content and that key sections are present.
"""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.server import coaching_context_protocol  # pylint: disable=wrong-import-position
from intervals_mcp_server.resources.guide import USAGE_GUIDE  # pylint: disable=wrong-import-position


def test_coaching_context_protocol_returns_usage_guide_constant():
    """coaching_context_protocol() must return the module-level USAGE_GUIDE constant."""
    assert coaching_context_protocol() is USAGE_GUIDE


def test_usage_guide_is_plain_text():
    """The guide content must be a plain string, not JSON or markdown."""
    assert isinstance(USAGE_GUIDE, str)
    # Should not start with JSON or markdown indicators
    assert not USAGE_GUIDE.startswith("{")
    assert not USAGE_GUIDE.startswith("[")
    assert not USAGE_GUIDE.startswith("#")


def test_usage_guide_covers_activities():
    """Activities section must be present."""
    assert "Activities" in USAGE_GUIDE
    assert "completed sessions uploaded from a device" in USAGE_GUIDE


def test_usage_guide_covers_events():
    """Events section must be present."""
    assert "Events" in USAGE_GUIDE
    assert "Planned workouts" in USAGE_GUIDE


def test_usage_guide_covers_wellness():
    """Wellness section must be present."""
    assert "Wellness" in USAGE_GUIDE
    assert "one entry per day" in USAGE_GUIDE


def test_usage_guide_covers_load_metrics():
    """Load metric definitions (CTL, ATL, TSB) must be present."""
    assert "CTL" in USAGE_GUIDE
    assert "ATL" in USAGE_GUIDE
    assert "TSB" in USAGE_GUIDE
    assert "42-day" in USAGE_GUIDE
    assert "7-day" in USAGE_GUIDE


def test_usage_guide_covers_recommended_workflows():
    """Recommended workflows section must be present."""
    assert "RECOMMENDED WORKFLOWS" in USAGE_GUIDE
    assert "get_training_summary" in USAGE_GUIDE


def test_usage_guide_covers_available_tools():
    """Available tools catalogue must be present."""
    assert "AVAILABLE TOOLS" in USAGE_GUIDE
    expected_tools = [
        "get_training_summary",
        "get_athlete_zones",
        "get_activities",
        "get_activity_details",
        "get_activity_intervals",
        "get_activity_streams",
        "get_wellness_data",
        "get_events",
        "get_event_by_id",
        "add_or_update_event",
        "delete_event",
        "delete_events_by_date_range",
        "get_custom_items",
    ]
    for tool in expected_tools:
        assert tool in USAGE_GUIDE, f"Tool {tool!r} missing from AVAILABLE TOOLS"


def test_usage_guide_documents_compliance_distinction():
    """The compliance field distinction must be documented."""
    assert "compliance" in USAGE_GUIDE
    assert "execution vs prescription" in USAGE_GUIDE
    assert "session count ratio" in USAGE_GUIDE


def test_usage_guide_documents_zero_tss_behaviour():
    """Zero-TSS activity type behaviour must be documented."""
    assert "TSS = 0" in USAGE_GUIDE
    assert "Workout" in USAGE_GUIDE
    assert "WeightTraining" in USAGE_GUIDE


def test_coaching_context_protocol_exported_in_server_all():
    """coaching_context_protocol must be listed in server.py __all__."""
    from intervals_mcp_server.server import __all__ as server_all

    assert "coaching_context_protocol" in server_all
