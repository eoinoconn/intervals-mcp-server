"""
Formatting utilities for Intervals.icu MCP Server

This module contains formatting functions for handling data from the Intervals.icu API.
"""

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any


def strip_nulls(d: dict[str, Any]) -> dict[str, Any]:
    """Remove keys whose values are None or empty collections.

    Zero values are preserved — only ``None`` and empty lists/dicts are
    stripped.
    """
    out: dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            continue
        if isinstance(v, (list, dict)) and not v:
            continue
        out[k] = v
    return out


def set_if(
    target: dict[str, Any],
    key: str,
    value: Any,
    *,
    positive: bool = False,
    transform: Callable[[Any], Any] | None = None,
) -> None:
    """Conditionally set ``target[key]`` based on *value*.

    By default the key is set when *value* is not ``None``.  With
    ``positive=True`` the value must also satisfy ``> 0``.

    *transform* is applied before storing; if the result is ``None``
    the key is not set.
    """
    if value is None:
        return
    if positive and not (value > 0):
        return
    result = transform(value) if transform else value
    if result is not None:
        target[key] = result


# Valid field names for wellness entry filtering
WELLNESS_FIELDS: set[str] = {
    "training",
    "sport_info",
    "vital_signs",
    "sleep",
    "menstrual",
    "subjective",
    "nutrition",
    "activity",
}


def _get_activity_value(activity: dict[str, Any], *keys: str) -> Any:
    """Get the first non-None value from a series of activity keys."""
    for key in keys:
        val = activity.get(key)
        if val is not None:
            return val
    return None


def _add_field(lines: list[str], label: str, value: Any, unit: str = "") -> None:
    """Append a formatted field line only if value is not None."""
    if value is not None:
        suffix = f" {unit}" if unit else ""
        lines.append(f"  {label}: {value}{suffix}")


def _add_section(lines: list[str], heading: str, section_lines: list[str]) -> None:
    """Append a section with heading only if it has content."""
    if section_lines:
        lines.append(heading)
        lines.extend(section_lines)


