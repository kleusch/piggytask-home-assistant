"""Data update coordinator for PiggyTask."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PiggyTaskApiClient, PiggyTaskAuthError, PiggyTaskConnectionError, TaskCountsResult
from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class PiggyTaskCoordinator(DataUpdateCoordinator[TaskCountsResult]):
    """Polls task counts and the open-task list in one request.

    One poll used to be two separately authenticated requests (counts + tasks);
    the to-do lists now read `data.tasks` from the same response.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        minutes = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES))
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=timedelta(minutes=minutes)
        )
        session = async_get_clientsession(hass)
        self.client = PiggyTaskApiClient(
            session, entry.data[CONF_BASE_URL], entry.data[CONF_API_TOKEN]
        )

    async def _async_update_data(self) -> TaskCountsResult:
        try:
            return await self.client.async_get_task_counts(include_tasks=True)
        except PiggyTaskAuthError as err:
            raise ConfigEntryAuthFailed("PiggyTask API token is invalid or revoked") from err
        except PiggyTaskConnectionError as err:
            raise UpdateFailed(str(err)) from err
