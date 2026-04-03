"""
Wellness-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete wellness data.
"""

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import (
    WELLNESS_FIELDS,
    format_wellness_entry,
)
from intervals_mcp_server.utils.validation import resolve_athlete_id, resolve_date_params

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool()
async def get_wellness_data(
    athlete_id: str = "",
    api_key: str = "",
    start_date: str = "",
    end_date: str = "",
    fields: list[str] | None = None,
    cadence: int = 0,
    include_all_fields: bool = False,
) -> str:
    """Get wellness data for an athlete from Intervals.icu.

    By default returns standard wellness fields (training metrics, vitals, sleep,
    subjective scores, etc.). Set include_all_fields=True to also include any
    additional or custom fields configured by the user in Intervals.icu.

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        fields: List of wellness sections to include (optional, defaults to all).
            Valid values: "training", "sport_info", "vital_signs", "sleep",
            "menstrual", "subjective", "nutrition", "activity".
        cadence: Return every Nth day of data (optional). For example, cadence=7
            returns one entry per week. Use 0 (default) to return all entries
            without cadence filtering. Must be a positive integer when provided.
        include_all_fields: If True, include additional and custom fields beyond the standard set (optional, defaults to False)
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    start_date, end_date = resolve_date_params(start_date, end_date)

    # Validate fields parameter
    fields_set: set[str] | None = None
    if fields:
        invalid = set(fields) - WELLNESS_FIELDS
        if invalid:
            return (
                f"Invalid field(s): {', '.join(sorted(invalid))}. "
                f"Valid fields: {', '.join(sorted(WELLNESS_FIELDS))}"
            )
        fields_set = set(fields)

    # Validate cadence parameter
    if cadence and cadence < 1:
        return "Cadence must be a positive integer (1 or greater) when provided. Use 0 to disable cadence filtering."

    # Call the Intervals.icu API
    params = {"oldest": start_date, "newest": end_date}

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching wellness data: {result.get('message')}"

    if not result:
        return (
            f"No wellness data found for athlete {athlete_id_to_use} in the specified date range."
        )

    # Collect entries into a flat list
    entries: list[dict] = []
    if isinstance(result, dict):
        for date_str, data in result.items():
            if isinstance(data, dict):
                if "date" not in data:
                    data["date"] = date_str
                entries.append(data)
    elif isinstance(result, list):
        entries = [e for e in result if isinstance(e, dict)]

    # Apply cadence filtering (keep every Nth entry)
    if cadence and cadence > 1:
        entries = entries[::cadence]

    wellness_summary = "Wellness Data:\n\n"
    for entry in entries:
        wellness_summary += format_wellness_entry(entry, fields=fields_set, include_all_fields=include_all_fields) + "\n\n"

    return wellness_summary
