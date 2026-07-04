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
        """First step dispatcher to routing methods."""
        yaml_config_enabled = "default_config" in self.hass.config.components
        _LOGGER.debug(
            "options_flow async_step_init called: yaml_config_enabled=%s", 
            yaml_config_enabled
        )
        
        if yaml_config_enabled:
            return await self.async_step_init_yaml(user_input)
        return await self.async_step_init_managed(user_input)

    async def async_step_init_yaml(self, user_input=None):
        """Handle options step for Mode 1 (YAML mode)."""
        _LOGGER.debug("options_flow async_step_init_yaml called, user_input=%s", user_input)

        if user_input is not None:
            _LOGGER.debug("Saving options for init_yaml with user_input=%s", user_input)
            return self.async_create_entry(title="Options", data=user_input)

        hass = self.hass
        mode_display = MODE_DISPLAY[MODE_1]
        default_config_version = await get_default_config_version(hass)

        schema_dict = {
            vol.Optional(
                "mode",
                description={"suggested_value": mode_display},
            ): str,
        }

        return self.async_show_form(
            step_id="init_yaml",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": default_config_version,
                "status": mode_display,
            },
        )

    async def async_step_init_managed(self, user_input=None):
        """Handle options step for Modes 2 & 3 (Managed/Advanced modes)."""
        _LOGGER.debug("options_flow async_step_init_managed called, user_input=%s", user_input)

        if user_input is not None:
            _LOGGER.debug("Saving options for init_managed with user_input=%s", user_input)
            return self.async_create_entry(title="Options", data=user_input)

        hass = self.hass

        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        disabled_components = self._config_entry.options.get(
            CONF_COMPONENTS_TO_DISABLE,
            [],
        )

        mode_code = MODE_3 if advanced_mode else MODE_2
        mode_display = MODE_DISPLAY[mode_code]
        default_config_version = await get_default_config_version(hass)
        static_integrations = await get_static_integrations(hass)

        schema_dict = {
            vol.Optional(
                "mode",
                description={"suggested_value": mode_display},
            ): str,
            vol.Optional(
                CONF_ADVANCED_MODE,
                default=advanced_mode,
            ): bool,
        }

        if mode_code == MODE_3:
            schema_dict[vol.Optional(
                CONF_COMPONENTS_TO_DISABLE,
                default=disabled_components,
            )] = cv.multi_select({item: item for item in static_integrations})

        return self.async_show_form(
            step_id="init_managed",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": default_config_version,
                "status": mode_display,
            },
        )
