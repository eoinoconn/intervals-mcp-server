"""
Wellness-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete wellness data.
"""

from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import (
    WELLNESS_FIELDS,
    deep_strip_nulls,
)
from intervals_mcp_server.utils.validation import resolve_athlete_id, resolve_date_params

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()


@mcp.tool()
async def get_wellness_data(
    athlete_id: str | None = None,
    api_key: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    fields: list[str] | None = None,
    cadence: int | None = None,
) -> Any:
    """Get wellness data for an athlete from Intervals.icu

    Args:
        athlete_id: The Intervals.icu athlete ID (optional, will use ATHLETE_ID from .env if not provided)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
        fields: List of wellness sections to include (optional, defaults to all).
            Valid values: "training", "sport_info", "vital_signs", "sleep",
            "menstrual", "subjective", "nutrition", "activity".
        cadence: Return every Nth day of data (optional). For example, cadence=7
            returns one entry per week. Must be a positive integer.
    """
    # Resolve athlete ID and date parameters
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return {"error": error_msg}

    start_date, end_date = resolve_date_params(start_date, end_date)

    # Validate fields parameter
    fields_set: set[str] | None = None
    if fields:
        invalid = set(fields) - WELLNESS_FIELDS
        if invalid:
            return {
                "error": f"Invalid field(s): {', '.join(sorted(invalid))}. "
                f"Valid fields: {', '.join(sorted(WELLNESS_FIELDS))}"
            }
        fields_set = set(fields)

    # Validate cadence parameter
    if cadence is not None and cadence < 1:
        return {"error": "Cadence must be a positive integer (1 or greater)."}

    # Call the Intervals.icu API
    params = {"oldest": start_date, "newest": end_date}

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness", api_key=api_key, params=params
    )

    if isinstance(result, dict) and "error" in result:
        return {"error": f"Error fetching wellness data: {result.get('message')}"}

    # Format the response
    if not result:
        return {
            "error": f"No wellness data found for athlete {athlete_id_to_use} in the specified date range."
        }

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
    if cadence is not None and cadence > 1:
        entries = entries[::cadence]

    # Filter to requested field sections if specified
    if fields_set:
        entries = [_filter_wellness_fields(e, fields_set) for e in entries]

    return [deep_strip_nulls(e) for e in entries]


# Mapping from field section names to the API keys they include
_WELLNESS_SECTION_KEYS: dict[str, set[str]] = {
    "training": {"ctl", "atl", "rampRate", "ctlLoad", "atlLoad"},
    "sport_info": {"sportInfo"},
    "vital_signs": {
        "weight", "restingHR", "hrv", "hrvSDNN", "avgSleepingHR", "spO2",
        "systolic", "diastolic", "respiration", "bloodGlucose", "lactate",
        "vo2max", "bodyFat", "abdomen", "baevskySI", "hrvRMSSD",
    },
    "sleep": {"sleepSecs", "sleepHours", "sleepQuality", "sleepScore", "readiness"},
    "menstrual": {"menstrualPhase", "menstrualPhasePredicted"},
    "subjective": {"soreness", "fatigue", "stress", "mood", "motivation", "injury"},
    "nutrition": {"kcalConsumed", "hydrationVolume", "hydration"},
    "activity": {"steps"},
}

# Keys always included regardless of field filter
_WELLNESS_ALWAYS_KEYS: set[str] = {"id", "date", "comments", "locked"}


def _filter_wellness_fields(entry: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    """Filter a wellness entry to only include keys from the specified field sections."""
    allowed_keys = set(_WELLNESS_ALWAYS_KEYS)
    for section in fields:
        allowed_keys.update(_WELLNESS_SECTION_KEYS.get(section, set()))
    return {k: v for k, v in entry.items() if k in allowed_keys}
