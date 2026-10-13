"""Config flow for PiggyTask."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PiggyTaskApiClient, PiggyTaskAuthError, PiggyTaskConnectionError
from .const import (
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DOMAIN,
    SCAN_INTERVAL_CHOICES_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
    }
)


class PiggyTaskConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PiggyTask (single step: paste API token)."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PiggyTaskOptionsFlow:
        return PiggyTaskOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = PiggyTaskApiClient(
                session, user_input[CONF_BASE_URL], user_input[CONF_API_TOKEN]
            )
            try:
                result = await client.async_get_task_counts()
            except PiggyTaskAuthError:
                errors["base"] = "invalid_auth"
            except PiggyTaskConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - defensive, surfaces as "unknown" in the UI
                _LOGGER.exception("Unexpected error validating PiggyTask token")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(result.family_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=result.family_name or "PiggyTask",
                    data=user_input,
                )

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)


class PiggyTaskOptionsFlow(config_entries.OptionsFlow):
    """Let the user pick how often PiggyTask is polled."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # Not `self.config_entry`: newer Home Assistant sets that itself and
        # rejects assigning it, older versions (hacs.json: 2024.1) lack it.
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = int(
            self._entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES)
        )
        if current not in SCAN_INTERVAL_CHOICES_MINUTES:
            current = DEFAULT_SCAN_INTERVAL_MINUTES
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): vol.In(
                    SCAN_INTERVAL_CHOICES_MINUTES
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