def format_activity_summary(activity: dict[str, Any]) -> str:
    """Format an activity into a readable string, omitting fields with no data."""
    start_time = activity.get("startTime", activity.get("start_date", "Unknown"))

    if isinstance(start_time, str) and len(start_time) > 10:
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            start_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    rpe = activity.get("perceived_exertion") or activity.get("icu_rpe")
    if isinstance(rpe, (int, float)):
        rpe = f"{rpe}/10"

    feel = activity.get("feel")
    if isinstance(feel, int):
        feel = f"{feel}/5"

    # Header - always present
    lines = [
        f"Activity: {activity.get('name', 'Unnamed')}",
        f"  ID: {activity.get('id', 'N/A')}",
        f"  Type: {activity.get('type', 'Unknown')}",
        f"  Date: {start_time}",
    ]
    if activity.get("description"):
        lines.append(f"  Description: {activity['description']}")

    # Core metrics - always include if present
    distance = activity.get("distance")
    duration = activity.get("duration") or activity.get("elapsed_time")
    moving_time = activity.get("moving_time")
    if distance:
        lines.append(f"  Distance: {distance} m")
    if duration:
        lines.append(f"  Duration: {duration}s")
    if moving_time and moving_time != duration:
        lines.append(f"  Moving Time: {moving_time}s")
    elev_gain = _get_activity_value(activity, "elevationGain", "total_elevation_gain")
    if elev_gain:
        lines.append(f"  Elevation Gain: {elev_gain} m")

    # Power
    power_lines: list[str] = []
    avg_power = _get_activity_value(activity, "avgPower", "icu_average_watts", "average_watts")
    _add_field(power_lines, "Avg Power", avg_power, "W")
    _add_field(power_lines, "Weighted Avg", activity.get("icu_weighted_avg_watts"), "W")
    tl = _get_activity_value(activity, "trainingLoad", "icu_training_load")
    _add_field(power_lines, "Training Load", tl)
    _add_field(power_lines, "FTP", activity.get("icu_ftp"), "W")
    _add_field(power_lines, "Intensity", activity.get("icu_intensity"))
    _add_field(power_lines, "Variability Index", activity.get("icu_variability_index"))
    _add_field(power_lines, "Power:HR", activity.get("icu_power_hr"))
    _add_section(lines, "  Power:", power_lines)

    # Heart Rate
    hr_lines: list[str] = []
    avg_hr = _get_activity_value(activity, "avgHr", "average_heartrate")
    _add_field(hr_lines, "Avg HR", avg_hr, "bpm")
    _add_field(hr_lines, "Max HR", activity.get("max_heartrate"), "bpm")
    _add_field(hr_lines, "LTHR", activity.get("lthr"), "bpm")
    _add_field(hr_lines, "Resting HR", activity.get("icu_resting_hr"), "bpm")
    _add_field(hr_lines, "Decoupling", activity.get("decoupling"))
    _add_section(lines, "  HR:", hr_lines)

    # Other metrics - only non-None
    other_lines: list[str] = []
    _add_field(other_lines, "Cadence", activity.get("average_cadence"), "rpm")
    _add_field(other_lines, "Calories", activity.get("calories"))
    _add_field(other_lines, "Avg Speed", activity.get("average_speed"), "m/s")
    _add_field(other_lines, "Avg Stride", activity.get("average_stride"))
    _add_field(other_lines, "L/R Balance", activity.get("avg_lr_balance"))
    _add_field(other_lines, "Weight", activity.get("icu_weight"), "kg")
    _add_field(other_lines, "RPE", rpe)
    _add_field(other_lines, "Feel", feel)
    _add_section(lines, "  Metrics:", other_lines)

    # Environment - only if any data exists
    env_lines: list[str] = []
    _add_field(env_lines, "Trainer", activity.get("trainer"))
    _add_field(env_lines, "Avg Temp", activity.get("average_temp"), "°C")
    _add_field(env_lines, "Wind", activity.get("average_wind_speed"), "km/h")
    _add_section(lines, "  Environment:", env_lines)

    # Training load metrics
    load_lines: list[str] = []
    _add_field(load_lines, "CTL", activity.get("icu_ctl"))
    _add_field(load_lines, "ATL", activity.get("icu_atl"))
    _add_field(load_lines, "TRIMP", activity.get("trimp"))
    _add_field(load_lines, "Polarization", activity.get("polarization_index"))
    _add_field(load_lines, "Power Load", activity.get("power_load"))
    _add_field(load_lines, "HR Load", activity.get("hr_load"))
    _add_field(load_lines, "Pace Load", activity.get("pace_load"))
    _add_field(load_lines, "EF", activity.get("icu_efficiency_factor"))
    _add_section(lines, "  Load:", load_lines)

    # Workout compliance - only if activity is paired with a workout
    compliance_lines: list[str] = []
    _add_field(compliance_lines, "Paired Event ID", activity.get("paired_event_id"))
    compliance = activity.get("compliance")
    if compliance is not None:
        _add_field(compliance_lines, "Compliance", f"{compliance:.2f}%")
    _add_section(lines, "  Workout Compliance:", compliance_lines)

    # Device - only if present
    device = activity.get("device_name")
    if device:
        lines.append(f"  Device: {device}")

    return "\n".join(lines)


def format_activity_compact(activity: dict[str, Any]) -> str:
    """Format an activity as a single compact line for summary listings."""
    start_time = activity.get("startTime", activity.get("start_date", ""))
    if isinstance(start_time, str) and len(start_time) > 10:
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            start_time = dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    name = activity.get("name", "Unnamed")
    act_type = activity.get("type", "?")
    act_id = activity.get("id", "")

    parts = [f"{start_time} | {act_type}: {name} (ID:{act_id})"]

    distance = activity.get("distance")
    if distance:
        parts.append(f"{distance:.0f}m")

    duration = activity.get("duration") or activity.get("elapsed_time")
    if duration:
        mins = int(duration) // 60
        parts.append(f"{mins}min")

    tl = _get_activity_value(activity, "trainingLoad", "icu_training_load")
    if tl is not None:
        parts.append(f"TL:{tl}")

    avg_hr = _get_activity_value(activity, "avgHr", "average_heartrate")
    if avg_hr is not None:
        parts.append(f"HR:{avg_hr}")

    avg_power = _get_activity_value(activity, "avgPower", "icu_average_watts", "average_watts")
    if avg_power is not None:
        parts.append(f"Pwr:{avg_power}W")

    return " | ".join(parts)


