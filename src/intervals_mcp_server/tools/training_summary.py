"""
Training summary MCP tool for Intervals.icu.

This module provides a compact, coaching-ready training snapshot for a given
date range by aggregating data from four concurrent API calls:
athlete-summary, activities, wellness, and events.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, TypedDict

from mcp.types import ToolAnnotations

from intervals_mcp_server.api.client import make_intervals_request
from intervals_mcp_server.config import get_config
from intervals_mcp_server.utils.formatting import set_if, strip_nulls
from intervals_mcp_server.utils.dates import get_default_future_end_date, get_default_start_date
from intervals_mcp_server.utils.validation import resolve_athlete_id, validate_date

# Import mcp instance from shared module for tool registration
from intervals_mcp_server.mcp_instance import mcp  # noqa: F401

config = get_config()

# Event categories that are not training sessions
_NON_TRAINING_CATEGORIES = {"HOLIDAY", "NOTE"}


class _SportAgg(TypedDict):
    """Accumulator for per-sport totals within a planned week."""

    count: int
    tss: float
    duration_secs: int
    distance_m: float


class _PeriodSportAgg(TypedDict):
    """Accumulator for per-sport totals across a summary period."""

    count: int
    tss: float
    duration_secs: int
    distance_m: float
    elevation_m: float


def _round1(value: Any) -> float | None:
    """Round a numeric value to 1 decimal place, returning None for non-numeric."""
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def _round2(value: Any) -> float | None:
    """Round a numeric value to 2 decimal places, returning None for non-numeric."""
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _build_planned_summary(
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate a list of training events for one week into a planned summary.

    Non-training events (holidays, notes) are excluded.
    """
    sessions = 0
    tss = 0.0
    duration = 0
    distance = 0.0
    sport_agg: dict[str, _SportAgg] = {}

    for ev in events:
        cat = (ev.get("category") or "").upper()
        if cat in _NON_TRAINING_CATEGORIES:
            continue

        sessions += 1
        tss += ev.get("icu_training_load", 0) or 0
        duration += ev.get("moving_time", 0) or 0
        distance += ev.get("distance", 0) or 0

        sport = ev.get("type") or ev.get("category") or "Other"
        agg = sport_agg.setdefault(sport, {"count": 0, "tss": 0.0,
                                            "duration_secs": 0, "distance_m": 0.0})
        agg["count"] += 1
        agg["tss"] += ev.get("icu_training_load", 0) or 0
        agg["duration_secs"] += ev.get("moving_time", 0) or 0
        agg["distance_m"] += ev.get("distance", 0) or 0

    by_sport: dict[str, dict[str, Any]] = {}
    for name, a in sport_agg.items():
        sport_entry: dict[str, Any] = {
            "count": int(a["count"]),
            "tss": _round1(a["tss"]),
            "duration_secs": int(a["duration_secs"]),
        }
        set_if(sport_entry, "distance_m", a["distance_m"], positive=True, transform=_round1)
        by_sport[name] = strip_nulls(sport_entry)

    result: dict[str, Any] = {
        "sessions": sessions,
        "tss": _round1(tss),
        "duration_secs": duration,
    }
    set_if(result, "distance_m", distance, positive=True, transform=_round1)
    if by_sport:
        result["by_sport"] = by_sport
    return strip_nulls(result)


