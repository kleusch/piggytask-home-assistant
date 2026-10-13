"""The PiggyTask integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS, TODO_PLATFORM
from .coordinator import PiggyTaskCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PiggyTask from a config entry.

    Every token can read task counts (sensors). Whether it can also list/complete
    tasks depends on the scope chosen when the token was created in PiggyTask (and
    on Premium); the first poll tells — `tasks` is None for a counts-only token,
    which then gets no todo platform.
    """
    coordinator = PiggyTaskCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    platforms = list(PLATFORMS)
    if coordinator.data.tasks is not None:
        platforms.append(TODO_PLATFORM)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "counts": coordinator,
        "platforms": platforms,
    }
    await hass.config_entries.async_forward_entry_setups(entry, platforms)
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_options_change))
    return True


async def _async_reload_on_options_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply a changed polling interval."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    platforms = data["platforms"] if data else PLATFORMS
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