def format_workout(workout: dict[str, Any]) -> str:
    """Format a workout into a readable string."""
    return f"""
Workout: {workout.get("name", "Unnamed")}
Description: {workout.get("description", "No description")}
Sport: {workout.get("sport", "Unknown")}
Duration: {workout.get("duration", 0)} seconds
TSS: {workout.get("tss", "N/A")}
Intervals: {len(workout.get("intervals", []))}
"""


def _format_training_metrics(entries: dict[str, Any]) -> list[str]:
    """Format training metrics section."""
    training_metrics = []
    for k, label in [
        ("ctl", "Fitness (CTL)"),
        ("atl", "Fatigue (ATL)"),
        ("rampRate", "Ramp Rate"),
        ("ctlLoad", "CTL Load"),
        ("atlLoad", "ATL Load"),
    ]:
        if entries.get(k) is not None:
            training_metrics.append(f"- {label}: {entries[k]}")
    return training_metrics


def _format_sport_info(entries: dict[str, Any]) -> list[str]:
    """Format sport-specific info section."""
    sport_info_list = []
    if entries.get("sportInfo"):
        for sport in entries.get("sportInfo", []):
            if isinstance(sport, dict) and sport.get("eftp") is not None:
                sport_info_list.append(f"- {sport.get('type')}: eFTP = {sport['eftp']}")
    return sport_info_list


def _format_vital_signs(entries: dict[str, Any]) -> list[str]:
    """Format vital signs section."""
    vital_signs = []
    for k, label, unit in [
        ("weight", "Weight", "kg"),
        ("restingHR", "Resting HR", "bpm"),
        ("hrv", "HRV", ""),
        ("hrvSDNN", "HRV SDNN", ""),
        ("avgSleepingHR", "Average Sleeping HR", "bpm"),
        ("spO2", "SpO2", "%"),
        ("systolic", "Systolic BP", ""),
        ("diastolic", "Diastolic BP", ""),
        ("respiration", "Respiration", "breaths/min"),
        ("bloodGlucose", "Blood Glucose", "mmol/L"),
        ("lactate", "Lactate", "mmol/L"),
        ("vo2max", "VO2 Max", "ml/kg/min"),
        ("bodyFat", "Body Fat", "%"),
        ("abdomen", "Abdomen", "cm"),
        ("baevskySI", "Baevsky Stress Index", ""),
    ]:
        if entries.get(k) is not None:
            value = entries[k]
            if k == "systolic" and entries.get("diastolic") is not None:
                vital_signs.append(
                    f"- Blood Pressure: {entries['systolic']}/{entries['diastolic']} mmHg"
                )
            elif k not in ("systolic", "diastolic"):
                vital_signs.append(f"- {label}: {value}{(' ' + unit) if unit else ''}")
    return vital_signs


def _format_sleep_recovery(entries: dict[str, Any]) -> list[str]:
    """Format sleep and recovery section."""
    sleep_lines = []
    sleep_hours = None
    if entries.get("sleepSecs") is not None:
        sleep_hours = f"{entries['sleepSecs'] / 3600:.2f}"
    elif entries.get("sleepHours") is not None:
        sleep_hours = f"{entries['sleepHours']}"
    if sleep_hours is not None:
        sleep_lines.append(f"  Sleep: {sleep_hours} hours")

    if entries.get("sleepQuality") is not None:
        quality_value = entries["sleepQuality"]
        quality_labels = {1: "Great", 2: "Good", 3: "Average", 4: "Poor"}
        quality_text = quality_labels.get(quality_value, str(quality_value))
        sleep_lines.append(f"  Sleep Quality: {quality_value} ({quality_text})")

    if entries.get("sleepScore") is not None:
        sleep_lines.append(f"  Device Sleep Score: {entries['sleepScore']}/100")

    if entries.get("readiness") is not None:
        sleep_lines.append(f"  Readiness: {entries['readiness']}/10")

    return sleep_lines


def _format_menstrual_tracking(entries: dict[str, Any]) -> list[str]:
    """Format menstrual tracking section."""
    menstrual_lines = []
    if entries.get("menstrualPhase") is not None:
        menstrual_lines.append(f"  Menstrual Phase: {str(entries['menstrualPhase']).capitalize()}")
    if entries.get("menstrualPhasePredicted") is not None:
        menstrual_lines.append(
            f"  Predicted Phase: {str(entries['menstrualPhasePredicted']).capitalize()}"
        )
    return menstrual_lines


