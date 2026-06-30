# config_flow.py

from __future__ import annotations

from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    NAME,
    CONF_ADVANCED_MODE,
    CONF_COMPONENTS_TO_DISABLE,
)
from .helpers import get_static_integrations
from .options_flow import DefaultConfigManagerOptionsFlow

import logging
_LOGGER = logging.getLogger(__name__)


class DefaultConfigManagerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Default Config Manager."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Create the options flow."""
        _LOGGER.debug(
            "config_flow async_get_options_flow called for entry_id=%s",
            config_entry.entry_id,
        )
        return DefaultConfigManagerOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        _LOGGER.debug("config_flow async_step_user called, user_input=%s", user_input)

        if user_input is not None:
            _LOGGER.debug("Creating config entry with options=%s", user_input)
            return self.async_create_entry(
                title=NAME,
                data={},
                options={
                    CONF_ADVANCED_MODE: user_input.get(CONF_ADVANCED_MODE, False),
                    CONF_COMPONENTS_TO_DISABLE: user_input.get(
                        CONF_COMPONENTS_TO_DISABLE, []
                    ),
                },
            )

        return await self._show_form()

    async def _show_form(self):
        """Show the configuration form."""
        _LOGGER.debug("config_flow _show_form called")

        static_integrations = await get_static_integrations(self.hass)
        _LOGGER.debug("static_integrations=%s", static_integrations)

        schema = vol.Schema(
            {
                vol.Optional(CONF_ADVANCED_MODE, default=False): bool,
                vol.Optional(CONF_COMPONENTS_TO_DISABLE, default=[]): cv.multi_select(
                    {item: item for item in static_integrations}
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )
