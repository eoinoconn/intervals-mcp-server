"""
Athlete-related MCP tools for Intervals.icu.

This module contains tools for retrieving athlete configuration data
such as training zone definitions.
"""

import json
from typing import Any

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.validation import resolve_athlete_id

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()

# Percentage values at or above this threshold are treated as sentinel
# "no upper limit" markers by Intervals.icu (e.g. 999%).
_SENTINEL_PCT = 900


def _build_power_zones(
    ftp: int | float,
    zone_pcts: list[int | float],
    zone_names: list[str],
) -> list[dict[str, Any]]:
    """Build power zone list from FTP and percentage boundaries.

    Args:
        ftp: Functional Threshold Power in watts.
        zone_pcts: Upper-boundary percentages of FTP for each zone.
        zone_names: Display names for each zone.

    Returns:
        List of zone dicts with name, min_w, and (optionally) max_w.
    """
    zones: list[dict[str, Any]] = []
    prev_w = 0
    for i, name in enumerate(zone_names):
        if i >= len(zone_pcts):
            break
        pct = zone_pcts[i]
        zone: dict[str, Any] = {"name": name, "min_w": prev_w}
        if pct < _SENTINEL_PCT:
            max_w = round(ftp * pct / 100)
            zone["max_w"] = max_w
            prev_w = max_w + 1
        zones.append(zone)
    return zones


def _build_hr_zones(
    hr_boundaries: list[int | float],
    zone_names: list[str],
) -> list[dict[str, Any]]:
    """Build HR zone list from absolute BPM boundaries.

    Args:
        hr_boundaries: Upper BPM boundary for each zone.
        zone_names: Display names for each zone.

    Returns:
        List of zone dicts with name, min_bpm, and max_bpm.
    """
    zones: list[dict[str, Any]] = []
    prev_bpm = 0
    for i, name in enumerate(zone_names):
        if i >= len(hr_boundaries):
            break
        max_bpm = int(hr_boundaries[i])
        zones.append({"name": name, "min_bpm": prev_bpm, "max_bpm": max_bpm})
        prev_bpm = max_bpm + 1
    return zones


