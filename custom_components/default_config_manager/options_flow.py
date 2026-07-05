"""Options flow for Default Config Manager."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

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

    async def async_step_init_managed(self, user_input: dict[str, Any] | None = None):
        """Handle options step for Modes 2 & 3 (Managed/Advanced modes)."""
        _LOGGER.debug("options_flow async_step_init_managed called, user_input=%s", user_input)

        if user_input is not None:
            # Strip the UI-only elements before saving
            data = {k: v for k, v in user_input.items() if k not in ["mode", "integration_list"]}
            _LOGGER.debug("Saving options for init_managed with user_input=%s", data)
            return self.async_create_entry(title="Options", data=data)

        hass = self.hass

        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        mode_code = MODE_3 if advanced_mode else MODE_2
        mode_display = MODE_DISPLAY[mode_code]
        
        default_config_version = await get_default_config_version(hass)
        static_integrations = await get_running_integrations(hass)
        active_components_csv = ", ".join(static_integrations)

        schema_dict = {
            vol.Optional(
                "mode",
                description={"suggested_value": mode_display},
            ): str,
            vol.Optional(
                CONF_ADVANCED_MODE,
                default=advanced_mode,
            ): bool,
            vol.Optional("integration_list"): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                    multiline=True,
                )
            ),
        }

        return self.async_show_form(
            step_id="init_managed",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": default_config_version,
                "status": mode_display,
                "integration_list": active_components_csv,
            },
        )
