"""Options flow for Default Config Manager."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    MODE_0,
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
        self.mode_code = MODE_2 # Default fallback

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """First step dispatcher, reading from established init state."""
        # Pull the mode that async_setup established
        self.mode_code = self.hass.data[DOMAIN].get(self._config_entry.entry_id, MODE_2)
        
        _LOGGER.debug("options_flow init: resolved mode_code=%s", self.mode_code)
        
        # Route based on the resolved mode_code
        if self.mode_code == MODE_0:
            return await self.async_step_init_unmanaged_mode_0(user_input)
        
        if self.mode_code == MODE_1:
            # Check YAML state to decide which Mode 1 sub-step to show
            factory_yaml_enabled = "default_config" in self.hass.config.components
            dcm_yaml_enabled = self.hass.data[DOMAIN].get("launched_via_yaml", False)
            
            if factory_yaml_enabled and dcm_yaml_enabled:
                return await self.async_step_init_unmanaged_mode_1_both(user_input)
            return await self.async_step_init_unmanaged_mode_1_factory_only(user_input)
            
        return await self.async_step_init_managed(user_input)

    async def async_step_init_unmanaged_mode_0(self, user_input: dict[str, Any] | None = None):
        """Handle landing step for Mode 0."""
        return await self._async_unmanaged_base_form(user_input, "init_unmanaged_mode_0")

    async def async_step_init_unmanaged_mode_1_factory_only(self, user_input: dict[str, Any] | None = None):
        """Handle landing step for Mode 1 (factory default config only)."""
        return await self._async_unmanaged_base_form(user_input, "init_unmanaged_mode_1_factory_only")

    async def async_step_init_unmanaged_mode_1_both(self, user_input: dict[str, Any] | None = None):
        """Handle landing step for Mode 1 (both integrations enabled)."""
        return await self._async_unmanaged_base_form(user_input, "init_unmanaged_mode_1_both")

    async def _async_unmanaged_base_form(self, user_input: dict[str, Any] | None, form_step: str):
        """Shared logic for all unmanaged options steps."""
        _LOGGER.debug("options_flow unmanaged form called, mode=%s, step=%s", self.mode_code, form_step)

        if user_input is not None:
            _LOGGER.debug("Closing Unmanaged options flow.")
            return self.async_create_entry(title="Options", data={})

        hass = self.hass
        default_config_version = await get_default_config_version(hass)
        static_integrations = await get_static_integrations(hass)
        total_count = len(static_integrations)

        schema_dict = {
            vol.Required(
                "mode_dropdown",
                default=str(self.mode_code),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=str(self.mode_code), label=MODE_DISPLAY[self.mode_code]),
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }

        return self.async_show_form(
            step_id=form_step,
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": str(default_config_version),
                "total_integrations": str(total_count),
            },
        )

    async def async_step_init_managed(self, user_input: dict[str, Any] | None = None):
        """Handle options step for Modes 2 & 3 (Managed/Advanced modes)."""
        _LOGGER.debug("options_flow async_step_init_managed called, user_input=%s", user_input)

        if user_input is not None:
            selected_mode = user_input.get("mode_dropdown")
            is_advanced = (int(selected_mode) == MODE_3)
            
            was_advanced = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
            
            if is_advanced and not was_advanced:
                return await self.async_step_disclaimer()
                
            if not is_advanced and was_advanced:
                return await self.async_step_revert_basic()
            
            save_data = {CONF_ADVANCED_MODE: is_advanced}
            return self.async_create_entry(title="Options", data=save_data)

        hass = self.hass
        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        current_mode_code = MODE_3 if advanced_mode else MODE_2
        
        default_config_version = await get_default_config_version(hass)
        static_integrations = await get_static_integrations(hass)
        
        running_integrations = [comp for comp in static_integrations if comp in hass.config.components]
        
        running_count = len(running_integrations)
        total_count = len(static_integrations)
        count_text = f"{running_count}/{total_count}"
        components_list = ", ".join(running_integrations)

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
            vol.Required("integrations_section"): section(
                vol.Schema({})
            ),
        }

        return self.async_show_form(
            step_id="init_managed",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "default_config_version": str(default_config_version),
                "total_integrations": str(total_count),
                "count_text": str(count_text),
                "components_list": str(components_list),
            },
        )

    async def async_step_disclaimer(self, user_input: dict[str, Any] | None = None):
        """Handle the mandatory disclaimer step for Advanced Mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("acknowledge"):
                return self.async_create_entry(title="Options", data={CONF_ADVANCED_MODE: True})
            
            errors["base"] = "must_acknowledge"

        return self.async_show_form(
            step_id="disclaimer",
            data_schema=vol.Schema(
                {
                    vol.Required("acknowledge", default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_revert_basic(self, user_input: dict[str, Any] | None = None):
        """Handle the informational step when reverting to Managed Mode."""
        if user_input is not None:
            return self.async_create_entry(title="Options", data={CONF_ADVANCED_MODE: False})

        return self.async_show_form(
            step_id="revert_basic",
            data_schema=vol.Schema({}),
        )
