"""config_flow.py for Default Config Manager."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant import config_entries

from .const import (
    DOMAIN,
    NAME,
    CONF_ADVANCED_MODE,
    CONF_COMPONENTS_TO_DISABLE,
)
from .helpers import get_static_integrations


class DefaultConfigManagerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Default Config Manager."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""

        if user_input is not None:
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

        static_integrations = await get_static_integrations(self.hass)

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

    async def async_step_options(self, user_input=None):
        """Handle options flow."""
        return await self.async_step_user(user_input)
