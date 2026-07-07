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
            selected_mode = user_input.get("mode_section", {}).get("mode_dropdown")
            is_advanced = (int(selected_mode) == MODE_3)
            
            was_advanced = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
            
            # INTERCEPT 1: Route to disclaimer if switching TO Advanced Mode
            if is_advanced and not was_advanced:
                _LOGGER.debug("Switching to Advanced mode. Routing to disclaimer step.")
                return await self.async_step_disclaimer()
                
            # INTERCEPT 2: Route to info message if switching FROM Advanced Mode back to Managed
            if not is_advanced and was_advanced:
                _LOGGER.debug("Switching to Managed mode. Routing to info step.")
                return await self.async_step_revert_basic()
            
            save_data = {CONF_ADVANCED_MODE: is_advanced}
            
            _LOGGER.debug("Saving options for init_managed with data=%s", save_data)
            return self.async_create_entry(title="Options", data=save_data)

        hass = self.hass

        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        current_mode_code = MODE_3 if advanced_mode else MODE_2
        
        default_config_version = await get_default_config_version(hass)
        static_integrations = await get_static_integrations(hass)
        
        running_integrations = [comp for comp in static_integrations if comp in hass.config.components]
        
        # Calculate totals and format the string with markdown
        running_count = len(running_integrations)
        total_count = len(static_integrations)
        count_text = f"{running_count} / {total_count}"
        components_list = ", ".join(running_integrations)
        
        active_components_text = f"**{running_count}** / {total_count} active\n\n{components_list}"

        schema_dict = {
            vol.Required("mode_section"): section(
                vol.Schema(
                    {
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
                    }
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
                "default_config_version": default_config_version,
                "count_text": count_text,
                "components_list": components_list,
            },
        )

    async def async_step_disclaimer(self, user_input: dict[str, Any] | None = None):
        """Handle the mandatory disclaimer step for Advanced Mode."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input.get("acknowledge"):
                _LOGGER.debug("Disclaimer acknowledged. Saving Advanced Mode options.")
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
            _LOGGER.debug("Revert to basic acknowledged. Saving Managed Mode options.")
            return self.async_create_entry(title="Options", data={CONF_ADVANCED_MODE: False})

        # Empty schema renders as a simple message with a Submit button
        return self.async_show_form(
            step_id="revert_basic",
            data_schema=vol.Schema({}),
        )