def _format_subjective_feelings(entries: dict[str, Any]) -> list[str]:
    """Format subjective feelings section."""
    subjective_lines = []
    for k, label in [
        ("soreness", "Soreness"),
        ("fatigue", "Fatigue"),
        ("stress", "Stress"),
        ("mood", "Mood"),
        ("motivation", "Motivation"),
        ("injury", "Injury Level"),
    ]:
        if entries.get(k) is not None:
            subjective_lines.append(f"  {label}: {entries[k]}/10")
    return subjective_lines


def _format_nutrition_hydration(entries: dict[str, Any]) -> list[str]:
    """Format nutrition and hydration section."""
    nutrition_lines = []
    for k, label in [
        ("kcalConsumed", "Calories Consumed"),
        ("hydrationVolume", "Hydration Volume"),
    ]:
        if entries.get(k) is not None:
            nutrition_lines.append(f"- {label}: {entries[k]}")

    if entries.get("hydration") is not None:
        nutrition_lines.append(f"  Hydration Score: {entries['hydration']}/10")

    return nutrition_lines


def format_wellness_entry(entries: dict[str, Any], fields: set[str] | None = None) -> str:
    """Format wellness entry data into a readable string.

    Formats various wellness metrics including training metrics, vital signs,
    sleep data, menstrual tracking, subjective feelings, nutrition, and activity.

    Args:
        entries: Dictionary containing wellness data fields such as:
            - Training metrics: ctl, atl, rampRate, ctlLoad, atlLoad
            - Vital signs: weight, restingHR, hrv, hrvSDNN, avgSleepingHR, spO2,
              systolic, diastolic, respiration, bloodGlucose, lactate, vo2max,
              bodyFat, abdomen, baevskySI
            - Sleep: sleepSecs, sleepHours, sleepQuality, sleepScore, readiness
            - Menstrual: menstrualPhase, menstrualPhasePredicted
            - Subjective: soreness, fatigue, stress, mood, motivation, injury
            - Nutrition: kcalConsumed, hydrationVolume, hydration
            - Activity: steps
            - Other: comments, locked, date
        fields: Optional set of section names to include. If None or empty,
            all sections are included. Valid values: "training", "sport_info",
            "vital_signs", "sleep", "menstrual", "subjective", "nutrition",
            "activity".

    Returns:
        A formatted string representation of the wellness entry.
    """
    include_all = not fields
    lines = ["Wellness Data:"]
    lines.append(f"Date: {entries.get('id', 'N/A')}")
    lines.append("")

    if include_all or "training" in fields:  # type: ignore[operator]
        training_metrics = _format_training_metrics(entries)
        if training_metrics:
            lines.append("Training Metrics:")
            lines.extend(training_metrics)
            lines.append("")

    if include_all or "sport_info" in fields:  # type: ignore[operator]
        sport_info_list = _format_sport_info(entries)
        if sport_info_list:
            lines.append("Sport-Specific Info:")
            lines.extend(sport_info_list)
            lines.append("")

    if include_all or "vital_signs" in fields:  # type: ignore[operator]
        vital_signs = _format_vital_signs(entries)
        if vital_signs:
            lines.append("Vital Signs:")
            lines.extend(vital_signs)
            lines.append("")

    if include_all or "sleep" in fields:  # type: ignore[operator]
        sleep_lines = _format_sleep_recovery(entries)
        if sleep_lines:
            lines.append("Sleep & Recovery:")
            lines.extend(sleep_lines)
            lines.append("")

    if include_all or "menstrual" in fields:  # type: ignore[operator]
        menstrual_lines = _format_menstrual_tracking(entries)
        if menstrual_lines:
            lines.append("Menstrual Tracking:")
            lines.extend(menstrual_lines)
            lines.append("")

    if include_all or "subjective" in fields:  # type: ignore[operator]
        subjective_lines = _format_subjective_feelings(entries)
        if subjective_lines:
            lines.append("Subjective Feelings:")
            lines.extend(subjective_lines)
            lines.append("")

    if include_all or "nutrition" in fields:  # type: ignore[operator]
        nutrition_lines = _format_nutrition_hydration(entries)
        if nutrition_lines:
            lines.append("Nutrition & Hydration:")
            lines.extend(nutrition_lines)
            lines.append("")

    if include_all or "activity" in fields:  # type: ignore[operator]
        if entries.get("steps") is not None:
            lines.append("Activity:")
            lines.append(f"- Steps: {entries['steps']}")
            lines.append("")

    if entries.get("comments"):
        lines.append(f"Comments: {entries['comments']}")
    if "locked" in entries:
        lines.append(f"Status: {'Locked' if entries.get('locked') else 'Unlocked'}")

    return "\n".join(lines)


