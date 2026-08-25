"""Config flow for PiggyTask."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PiggyTaskApiClient, PiggyTaskAuthError, PiggyTaskConnectionError
from .const import CONF_API_TOKEN, CONF_BASE_URL, DEFAULT_BASE_URL, DOMAIN

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
