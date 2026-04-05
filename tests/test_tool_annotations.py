"""
Tests to verify that all MCP tools have the required annotations
(title, readOnlyHint, destructiveHint) per Anthropic Software Directory Policy §5.E.
"""

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
os.environ.setdefault("API_KEY", "test")
os.environ.setdefault("ATHLETE_ID", "i1")

from intervals_mcp_server.mcp_instance import mcp  # noqa: E402

# Import all tool modules so they register with the mcp instance
import intervals_mcp_server.tools.activities  # noqa: E402, F401
import intervals_mcp_server.tools.events  # noqa: E402, F401
import intervals_mcp_server.tools.wellness  # noqa: E402, F401
import intervals_mcp_server.tools.custom_items  # noqa: E402, F401
import intervals_mcp_server.tools.athlete  # noqa: E402, F401
import intervals_mcp_server.tools.power_curves  # noqa: E402, F401
import intervals_mcp_server.tools.training_summary  # noqa: E402, F401


EXPECTED_ANNOTATIONS = {
    "get_activities": {"title": "Get Activities", "readOnlyHint": True, "destructiveHint": False},
    "get_activity_details": {"title": "Get Activity Details", "readOnlyHint": True, "destructiveHint": False},
    "get_activity_intervals": {"title": "Get Activity Intervals", "readOnlyHint": True, "destructiveHint": False},
    "get_activity_streams": {"title": "Get Activity Streams", "readOnlyHint": True, "destructiveHint": False},
    "get_activity_messages": {"title": "Get Activity Messages", "readOnlyHint": True, "destructiveHint": False},
    "add_activity_message": {"title": "Add Activity Message", "readOnlyHint": False, "destructiveHint": False},
    "get_events": {"title": "Get Events", "readOnlyHint": True, "destructiveHint": False},
    "get_event_by_id": {"title": "Get Event by ID", "readOnlyHint": True, "destructiveHint": False},
    "add_or_update_event": {"title": "Add or Update Event", "readOnlyHint": False, "destructiveHint": False},
    "delete_event": {"title": "Delete Event", "readOnlyHint": False, "destructiveHint": True},
    "delete_events_by_date_range": {"title": "Delete Events by Date Range", "readOnlyHint": False, "destructiveHint": True},
    "get_wellness_data": {"title": "Get Wellness Data", "readOnlyHint": True, "destructiveHint": False},
    "get_custom_items": {"title": "Get Custom Items", "readOnlyHint": True, "destructiveHint": False},
    "get_custom_item_by_id": {"title": "Get Custom Item by ID", "readOnlyHint": True, "destructiveHint": False},
    "create_custom_item": {"title": "Create Custom Item", "readOnlyHint": False, "destructiveHint": False},
    "update_custom_item": {"title": "Update Custom Item", "readOnlyHint": False, "destructiveHint": False},
    "delete_custom_item": {"title": "Delete Custom Item", "readOnlyHint": False, "destructiveHint": True},
    "get_training_summary": {"title": "Get Training Summary", "readOnlyHint": True, "destructiveHint": False},
    "get_athlete_zones": {"title": "Get Athlete Zones", "readOnlyHint": True, "destructiveHint": False},
    "get_athlete_power_curves": {"title": "Get Athlete Power Curves", "readOnlyHint": True, "destructiveHint": False},
}


def _get_tool_map() -> dict:
    """Build a mapping of tool name to Tool object from the mcp instance."""
    tools = {}
    for tool in mcp._tool_manager._tools.values():
        tools[tool.name] = tool
    return tools


def test_all_tools_have_annotations():
    """Every registered tool must have annotations set."""
    tool_map = _get_tool_map()
    for tool_name in EXPECTED_ANNOTATIONS:
        assert tool_name in tool_map, f"Tool '{tool_name}' not found in registered tools"
        tool = tool_map[tool_name]
        assert tool.annotations is not None, f"Tool '{tool_name}' is missing annotations"


def test_all_tools_have_title():
    """Every registered tool must have a title annotation."""
    tool_map = _get_tool_map()
    for tool_name, expected in EXPECTED_ANNOTATIONS.items():
        tool = tool_map[tool_name]
        assert tool.annotations is not None
        assert tool.annotations.title == expected["title"], (
            f"Tool '{tool_name}' title mismatch: "
            f"expected '{expected['title']}', got '{tool.annotations.title}'"
        )


def test_all_tools_have_read_only_hint():
    """Every registered tool must have a readOnlyHint annotation."""
    tool_map = _get_tool_map()
    for tool_name, expected in EXPECTED_ANNOTATIONS.items():
        tool = tool_map[tool_name]
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint == expected["readOnlyHint"], (
            f"Tool '{tool_name}' readOnlyHint mismatch: "
            f"expected {expected['readOnlyHint']}, got {tool.annotations.readOnlyHint}"
        )


def test_all_tools_have_destructive_hint():
    """Every registered tool must have a destructiveHint annotation."""
    tool_map = _get_tool_map()
    for tool_name, expected in EXPECTED_ANNOTATIONS.items():
        tool = tool_map[tool_name]
        assert tool.annotations is not None
        assert tool.annotations.destructiveHint == expected["destructiveHint"], (
            f"Tool '{tool_name}' destructiveHint mismatch: "
            f"expected {expected['destructiveHint']}, got {tool.annotations.destructiveHint}"
        )


def test_no_tool_missing_annotations():
    """Ensure no registered tool is missing annotations entirely."""
    tool_map = _get_tool_map()
    for tool_name, tool in tool_map.items():
        assert tool.annotations is not None, (
            f"Tool '{tool_name}' is missing annotations"
        )
        assert tool.annotations.title is not None, (
            f"Tool '{tool_name}' is missing title annotation"
        )
        assert tool.annotations.readOnlyHint is not None, (
            f"Tool '{tool_name}' is missing readOnlyHint annotation"
        )
        assert tool.annotations.destructiveHint is not None, (
            f"Tool '{tool_name}' is missing destructiveHint annotation"
        )