def _ms_to_minkm_str(ms: float) -> str:
    """Convert m/s speed to min/km pace formatted as ``M:SS``.

    Args:
        ms: Speed in metres per second (must be > 0).

    Returns:
        Pace string in ``M:SS`` format (e.g. ``"4:35"``).
    """
    if ms <= 0:
        raise ValueError("Speed must be positive for pace conversion")
    secs_per_km = 1000.0 / ms
    minutes = int(secs_per_km // 60)
    seconds = int(round(secs_per_km % 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d}"


def _ms_to_sec100m(ms: float) -> float:
    """Convert m/s speed to seconds per 100 m.

    Args:
        ms: Speed in metres per second (must be > 0).

    Returns:
        Pace as seconds per 100 m, rounded to one decimal.
    """
    if ms <= 0:
        raise ValueError("Speed must be positive for pace conversion")
    return round(100.0 / ms, 1)


def _build_pace_zones(
    threshold_pace: float,
    zone_pcts: list[int | float],
    zone_names: list[str],
    pace_units: str | None = None,
) -> list[dict[str, Any]]:
    """Build pace zone list from threshold pace and percentage boundaries.

    When *pace_units* is ``"MINS_KM"`` or ``"SECS_100M"`` the boundaries are
    converted to human-readable values.  Otherwise raw m/s values are used.

    Args:
        threshold_pace: Threshold pace in m/s.
        zone_pcts: Upper-boundary percentages of threshold pace for each zone.
        zone_names: Display names for each zone.
        pace_units: Unit identifier from the Intervals.icu API (e.g.
            ``"MINS_KM"``, ``"SECS_100M"``).  ``None`` keeps raw m/s.

    Returns:
        List of zone dicts with name and pace boundaries in the target unit.
    """
    # Pre-compute speed boundaries (m/s) for every zone cutoff.
    speed_bounds: list[float | None] = []
    for pct in zone_pcts:
        if pct < _SENTINEL_PCT:
            speed_bounds.append(threshold_pace * pct / 100)
        else:
            speed_bounds.append(None)  # sentinel – no upper speed limit

    zones: list[dict[str, Any]] = []
    for i, name in enumerate(zone_names):
        if i >= len(speed_bounds):
            break

        zone: dict[str, Any] = {"name": name}
        fast_speed = speed_bounds[i]  # upper speed boundary (fast end)
        slow_speed = speed_bounds[i - 1] if i > 0 else None  # previous zone boundary

        if pace_units == "MINS_KM":
            if fast_speed is not None:
                zone["min_minkm"] = _ms_to_minkm_str(fast_speed)
            if slow_speed is not None:
                zone["max_minkm"] = _ms_to_minkm_str(slow_speed)
        elif pace_units == "SECS_100M":
            if fast_speed is not None:
                zone["min_sec100m"] = _ms_to_sec100m(fast_speed)
            if slow_speed is not None:
                zone["max_sec100m"] = _ms_to_sec100m(slow_speed)
        else:
            # Fallback: raw m/s format
            if slow_speed is not None:
                zone["min_ms"] = round(slow_speed + 0.01, 2)
            else:
                zone["min_ms"] = 0.0
            if fast_speed is not None:
                zone["max_ms"] = round(fast_speed, 2)

        zones.append(zone)
    return zones


def _extract_sport_zones(setting: dict[str, Any]) -> dict[str, Any]:
    """Extract zone-relevant fields from a single sport-settings entry.

    Args:
        setting: A sport-settings object from the Intervals.icu API.

    Returns:
        Compact dict with types, thresholds, and configured zone arrays.
    """
    types = setting.get("types", [])
    sport = types[0] if types else "Unknown"

    result: dict[str, Any] = {"sport": sport, "types": types}

    updated = setting.get("updated")
    if updated is not None:
        result["last_updated"] = updated

    # Thresholds
    thresholds: dict[str, Any] = {}
    ftp = setting.get("ftp")
    if ftp is not None:
        thresholds["ftp_w"] = ftp
    lthr = setting.get("lthr")
    if lthr is not None:
        thresholds["lthr_bpm"] = lthr
    max_hr = setting.get("max_hr")
    if max_hr is not None:
        thresholds["max_hr_bpm"] = max_hr
    threshold_pace = setting.get("threshold_pace")
    if threshold_pace is not None:
        thresholds["threshold_pace_ms"] = round(threshold_pace, 2)
        pace_units = setting.get("pace_units")
        if pace_units:
            thresholds["pace_units"] = pace_units
            if pace_units == "MINS_KM":
                thresholds["threshold_pace_minkm"] = _ms_to_minkm_str(threshold_pace)
            elif pace_units == "SECS_100M":
                thresholds["threshold_pace_sec100m"] = _ms_to_sec100m(threshold_pace)
    if thresholds:
        result["thresholds"] = thresholds

    # Power zones (require FTP and zone definitions)
    power_zones_pcts = setting.get("power_zones")
    power_zone_names = setting.get("power_zone_names")
    if ftp and power_zones_pcts and power_zone_names:
        result["power_zones"] = _build_power_zones(ftp, power_zones_pcts, power_zone_names)

    # HR zones (absolute BPM boundaries)
    hr_zones_vals = setting.get("hr_zones")
    hr_zone_names = setting.get("hr_zone_names")
    if hr_zones_vals and hr_zone_names:
        result["hr_zones"] = _build_hr_zones(hr_zones_vals, hr_zone_names)

    # Pace zones (require threshold pace and zone definitions)
    pace_zones_pcts = setting.get("pace_zones")
    pace_zone_names = setting.get("pace_zone_names")
    pace_units = setting.get("pace_units")
    if threshold_pace and pace_zones_pcts and pace_zone_names:
        result["pace_zones"] = _build_pace_zones(
            threshold_pace, pace_zones_pcts, pace_zone_names, pace_units
        )

    return result


@mcp.tool()
async def get_athlete_zones(
    athlete_id: str | None = None,
    api_key: str | None = None,
    sport: str | None = None,
) -> str:
    """
    Get training zone definitions for an athlete from Intervals.icu.

    Returns power zones, heart rate zones, and pace zones per sport, along
    with the thresholds they are derived from (FTP, LTHR, threshold pace).
    Useful for interpreting zone-relative metrics in activity data or for
    prescribing intensity targets in planned workouts.

    Args:
        athlete_id: Intervals.icu athlete ID (optional, falls back to ATHLETE_ID env var)
        api_key: The Intervals.icu API key (optional, will use API_KEY from .env if not provided)
        sport: Filter to a specific sport type e.g. "Run", "Ride", "Swim" (optional, returns all if omitted)
    """
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/sport-settings",
        api_key=api_key,
    )

    if isinstance(result, dict) and "error" in result:
        return f"Error fetching athlete zones: {result.get('message')}"

    if not result or not isinstance(result, list):
        return f"No sport settings found for athlete {athlete_id_to_use}."

    zones_list: list[dict[str, Any]] = []
    for setting in result:
        if not isinstance(setting, dict):
            continue
        zones = _extract_sport_zones(setting)
        zones_list.append(zones)

    # Filter by sport if specified
    if sport:
        zones_list = [z for z in zones_list if sport in z.get("types", [])]
        if not zones_list:
            return f"No zone settings found for sport '{sport}'."

    if not zones_list:
        return f"No zone settings found for athlete {athlete_id_to_use}."

    return json.dumps(zones_list, separators=(",", ":"))
