"""
Usage guide resource for the Intervals.icu MCP server.

Provides a static plain-text briefing that describes key concepts,
data type distinctions, load metric definitions, and recommended tool
workflows for common coaching questions.
"""

from intervals_mcp_server.mcp_instance import mcp

USAGE_GUIDE = """\
INTERVALS.ICU MCP SERVER — USAGE GUIDE

CONCEPTS

Activities — completed sessions uploaded from a device. Historical only.
  Types: Ride, Run, Swim, Walk, Workout, WeightTraining, VirtualRide, etc.
  Key distinction: some types (Workout, WeightTraining) contribute 0% to
  fitness (CTL) but 100% to fatigue (ATL) by design in intervals.icu.
  A week with elevated ATL and zero-TSS sport entries is correctly modelled not a data gap.

  Activity Fields:
    - `compliance` (0-100%) — how well the activity execution matched the
      planned workout prescription, if any. Only present if the activity is linked to a planned workout event.
    - `planned_workout_id` — the ID of the linked planned workout event, if any.
    - `tss` — Training Stress Score. May be 0 for activities without power or HR data, but these can still drive ATL.
    - `Polarization` — the distribution of training intensity across different zones.
    - `Intensity %` — power / FTP.
    - `Variability Index` — NP / average power. A measure of how steady vs variable the power was during the activity.
    - `Power:HR` — the ratio of normalized power to average heart rate, indicating cardiovascular efficiency.
    - `Decoupling` — the change in Power:HR ratio over the course of the activity, indicating fatigue resistance.
    - `RPE` — Rate of Perceived Exertion, a subjective measure of how hard the session felt. Higher = more difficult.
    - `Feel` - a subjective measure of how the athlete felt during the session, on a scale from 1 (Great) to 5 (Poor).
    - `TRIPM` - measure of training load derived from the average HR for the activity relative to resting HR and max HR and the moving time.

Events — items on the athlete's calendar. Three subtypes:
  - Planned workouts (future or past; have a linked activity if completed)
  - Races
  - Notes / annotations (these are common used to annotate what training phase the athlete is in)
  The `compliance` field is only present on an activity when it has an
  associated planned workout event. It measures execution vs prescription
  (0-inf%), not a session count ratio.

Wellness — one entry per day. Athlete-logged or device-synced.
  Not tied to activities. Gaps are common — always check data completeness.

Fields and Metrics:
  - Chronic Training Load (CTL/Fitness) — 42-day exponential weighted rolling avg of daily TSS
  - Acute Training Load (ATL/Fatigue) —  7-day exponential weighted rolling avg of daily TSS
  - Training Stress Balance (TSB/Form)    — CTL minus ATL. Negative = fatigued, positive = fresh
  - Acute Chronic (AC) ratio      — ATL / CTL. Training sweet spot: 0.8-1.3
  - TSS = Training Stress Score. Activities without power or HR data
    (e.g. Workout, WeightTraining) may have TSS = 0 but still drive ATL.
  - Normalized Power (NP) — the power that would produce the same physiological

Athlete Zones:
  Power zones, heart rate zones, pace zones etc. Zones are sport-specific
  and athlete-specific. Always query the current zones for the relevant
  sport before prescribing intensity targets. Intervals.icu is the single 
  source of truth for athlete zones used in training prescriptions.

RECOMMENDED WORKFLOWS

Start of any coaching conversation:
  1. get_training_summary(start_date, end_date)  ← always call first
  2. get_athlete_zones(sport)  ← if prescribing intensity targets

Analysing a completed activity:
  1. get_activities()              ← find the activity ID
  2. get_activity_details(id)      ← full metrics
  3. get_activity_intervals(id)    ← interval breakdown (if structured)

Planning / calendar management:
  1. get_events()                  ← view upcoming calendar
  2. add_or_update_event()         ← create or modify a planned workout

Reviewing a period:
  1. get_training_summary(start_date, end_date)
  2. get_wellness_data(start_date, end_date)    ← if wellness detail needed

Context efficiency:
  1. Make use of the 'compact' flags available for some tool calls to reduce 
    the burden on the context window.

AVAILABLE TOOLS

  get_training_summary      Weekly load snapshot. Start every coaching session here.
  get_athlete_zones         FTP, LTHR, zone boundaries per sport.
  get_activities            Completed session list with load metrics.
  get_activity_details      Full metrics for a single activity.
  get_activity_intervals    Interval breakdown for a structured activity.
  get_activity_streams      Raw time-series streams (power, HR, cadence etc).
  get_wellness_data         Daily wellness entries (HRV, sleep, weight etc).
  get_events                Calendar events — planned workouts, races, notes.
  get_event_by_id           Single event detail.
  add_or_update_event       Create or update a planned workout on the calendar.
  delete_event              Remove an event from the calendar.
  delete_events_by_date_range  Bulk delete events within a date range.
  get_custom_items          Athlete custom charts, fields, and zones.\
"""


@mcp.resource("intervals-icu://guide")
def coaching_context_protocol() -> str:
    """
    Usage guide for the intervals.icu MCP server. Describes key concepts,
    data type distinctions, load metric definitions, and recommended tool
    workflows for common coaching questions.
    """
    return USAGE_GUIDE
