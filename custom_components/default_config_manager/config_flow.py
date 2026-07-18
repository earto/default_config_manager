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
from .helpers import get_default_config_version, get_static_integrations
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
            _LOGGER.debug("Creating config entry with options=%s", user_input)
            return self.async_create_entry(
                title=NAME,
                data={},
                options={
                    CONF_ADVANCED_MODE: False,
                },
            )

        # The Unified Source of Truth: Query the live registry directly
        yaml_config_enabled = "default_config" in self.hass.config.components
        _LOGGER.debug("default_config loaded by YAML=%s", yaml_config_enabled)
        
        mode_code = MODE_1 if yaml_config_enabled else MODE_2
        mode_display = MODE_DISPLAY[mode_code]
        
        default_config_version = await get_default_config_version(self.hass)
        _LOGGER.debug("default_config version=%s", default_config_version)

        # Generate the CSV list of active integrations for the UI description
        components = await get_static_integrations(self.hass)
        active_components_csv = ", ".join(components)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "default_config_version": default_config_version,
                "status": mode_display,
                "active_components": active_components_csv,
            },
        )
