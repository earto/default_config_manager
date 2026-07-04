"""Options flow for Default Config Manager."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    CONF_COMPONENTS_TO_DISABLE,
    MODE_1,
    MODE_2,
    MODE_3,
    MODE_DISPLAY,
)
from .helpers import get_static_integrations, get_default_config_version

import logging

_LOGGER = logging.getLogger(__name__)


class DefaultConfigManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Default Config Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """First step."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle user options step."""
        if user_input is not None:
            return self.async_create_entry(title="Options", data=user_input)

        hass = self.hass

        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        disabled_components = self._config_entry.options.get(
            CONF_COMPONENTS_TO_DISABLE,
            [],
        )

        yaml_config_enabled = hass.data.setdefault(DOMAIN, {}).get("yaml_config", False)

        # Mode detection
        if yaml_config_enabled:
            mode_code = MODE_1
        elif advanced_mode:
            mode_code = MODE_3
        else:
            mode_code = MODE_2

        mode_display = MODE_DISPLAY[mode_code]
        default_config_version = await get_default_config_version(hass)
        static_integrations = await get_static_integrations(hass)

        schema_dict = {
            vol.Optional(
                "mode",
                description={"suggested_value": mode_display},
            ): str,
        }

        if mode_code in (MODE_2, MODE_3):
            schema_dict[vol.Optional(
                CONF_ADVANCED_MODE,
                default=advanced_mode,
            )] = bool

        if mode_code == MODE_3:
            schema_dict[vol.Optional(
                CONF_COMPONENTS_TO_DISABLE,
                default=disabled_components,
            )] = cv.multi_select({item: item for item in static_integrations})

        note_text = ""
        if mode_code == MODE_1:
            note_text = "\n\nNOTE: Default Config Manager is ready to manage your default_config. Remove default_config from your configuration file and restart Home Assistant to enable management."

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": default_config_version,
                "status": mode_display,
                "note": note_text,
            },
        )
