"""Options flow for Default Config Manager."""

from __future__ import annotations

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
            return self.async_create_entry(title="", data=user_input)

        hass = self.hass

        # Read configuration state safely
        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        disabled_components = self._config_entry.options.get(CONF_COMPONENTS_TO_DISABLE, [])
        yaml_config_enabled = hass.data.setdefault(DOMAIN, {}).get("yaml_config", False)

        # Evaluate operating mode
        if yaml_config_enabled:
            mode_code = MODE_1
        elif advanced_mode:
            mode_code = MODE_3
        else:
            mode_code = MODE_2

        mode_display = MODE_DISPLAY[mode_code]
        default_config_version = await get_default_config_version(hass)

        schema_dict = {}
        status_message = ""

        # Build UI layout based on mode context
        if mode_code == MODE_1:
            status_message = "⚠️ **To manage integrations, remove `default_config:` from your configuration.yaml file.**"
            
        elif mode_code == MODE_2:
            status_message = "Status list placeholder (Managed Read-Only)"
            schema_dict[vol.Optional(CONF_ADVANCED_MODE, default=advanced_mode)] = bool
            
        elif mode_code == MODE_3:
            status_message = "Status list placeholder (Managed Advanced)"
            static_integrations = await get_static_integrations(hass)
            
            schema_dict[vol.Optional(CONF_ADVANCED_MODE, default=advanced_mode)] = bool
            schema_dict[vol.Optional(
                CONF_COMPONENTS_TO_DISABLE,
                default=disabled_components,
            )] = cv.multi_select({item: item for item in static_integrations})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "mode_display": mode_display,
                "default_config_version": default_config_version,
                "status_message": status_message,
            },
        )
