"""Data update coordinator for PiggyTask."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    PiggyTaskApiClient,
    PiggyTaskAuthError,
    PiggyTaskConnectionError,
    TaskCountsResult,
    TaskItem,
)
from .const import CONF_API_TOKEN, CONF_BASE_URL, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PiggyTaskCoordinator(DataUpdateCoordinator[TaskCountsResult]):
    """Polls the task-counts endpoint on UPDATE_INTERVAL."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        session = async_get_clientsession(hass)
        self.client = PiggyTaskApiClient(
            session, entry.data[CONF_BASE_URL], entry.data[CONF_API_TOKEN]
        )

    async def _async_update_data(self) -> TaskCountsResult:
        try:
            return await self.client.async_get_task_counts()
        except PiggyTaskAuthError as err:
            raise ConfigEntryAuthFailed("PiggyTask API token is invalid or revoked") from err
        except PiggyTaskConnectionError as err:
            raise UpdateFailed(str(err)) from err


class PiggyTaskTasksCoordinator(DataUpdateCoordinator[list[TaskItem]]):
    """Polls open tasks for the todo platform. Only set up when the token has task access."""

    def __init__(self, hass: HomeAssistant, client: PiggyTaskApiClient) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN}_tasks", update_interval=UPDATE_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> list[TaskItem]:
        try:
            return await self.client.async_get_tasks()
        except PiggyTaskAuthError as err:
            raise ConfigEntryAuthFailed(
                "PiggyTask API token no longer has task read access"
            ) from err
        except PiggyTaskConnectionError as err:
            raise UpdateFailed(str(err)) from err