def format_event_summary(event: dict[str, Any]) -> str:
    """Format a basic event summary into a readable string."""

    # Update to check for "date" if "start_date_local" is not provided
    event_date = event.get("start_date_local", event.get("date", "Unknown"))
    event_type = "Workout" if event.get("workout") else "Race" if event.get("race") else "Other"
    event_name = event.get("name", "Unnamed")
    event_id = event.get("id", "N/A")
    event_desc = event.get("description", "No description")

    return f"""Date: {event_date}
ID: {event_id}
Type: {event_type}
Name: {event_name}
Description: {event_desc}"""


def format_event_details(event: dict[str, Any]) -> str:
    """Format detailed event information into a readable string."""

    event_details = f"""Event Details:

ID: {event.get("id", "N/A")}
Date: {event.get("date", "Unknown")}
Name: {event.get("name", "Unnamed")}
Description: {event.get("description", "No description")}"""

    # Check if it's a workout-based event
    if "workout" in event and event["workout"]:
        workout = event["workout"]
        event_details += f"""

Workout Information:
Workout ID: {workout.get("id", "N/A")}
Sport: {workout.get("sport", "Unknown")}
Duration: {workout.get("duration", 0)} seconds
TSS: {workout.get("tss", "N/A")}"""

        # Include interval count if available
        if "intervals" in workout and isinstance(workout["intervals"], list):
            event_details += f"""
Intervals: {len(workout["intervals"])}"""

    # Check if it's a race
    if event.get("race"):
        event_details += f"""

Race Information:
Priority: {event.get("priority", "N/A")}
Result: {event.get("result", "N/A")}"""

    # Include calendar information
    if "calendar" in event:
        cal = event["calendar"]
        event_details += f"""

Calendar: {cal.get("name", "N/A")}"""

    return event_details


def format_custom_item_details(item: dict[str, Any]) -> str:
    """Format detailed custom item information into a readable string."""
    lines = ["Custom Item Details:", ""]
    lines.append(f"ID: {item.get('id', 'N/A')}")
    lines.append(f"Name: {item.get('name', 'N/A')}")
    lines.append(f"Type: {item.get('type', 'N/A')}")

    if item.get("description"):
        lines.append(f"Description: {item['description']}")
    if item.get("visibility"):
        lines.append(f"Visibility: {item['visibility']}")
    if item.get("index") is not None:
        lines.append(f"Index: {item['index']}")
    if item.get("hide_script") is not None:
        lines.append(f"Hide Script: {item['hide_script']}")
    if item.get("content"):
        lines.append(f"Content: {json.dumps(item['content'], indent=2)}")

    return "\n".join(lines)


