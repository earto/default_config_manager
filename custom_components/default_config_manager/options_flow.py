"""Options flow for Default Config Manager."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    MODE_1,
    MODE_2,
    MODE_3,
    MODE_DISPLAY,
)
from .helpers import get_static_integrations, get_default_config_version

_LOGGER = logging.getLogger(__name__)


class DefaultConfigManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Default Config Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """First step dispatcher to routing methods."""
        yaml_config_enabled = "default_config" in self.hass.config.components
        _LOGGER.debug(
            "options_flow async_step_init called: yaml_config_enabled=%s", 
            yaml_config_enabled
        )
        
        if yaml_config_enabled:
            return await self.async_step_init_yaml(user_input)
        return await self.async_step_init_managed(user_input)

    async def async_step_init_yaml(self, user_input: dict[str, Any] | None = None):
        """Handle options step for Mode 1 (YAML mode)."""
        _LOGGER.debug("options_flow async_step_init_yaml called, user_input=%s", user_input)

        if user_input is not None:
            _LOGGER.debug("Closing YAML options flow.")
            return self.async_create_entry(title="Options", data={})

        hass = self.hass
        default_config_version = await get_default_config_version(hass)

        # Ensure default and value are cast to strings
        schema_dict = {
            vol.Required(
                "mode_dropdown",
                default=str(MODE_1),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=str(MODE_1), label=MODE_DISPLAY[MODE_1]),
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        return self.async_show_form(
            step_id="init_yaml",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": default_config_version,
            },
        )

    async def async_step_init_managed(self, user_input: dict[str, Any] | None = None):
        """Handle options step for Modes 2 & 3 (Managed/Advanced modes)."""
        _LOGGER.debug("options_flow async_step_init_managed called, user_input=%s", user_input)

        if user_input is not None:
            # Cast the string input back to int before comparing to int
            selected_mode = user_input.get("mode_dropdown")
            is_advanced = (int(selected_mode) == MODE_3)
            
            save_data = {CONF_ADVANCED_MODE: is_advanced}
            
            _LOGGER.debug("Saving options for init_managed with data=%s", save_data)
            return self.async_create_entry(title="Options", data=save_data)

        hass = self.hass

        # Read existing boolean to set visual default
        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        current_mode_code = MODE_3 if advanced_mode else MODE_2
        
        default_config_version = await get_default_config_version(hass)
        static_integrations = await get_static_integrations(hass)
        
        active_components_text = "\n".join(static_integrations)

        schema_dict = {
            vol.Required(
                "mode_dropdown",
                default=str(current_mode_code),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=str(MODE_2), label=MODE_DISPLAY[MODE_2]),
                        SelectOptionDict(value=str(MODE_3), label=MODE_DISPLAY[MODE_3]),
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                "integration_list",
                default=active_components_text,
            ): TextSelector(
                TextSelectorConfig(
                    type=TextSelectorType.TEXT,
                )
            ),
        }

        return self.async_show_form(
            step_id="init_managed",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": default_config_version,
            },
        )
