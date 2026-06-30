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

import logging
_LOGGER = logging.getLogger(__name__)


class DefaultConfigManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Default Config Manager."""

    def __init__(self, config_entry):
        self.config_entry = config_entry
        _LOGGER.debug("OptionsFlow __init__ called for entry_id=%s", config_entry.entry_id)

    async def async_step_init(self, user_input=None):
        _LOGGER.debug("OptionsFlow async_step_init called, user_input=%s", user_input)
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Options form."""
        _LOGGER.debug("OptionsFlow async_step_user called, user_input=%s", user_input)

        if user_input is not None:
            _LOGGER.debug("OptionsFlow creating entry with data=%s", user_input)
            return self.async_create_entry(
                title="Options",
                data=user_input,
            )

        static_integrations = await get_static_integrations(self.config_entry.hass)
        _LOGGER.debug("static_integrations=%s", static_integrations)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_ADVANCED_MODE,
                    default=self.config_entry.options.get(CONF_ADVANCED_MODE, False),
                ): bool,
                vol.Optional(
                    CONF_COMPONENTS_TO_DISABLE,
                    default=self.config_entry.options.get(CONF_COMPONENTS_TO_DISABLE, []),
                ): cv.multi_select({item: item for item in static_integrations}),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )
