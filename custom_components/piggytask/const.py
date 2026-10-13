"""Constants for the PiggyTask integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "piggytask"
PLATFORMS = [Platform.SENSOR]
TODO_PLATFORM = Platform.TODO

CONF_API_TOKEN = "api_token"
CONF_BASE_URL = "base_url"

DEFAULT_BASE_URL = "https://app.piggytask.de"
TASK_COUNTS_PATH = "/api/integrations/home-assistant/task-counts"
TASKS_PATH = "/api/integrations/llm/tasks"
TASKS_COMPLETE_PATH = "/api/integrations/llm/tasks/complete"

# Every poll costs the PiggyTask backend a token check, a rate-limit write and
# three queries — 15 minutes is plenty for chore counters. Completing a task from
# Home Assistant refreshes right away regardless.
CONF_SCAN_INTERVAL = "scan_interval_minutes"
DEFAULT_SCAN_INTERVAL_MINUTES = 15
SCAN_INTERVAL_CHOICES_MINUTES = [5, 15, 30, 60]
