"""Constants for the PiggyTask integration."""

from __future__ import annotations

from datetime import timedelta

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

UPDATE_INTERVAL = timedelta(minutes=5)