def format_intervals(intervals_data: dict[str, Any]) -> str:
    """Format intervals data into a readable string, omitting fields with no data.

    Args:
        intervals_data: The intervals data from the Intervals.icu API

    Returns:
        A formatted string representation of the intervals data
    """
    result = f"Intervals Analysis: ID={intervals_data.get('id', 'N/A')}\n\n"

    if "icu_intervals" in intervals_data and intervals_data["icu_intervals"]:
        for i, iv in enumerate(intervals_data["icu_intervals"], 1):
            label = iv.get("label", f"Interval {i}")
            iv_type = iv.get("type", "Unknown")
            elapsed = iv.get("elapsed_time", 0)
            dist = iv.get("distance", 0)
            header = f"[{i}] {label} ({iv_type}) {elapsed}s"
            if dist:
                header += f" {dist}m"
            result += header + "\n"

            fields: list[str] = []
            # Power
            _add_field(fields, "Avg Pwr", iv.get("average_watts"), "W")
            _add_field(fields, "Max Pwr", iv.get("max_watts"), "W")
            _add_field(fields, "W. Avg Pwr", iv.get("weighted_average_watts"), "W")
            _add_field(fields, "W/kg", iv.get("average_watts_kg"))
            _add_field(fields, "Intensity", iv.get("intensity"))
            _add_field(fields, "TL", iv.get("training_load"))
            zone = iv.get("zone")
            if zone is not None:
                z_min = iv.get("zone_min_watts", "")
                z_max = iv.get("zone_max_watts", "")
                fields.append(f"  Zone: {zone} ({z_min}-{z_max}W)")
            # HR
            _add_field(fields, "Avg HR", iv.get("average_heartrate"), "bpm")
            _add_field(fields, "Max HR", iv.get("max_heartrate"), "bpm")
            _add_field(fields, "Decoupling", iv.get("decoupling"))
            # Speed / Cadence
            _add_field(fields, "Avg Speed", iv.get("average_speed"), "m/s")
            _add_field(fields, "GAP", iv.get("gap"), "m/s")
            _add_field(fields, "Avg Cadence", iv.get("average_cadence"), "rpm")
            _add_field(fields, "Stride", iv.get("average_stride"))
            # Elevation / environment
            _add_field(fields, "Elev Gain", iv.get("total_elevation_gain"), "m")
            _add_field(fields, "Gradient", iv.get("average_gradient"), "%")
            _add_field(fields, "Temp", iv.get("average_temp"), "°C")

            if fields:
                result += "\n".join(fields) + "\n"
            result += "\n"

    if "icu_groups" in intervals_data and intervals_data["icu_groups"]:
        result += "Groups:\n"
        for i, group in enumerate(intervals_data["icu_groups"], 1):
            gid = group.get("id", f"Group {i}")
            count = group.get("count", 0)
            elapsed = group.get("elapsed_time", 0)
            dist = group.get("distance", 0)
            header = f"  {gid} ({count} intervals) {elapsed}s"
            if dist:
                header += f" {dist}m"
            result += header + "\n"

            fields = []
            _add_field(fields, "Avg Pwr", group.get("average_watts"), "W")
            _add_field(fields, "Avg HR", group.get("average_heartrate"), "bpm")
            _add_field(fields, "Avg Speed", group.get("average_speed"), "m/s")
            _add_field(fields, "Avg Cadence", group.get("average_cadence"), "rpm")
            if fields:
                result += "\n".join(fields) + "\n"
            result += "\n"

    return result


def _format_duration_label(secs: int) -> str:
    """Format seconds into a concise human-readable label (e.g. 5s, 2m, 1h)."""
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        mins = secs // 60
        remainder = secs % 60
        if remainder:
            return f"{mins}m{remainder}s"
        return f"{mins}m"
    hours = secs // 3600
    remainder = (secs % 3600) // 60
    if remainder:
        return f"{hours}h{remainder}m"
    return f"{hours}h"


def format_power_curves(
    curves: list[dict[str, Any]],
    activity_type: str,
    include_normalised: bool,
) -> str:
    """Format extracted power curve data into a concise readable string.

    Args:
        curves: List of extracted curve data dicts with id, label, data_points.
        activity_type: The activity type used for the query.
        include_normalised: Whether W/kg data is included.

    Returns:
        A formatted string representation of the power curves.
    """
    lines: list[str] = [f"Power Curves ({activity_type}):", ""]

    for curve in curves:
        label = curve.get("label", curve.get("id", "Unknown"))
        start = curve.get("start", "")
        end = curve.get("end", "")
        date_range = ""
        if start and end:
            # Trim time portion if present
            start_short = start[:10] if len(start) > 10 else start
            end_short = end[:10] if len(end) > 10 else end
            date_range = f" ({start_short} to {end_short})"

        lines.append(f"{label}{date_range}:")

        data_points = curve.get("data_points", [])
        if not data_points:
            lines.append("  No data available for requested durations.")
            lines.append("")
            continue

        for point in data_points:
            dur_label = _format_duration_label(point["secs"])
            watts = point.get("watts")
            aid = point.get("activity_id", "")
            parts = [f"  {dur_label}: {watts}W"]
            if include_normalised and "watts_per_kg" in point:
                parts.append(f"{point['watts_per_kg']:.2f}W/kg")
                wkg_aid = point.get("wkg_activity_id", "")
                if wkg_aid and wkg_aid != aid:
                    parts.append(f"[{aid}|wkg:{wkg_aid}]")
                else:
                    parts.append(f"[{aid}]")
            else:
                parts.append(f"[{aid}]")
            lines.append(" ".join(parts))
        lines.append("")

    return "\n".join(lines)