def _group_events_by_week(
    events: list[dict[str, Any]],
    summary_weeks: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group events into week buckets keyed by week_start date string.

    Uses the week boundaries from summary_weeks (each has a 'date' field
    representing the week start, with weeks spanning 7 days).
    """
    # Build a sorted list of week start dates
    week_starts = sorted(
        datetime.strptime(w["date"], "%Y-%m-%d").date()
        for w in summary_weeks
        if w.get("date")
    )
    grouped: dict[str, list[dict[str, Any]]] = {
        ws.strftime("%Y-%m-%d"): [] for ws in week_starts
    }

    for ev in events:
        date_str = ev.get("start_date_local", "")
        if not date_str:
            continue
        try:
            ev_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        # Find which week this event belongs to
        for ws in reversed(week_starts):
            we = ws + timedelta(days=6)
            if ws <= ev_date <= we:
                grouped[ws.strftime("%Y-%m-%d")].append(ev)
                break

    return grouped


def _build_by_sport(
    categories: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build a by_sport dict from the byCategory list of an athlete-summary week."""
    result: dict[str, dict[str, Any]] = {}
    for cat in categories:
        name = cat.get("category")
        if not name:
            continue
        sport: dict[str, Any] = {
            "count": cat.get("count", 0),
            "tss": _round1(cat.get("training_load")),
            "duration_secs": cat.get("time", 0),
        }
        set_if(sport, "distance_m", cat.get("distance"), positive=True, transform=_round1)
        set_if(sport, "elevation_m", cat.get("total_elevation_gain"), positive=True, transform=_round1)
        set_if(sport, "eftp_w", cat.get("eftp"), transform=_round1)
        set_if(sport, "eftp_w_kg", cat.get("eftpPerKg"), transform=_round1)

        result[name] = strip_nulls(sport)
    return result


def _build_period_totals(
    weeks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate period totals across all weeks."""
    sessions = 0
    duration = 0
    tss = 0.0
    srpe = 0.0
    distance = 0.0
    elevation = 0.0
    sport_agg: dict[str, _PeriodSportAgg] = {}

    for w in weeks:
        sessions += w.get("count", 0)
        duration += w.get("time", 0)
        tss += w.get("training_load", 0) or 0
        srpe += w.get("srpe", 0) or 0
        distance += w.get("distance", 0) or 0
        elevation += w.get("total_elevation_gain", 0) or 0

        for cat in w.get("byCategory", []):
            name = cat.get("category")
            if not name:
                continue
            agg = sport_agg.setdefault(name, {"count": 0, "tss": 0.0, "duration_secs": 0,
                                               "distance_m": 0.0, "elevation_m": 0.0})
            agg["count"] += cat.get("count", 0)
            agg["tss"] += cat.get("training_load", 0) or 0
            agg["duration_secs"] += cat.get("time", 0)
            agg["distance_m"] += cat.get("distance", 0) or 0
            agg["elevation_m"] += cat.get("total_elevation_gain", 0) or 0

    by_sport: dict[str, dict[str, Any]] = {}
    for name, agg in sport_agg.items():
        sport: dict[str, Any] = {
            "count": int(agg["count"]),
            "tss": _round1(agg["tss"]),
            "duration_secs": int(agg["duration_secs"]),
        }
        set_if(sport, "distance_m", agg["distance_m"], positive=True, transform=_round1)
        set_if(sport, "elevation_m", agg["elevation_m"], positive=True, transform=_round1)
        by_sport[name] = strip_nulls(sport)

    totals: dict[str, Any] = {
        "sessions": sessions,
        "duration_secs": duration,
        "tss": _round1(tss),
        "srpe": _round1(srpe),
    }
    set_if(totals, "distance_m", distance, positive=True, transform=_round1)
    set_if(totals, "elevation_m", elevation, positive=True, transform=_round1)
    if by_sport:
        totals["by_sport"] = by_sport

    return strip_nulls(totals)


def _compute_weekly_compliance(
    activities: list[dict[str, Any]],
    week_start: str,
    week_end: str,
) -> int | None:
    """Compute average compliance for activities in a given week that have compliance."""
    ws = datetime.strptime(week_start, "%Y-%m-%d").date()
    we = datetime.strptime(week_end, "%Y-%m-%d").date()

    compliance_values: list[float] = []
    for act in activities:
        # Activities have start_date_local like "2026-03-09T08:00:00"
        date_str = act.get("start_date_local", "")
        if not date_str:
            continue
        try:
            act_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if ws <= act_date <= we:
            comp = act.get("compliance")
            if comp is not None:
                try:
                    compliance_values.append(float(comp))
                except (TypeError, ValueError):
                    pass

    if not compliance_values:
        return None
    return round(sum(compliance_values) / len(compliance_values))


def _compute_weekly_wellness(
    wellness_data: list[dict[str, Any]],
    week_start: str,
    week_end: str,
) -> dict[str, float]:
    """Average wellness metrics for days within the given week."""
    ws = datetime.strptime(week_start, "%Y-%m-%d").date()
    we = datetime.strptime(week_end, "%Y-%m-%d").date()

    # Mapping from API field names to output keys
    field_map = {
        "hrvRMSSD": "hrv",
        "restingHR": "resting_hr_bpm",
        "sleepSecs": "_sleep_secs",
        "fatigue": "fatigue",
        "mood": "mood",
    }

    sums: dict[str, float] = {}
    counts: dict[str, int] = {}

    for entry in wellness_data:
        date_str = entry.get("id") or entry.get("date", "")
        if not date_str:
            continue
        try:
            d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        if ws <= d <= we:
            for api_field, out_key in field_map.items():
                val = entry.get(api_field)
                if val is not None:
                    try:
                        sums[out_key] = sums.get(out_key, 0.0) + float(val)
                        counts[out_key] = counts.get(out_key, 0) + 1
                    except (TypeError, ValueError):
                        pass

    result: dict[str, float] = {}
    for key in sums:
        avg = sums[key] / counts[key]
        if key == "_sleep_secs":
            # Convert average sleep seconds to hours
            result["sleep_hrs"] = round(avg / 3600, 1)
        else:
            result[key] = round(avg, 1)
    return result


def _build_weeks(
    summary_weeks: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    wellness_data: list[dict[str, Any]],
    events_by_week: dict[str, list[dict[str, Any]]],
    today: datetime,
) -> list[dict[str, Any]]:
    """Build the per-week breakdown from athlete-summary data.

    Past weeks have both ``planned`` and ``completed`` sections.
    Future weeks have only a ``planned`` section.
    The current (partial) week has both.
    """
    result: list[dict[str, Any]] = []
    today_date = today.date()

    for w in summary_weeks:
        date_str = w.get("date", "")
        if not date_str:
            continue

        week_start_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
        week_end_dt = week_start_dt + timedelta(days=6)
        week_start = date_str
        week_end = week_end_dt.strftime("%Y-%m-%d")

        is_future = week_start_dt > today_date
        partial = not is_future and week_end_dt > today_date

        week: dict[str, Any] = {
            "week_start": week_start,
            "week_end": week_end,
        }

        if partial:
            week["partial"] = True

        # --- Planned section (from events) ---
        week_events = events_by_week.get(week_start, [])
        if week_events:
            planned = _build_planned_summary(week_events)
            if planned.get("sessions", 0) > 0:
                week["planned"] = planned

            # --- Holiday / Note annotations ---
            for ev in week_events:
                cat = (ev.get("category") or "").upper()
                if cat == "HOLIDAY":
                    date_str = ev.get("start_date_local", "")
                    holiday_date = date_str[:10] if date_str else None
                    if holiday_date:
                        week.setdefault("holiday", []).append(holiday_date)
                elif cat == "NOTE":
                    note_text = ev.get("name") or ev.get("description") or ""
                    if note_text:
                        week.setdefault("notes", []).append(note_text)

        # --- Completed section (only for past / current weeks) ---
        if not is_future:
            completed: dict[str, Any] = {
                "sessions": w.get("count", 0),
                "tss": _round1(w.get("training_load")),
                "srpe": _round1(w.get("srpe")),
                "duration_secs": w.get("time", 0),
            }

            # Compliance (from activities)
            compliance = _compute_weekly_compliance(activities, week_start, week_end)
            if compliance is not None:
                completed["compliance_pct"] = compliance

            # By sport
            by_cat = w.get("byCategory", [])
            if by_cat:
                completed["by_sport"] = _build_by_sport(by_cat)

            week["completed"] = strip_nulls(completed)

        # --- Load metrics (available for all weeks) ---
        week["ramp_rate"] = _round1(w.get("rampRate"))
        week["ctl"] = _round1(w.get("fitness"))
        week["atl"] = _round1(w.get("fatigue"))
        week["tsb"] = _round1(w.get("form"))

        # Wellness (only for past / current weeks)
        if not is_future:
            wellness = _compute_weekly_wellness(wellness_data, week_start, week_end)
            if wellness:
                week["wellness"] = wellness

        # Strip nulls
        result.append(strip_nulls(week))

    return result


def _build_result(
    summary_weeks: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    wellness_data: list[dict[str, Any]],
    events: list[dict[str, Any]],
    start_date: str,
    end_date: str,
    today: datetime,
) -> dict[str, Any]:
    """Build the complete training summary result dict."""
    if not summary_weeks:
        return {"period": {"start": start_date, "end": end_date}}

    oldest = summary_weeks[0]
    newest = summary_weeks[-1]

    start_ctl = _round1(oldest.get("fitness"))
    start_atl = _round1(oldest.get("fatigue"))
    start_tsb = _round1(oldest.get("form"))

    current_ctl = _round1(newest.get("fitness"))
    current_atl = _round1(newest.get("fatigue"))
    current_tsb = _round1(newest.get("form"))

    ac_ratio = None
    if current_atl is not None and current_ctl is not None and current_ctl != 0:
        ac_ratio = _round2(current_atl / current_ctl)

    load: dict[str, Any] = {
        "start": strip_nulls({"ctl": start_ctl, "atl": start_atl, "tsb": start_tsb}),
        "end": strip_nulls({"ctl": current_ctl, "atl": current_atl, "tsb": current_tsb}),
    }
    if ac_ratio is not None:
        load["ac_ratio"] = ac_ratio

    events_by_week = _group_events_by_week(events, summary_weeks)

    result: dict[str, Any] = {
        "period": {"start": start_date, "end": end_date},
        "load": strip_nulls(load),
        "period_totals": _build_period_totals(summary_weeks),
        "weeks": _build_weeks(summary_weeks, activities, wellness_data, events_by_week, today),
    }

    return strip_nulls(result)


@mcp.tool(annotations=ToolAnnotations(title="Get Training Summary", readOnlyHint=True, destructiveHint=False))
async def get_training_summary(
    start_date: str | None = None,
    end_date: str | None = None,
    athlete_id: str | None = None,
    api_key: str | None = None,
) -> str:
    """
    Returns a compact JSON training snapshot for the given date range.

    Covers both past and future training. Past weeks include planned events
    alongside completed activity data with compliance. Future weeks show
    only planned events. Load metrics (CTL/ATL/TSB) are available for all
    weeks including projected values for future weeks.

    Intended as the first call in any coaching conversation to establish
    training context before making recommendations.

    Args:
        start_date: Start date in YYYY-MM-DD format (optional, defaults to 30 days ago)
        end_date: End date in YYYY-MM-DD format (optional, defaults to 30 days from now)
        athlete_id: Intervals.icu athlete ID (optional, falls back to ATHLETE_ID env var)
        api_key: Intervals.icu API key (optional, falls back to API_KEY env var)
    """
    # Resolve athlete ID
    athlete_id_to_use, error_msg = resolve_athlete_id(athlete_id, config.athlete_id)
    if error_msg:
        return error_msg

    # Resolve dates (default: 30 days back, 30 days forward)
    if not start_date:
        start_date = get_default_start_date()
    if not end_date:
        end_date = get_default_future_end_date()

    # Validate dates
    try:
        validate_date(start_date)
        validate_date(end_date)
    except ValueError as e:
        return f"Error: {e}"

    # Four concurrent API calls
    summary_coro = make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/athlete-summary",
        api_key=api_key,
        params={"start": start_date, "end": end_date},
    )
    activities_coro = make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/activities",
        api_key=api_key,
        params={"oldest": start_date, "newest": end_date},
    )
    wellness_coro = make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/wellness",
        api_key=api_key,
        params={"oldest": start_date, "newest": end_date},
    )
    events_coro = make_intervals_request(
        url=f"/athlete/{athlete_id_to_use}/events",
        api_key=api_key,
        params={"oldest": start_date, "newest": end_date},
    )

    summary_raw, activities_raw, wellness_raw, events_raw = await asyncio.gather(
        summary_coro, activities_coro, wellness_coro, events_coro
    )

    # Handle errors from any of the calls
    for label, raw in [("athlete-summary", summary_raw), ("activities", activities_raw),
                       ("wellness", wellness_raw), ("events", events_raw)]:
        if isinstance(raw, dict) and "error" in raw:
            return f"Error fetching {label}: {raw.get('message', 'Unknown error')}"

    # Normalise to lists
    summary_weeks: list[dict[str, Any]] = (
        summary_raw if isinstance(summary_raw, list) else []
    )
    activities_list: list[dict[str, Any]] = (
        activities_raw if isinstance(activities_raw, list) else []
    )
    wellness_list: list[dict[str, Any]] = (
        wellness_raw if isinstance(wellness_raw, list) else []
    )
    events_list: list[dict[str, Any]] = (
        events_raw if isinstance(events_raw, list) else []
    )

    # Sort athlete-summary into chronological order by week date
    summary_weeks.sort(key=lambda w: w.get("date", ""))

    today = datetime.now()
    result = _build_result(summary_weeks, activities_list, wellness_list,
                           events_list, start_date, end_date, today)

    return json.dumps(result, separators=(",", ":"))
