"""
Activity-related MCP tools for Intervals.icu.

This module contains tools for retrieving and managing athlete activities.
"""

from datetime import datetime
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import (
    format_activity_message,
    format_activity_compact,
    format_activity_summary,
    format_ignore_flags,
    format_intervals,
)

from intervals_mcp_server.utils.validation import resolve_athlete_id, resolve_date_params

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


def _parse_activities_from_result(result: Any) -> list[dict[str, Any]]:
    """Extract a list of activity dictionaries from the API result."""
    activities: list[dict[str, Any]] = []

    if isinstance(result, list):
        activities = [item for item in result if isinstance(item, dict)]
    elif isinstance(result, dict):
        # Result is a single activity or a container
        for _key, value in result.items():
            if isinstance(value, list):
                activities = [item for item in value if isinstance(item, dict)]
                break
        # If no list was found but the dict has typical activity fields, treat it as a single activity
        if not activities and any(key in result for key in ["name", "startTime", "distance"]):
            activities = [result]

    return activities


def _filter_named_activities(activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out unnamed activities from the list."""
    return [
        activity
        for activity in activities
        if activity.get("name") and activity.get("name") != "Unnamed"
    ]


def _filter_activities_by_date(
    activities: list[dict[str, Any]],
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Filter activities to only include those within the specified date range.

    Args:
        activities: List of activity dictionaries.
        start_date: Start date in YYYY-MM-DD format (inclusive).
        end_date: End date in YYYY-MM-DD format (inclusive).

    Returns:
        Filtered list of activities within the date range.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return activities  # Can't filter if boundary dates are invalid

    filtered: list[dict[str, Any]] = []
    for activity in activities:
        raw = activity.get("start_date_local") or activity.get("startTime") or activity.get("start_date", "")
        if not raw:
            continue
        try:
            activity_date = datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
        except ValueError:
            continue
        if start_dt <= activity_date <= end_dt:
            filtered.append(activity)
    return filtered


def _format_activities_response(
    activities: list[dict[str, Any]],
    athlete_id: str,
    include_unnamed: bool,
    compact: bool = False,
) -> str:
    """Format the activities response based on the results."""
    if not activities:
        if include_unnamed:
            return (
                f"No valid activities found for athlete {athlete_id} in the specified date range."
            )
        return f"No named activities found for athlete {athlete_id} in the specified date range. Try with include_unnamed=True to see all activities."

    formatter = format_activity_compact if compact else format_activity_summary
    activities_summary = "Activities:\n\n"
    for activity in activities:
        if isinstance(activity, dict):
            activities_summary += formatter(activity) + "\n"

    return activities_summary


@mcp.tool()
async def get_activities(  # pylint: disable=too-many-arguments,too-many-return-statements,too-many-branches,too-many-positional-arguments
    athlete_id: str = "",
    api_key: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 10,
    include_unnamed: bool = False,
    compact: bool = True,
) -> str:
    """Get a list of activities for an athlete from Intervals.icu

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        limit: Maximum number of activities to return (optional, defaults to 10)
        include_unnamed: Whether to include unnamed activities (optional, defaults to False)
        compact: If True, return a brief one-line-per-activity summary to save tokens (optional, defaults to True)
    """
    # Resolve athlete ID and date parameters
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    start_date, end_date = resolve_date_params(start_date, end_date)

    # Fetch more activities if we need to filter out unnamed ones
    api_limit = limit * 3 if not include_unnamed else limit

    # Call the Intervals.icu API
    params = {"oldest": start_date, "newest": end_date, "limit": api_limit}
    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities", api_key=api_key, params=params
    )

    # Check for error
    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activities: {error_message}"

    if not result:
        return f"No activities found for athlete {athlete_id_to_use} in the specified date range."

    # Parse activities from result
    activities = _parse_activities_from_result(result)

    if not activities:
        return f"No valid activities found for athlete {athlete_id_to_use} in the specified date range."

    # Filter activities to the requested date range
    activities = _filter_activities_by_date(activities, start_date, end_date)

    # Filter and fetch more if needed
    if not include_unnamed:
        activities = _filter_named_activities(activities)

    # Limit to requested count
    activities = activities[:limit]

    return _format_activities_response(activities, athlete_id_to_use, include_unnamed, compact)


@mcp.tool()
async def get_activity_details(activity_id: str, api_key: str = "") -> str:
    """Get detailed information for a specific activity from Intervals.icu

    Args:
        activity_id: The Intervals.icu activity ID
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
    """
    # Call the Intervals.icu API
    result = await make_intervals_request(url=f"/activity/{activity_id}", api_key=api_key)

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activity details: {error_message}"

    # Format the response
    if not result:
        return f"No details found for activity {activity_id}."

    # If result is a list, use the first item if available
    activity_data = result[0] if isinstance(result, list) and result else result
    if not isinstance(activity_data, dict):
        return f"Invalid activity format for activity {activity_id}."

    # Return a more detailed view of the activity
    detailed_view = format_activity_summary(activity_data)

    # Add additional details if available
    if "zones" in activity_data:
        zones = activity_data["zones"]
        detailed_view += "\nPower Zones:\n"
        for zone in zones.get("power", []):
            detailed_view += f"Zone {zone.get('number')}: {zone.get('secondsInZone')} seconds\n"

        detailed_view += "\nHeart Rate Zones:\n"
        for zone in zones.get("hr", []):
            detailed_view += f"Zone {zone.get('number')}: {zone.get('secondsInZone')} seconds\n"

    return detailed_view


@mcp.tool()
async def get_activity_intervals(activity_id: str, api_key: str = "") -> str:
    """Get interval data for a specific activity from Intervals.icu

    This endpoint returns detailed metrics for each interval in an activity, including power, heart rate,
    cadence, speed, and environmental data. It also includes grouped intervals if applicable.

    Args:
        activity_id: The Intervals.icu activity ID
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
    """
    # Call the Intervals.icu API
    result = await make_intervals_request(url=f"/activity/{activity_id}/intervals", api_key=api_key)

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching intervals: {error_message}"

    # Format the response
    if not result:
        return f"No interval data found for activity {activity_id}."

    # If the result is empty or doesn't contain expected fields
    if not isinstance(result, dict) or not any(
        key in result for key in ["icu_intervals", "icu_groups"]
    ):
        return f"No interval data or unrecognized format for activity {activity_id}."

    # Fetch activity details to get ignore flags
    ignore_flags_text = ""
    activity_result = await make_intervals_request(
        url=f"/activity/{activity_id}", api_key=api_key
    )
    if isinstance(activity_result, dict) and "error" not in activity_result:
        ignore_flags_text = format_ignore_flags(activity_result)

    # Format the intervals data
    return ignore_flags_text + format_intervals(result)


@mcp.tool()
async def get_activity_streams(
    activity_id: str,
    api_key: str = "",
    stream_types: str = "",
) -> str:
    """Get stream data for a specific activity from Intervals.icu

    This endpoint returns time-series data for an activity, including metrics like power, heart rate,
    cadence, altitude, distance, temperature, and velocity data.

    Args:
        activity_id: The Intervals.icu activity ID
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        stream_types: Comma-separated list of stream types to retrieve (optional, defaults to all available types)
                     Available types: time, watts, heartrate, cadence, altitude, distance,
                     core_temperature, skin_temperature, velocity_smooth
    """
    # Build query parameters
    params = {}
    if stream_types:
        params["types"] = stream_types
    else:
        # Default to common stream types if none specified
        params["types"] = "time,watts,heartrate,cadence,altitude,distance,velocity_smooth"

    # Call the Intervals.icu API
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/streams",
        api_key=api_key,
        params=params,
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activity streams: {error_message}"

    # Format the response
    if not result:
        return f"No stream data found for activity {activity_id}."

    # Ensure result is a list
    streams = result if isinstance(result, list) else []

    if not streams:
        return f"No stream data found for activity {activity_id}."

    # Format the streams data
    streams_summary = f"Activity Streams for {activity_id}:\n\n"

    for stream in streams:
        if not isinstance(stream, dict):
            continue

        stream_type = stream.get("type", "unknown")
        stream_name = stream.get("name", stream_type)
        data = stream.get("data", [])
        value_type = stream.get("valueType", "")

        streams_summary += f"Stream: {stream_name} ({stream_type})\n"
        streams_summary += f"  Value Type: {value_type}\n"
        streams_summary += f"  Data Points: {len(data)}\n"

        # Show first few and last few data points for preview
        if data:
            if len(data) <= 10:
                streams_summary += f"  Values: {data}\n"
            else:
                preview_start = data[:5]
                preview_end = data[-5:]
                streams_summary += f"  First 5 values: {preview_start}\n"
                streams_summary += f"  Last 5 values: {preview_end}\n"

        streams_summary += "\n"

    return streams_summary


@mcp.tool()
async def get_activity_messages(activity_id: str, api_key: str = "") -> str:
    """Get messages (notes/comments) for a specific activity from Intervals.icu

    Args:
        activity_id: The Intervals.icu activity ID
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
    """
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/messages",
        api_key=api_key,
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error fetching activity messages: {error_message}"

    if not result:
        return f"No messages found for activity {activity_id}."

    messages = result if isinstance(result, list) else []
    if not messages:
        return f"No messages found for activity {activity_id}."

    output = f"Messages for activity {activity_id}:\n\n"
    for msg in messages:
        if isinstance(msg, dict):
            output += format_activity_message(msg) + "\n\n"

    return output


@mcp.tool()
async def add_activity_message(
    activity_id: str,
    content: str,
    api_key: str = "",
) -> str:
    """Add a message (note/comment) to an activity on Intervals.icu

    Args:
        activity_id: The Intervals.icu activity ID
        content: The message text to add
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
    """
    result = await make_intervals_request(
        url=f"/activity/{activity_id}/messages",
        api_key=api_key,
        method="POST",
        data={"content": content},
    )

    if isinstance(result, dict) and "error" in result:
        error_message = result.get("message", "Unknown error")
        return f"Error adding message to activity: {error_message}"

    if not result or not isinstance(result, dict):
        return "Error: Unexpected response when adding message."

    msg_id = result.get("id")
    if msg_id is not None:
        return f"Successfully added message (ID: {msg_id}) to activity {activity_id}."
    return f"Message appears to have been added to activity {activity_id}, but no ID was returned. Please verify manually."
