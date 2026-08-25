"""The PiggyTask integration."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import PiggyTaskApiError, TaskItem
from .const import DOMAIN, PLATFORMS, TODO_PLATFORM
from .coordinator import PiggyTaskCoordinator, PiggyTaskTasksCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PiggyTask from a config entry.

    Every token can read task counts (sensors). Whether it can also list/complete
    tasks depends on the scope chosen when the token was created in PiggyTask. Both
    are fetched concurrently; a failure to list tasks degrades to counts-only
    (no todo platform) rather than failing the whole entry — only a counts failure does.
    """
    coordinator = PiggyTaskCoordinator(hass, entry)

    async def _fetch_initial_tasks() -> list[TaskItem] | None:
        try:
            return await coordinator.client.async_get_tasks()
        except PiggyTaskApiError:
            return None

    _, initial_tasks = await asyncio.gather(
        coordinator.async_config_entry_first_refresh(), _fetch_initial_tasks()
    )

    platforms = list(PLATFORMS)
    tasks_coordinator: PiggyTaskTasksCoordinator | None = None
    if initial_tasks is not None:
        tasks_coordinator = PiggyTaskTasksCoordinator(hass, coordinator.client)
        tasks_coordinator.async_set_updated_data(initial_tasks)
        platforms.append(TODO_PLATFORM)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "counts": coordinator,
        "tasks": tasks_coordinator,
        "platforms": platforms,
    }
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    platforms = data["platforms"] if data else PLATFORMS
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
