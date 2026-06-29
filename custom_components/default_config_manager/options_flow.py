"""options_flow.py for Default Config Manager."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    CONF_COMPONENTS_TO_DISABLE,
)
from .helpers import get_static_integrations


class DefaultConfigManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Default Config Manager."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Options form."""

        if user_input is not None:
            return self.async_create_entry(
                title="Options",
                data=user_input,
            )

        static_integrations = await get_static_integrations(self.config_entry.hass)

        schema = vol.Schema(
            {
                vol.Optional(CONF_ADVANCED_MODE, default=self.config_entry.options.get(CONF_ADVANCED_MODE, False)): bool,
                vol.Optional(CONF_COMPONENTS_TO_DISABLE, default=self.config_entry.options.get(CONF_COMPONENTS_TO_DISABLE, [])): cv.multi_select(
                    {item: item for item in static_integrations}
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )
