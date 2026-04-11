# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-06-01

### Added

- Initial release of Intervals.icu MCP Server.
- Activity tools: `get_activities`, `get_activity_details`, `get_activity_intervals`,
  `get_activity_streams`, `get_activity_histogram`, `get_activity_messages`,
  `add_activity_message`.
- Event tools: `get_events`, `get_event_by_id`, `add_or_update_event`, `delete_event`,
  `delete_events_by_date_range`.
- Wellness & training tools: `get_wellness_data`, `get_training_summary`,
  `get_athlete_power_curves`, `get_athlete_zones`.
- Custom-item tools: `get_custom_items`, `get_custom_item_by_id`, `create_custom_item`,
  `update_custom_item`, `delete_custom_item`.
- Docker support with Render deployment guide.
- Local setup via `uv` and `mcp` CLI.
