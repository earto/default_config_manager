"""config_flow.py for Default Config Manager."""

from __future__ import annotations

from typing import Any
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry

from .const import (
    DOMAIN,
    NAME,
    CONF_ADVANCED_MODE,
    MODE_1,
    MODE_2,
    MODE_DISPLAY,
)
from .helpers import get_default_config_version, get_standard_integrations
from .options_flow import DefaultConfigManagerOptionsFlow

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
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        _LOGGER.debug("config_flow async_step_user called, user_input=%s", user_input)

        if user_input is not None:
            # Capture the state of the Advanced Mode checkbox
            is_advanced = user_input.get("enable_advanced_mode", False)
            _LOGGER.debug("Creating config entry with options={CONF_ADVANCED_MODE: %s}", is_advanced)
            
            return self.async_create_entry(
                title=NAME,
                data={},
                options={
                    CONF_ADVANCED_MODE: is_advanced,
                },
            )

        # Query the registry for default_config
        yaml_config_enabled = "default_config" in self.hass.config.components
        _LOGGER.debug("default_config loaded by YAML=%s", yaml_config_enabled)
        
        mode_code = MODE_1 if yaml_config_enabled else MODE_2
        mode_display = MODE_DISPLAY[mode_code]
        
        default_config_version = await get_default_config_version(self.hass)
        _LOGGER.debug("default_config version=%s", default_config_version)

        # Get the standard integrations to count them for the UI
        integrations = await get_standard_integrations(self.hass)
        total_integrations = len(integrations)

        # Show the form with the checkbox and the exact placeholders for en.json
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional("enable_advanced_mode", default=False): bool,
            }),
            description_placeholders={
                "default_config_version": default_config_version,
                "total_integrations": str(total_integrations),
            },
        )
