"""config_flow.py for Default Config Manager."""
from __future__ import annotations
from typing import Any
import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from .const import DOMAIN, NAME, CONF_ADVANCED_MODE, CONFIG_FILE_STATE_DISPLAY
from .helpers import (
    async_get_config_file_state,
    async_get_config_flow_context,
)
from .options_flow import DefaultConfigManagerOptionsFlow

_LOGGER = logging.getLogger(__name__)

_STATE_TO_STEP = {
    "mode_0": "user_mode_0",
    "mode_1_standard_only": "user_mode_1_standard_only",
    "mode_1_both": "user_mode_1_both",
    "correct": "user_correct",
}


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
        """Dispatch to the correct step based on configuration.yaml state."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        state = await async_get_config_file_state(self.hass)
        _LOGGER.debug("config_flow detected config_file_state=%s", state)

        step_name = _STATE_TO_STEP[state]
        return await getattr(self, f"async_step_{step_name}")(user_input)

    async def async_step_user_mode_0(self, user_input: dict[str, Any] | None = None):
        return await self._async_show_state_form(user_input, "user_mode_0", "mode_0")

    async def async_step_user_mode_1_standard_only(self, user_input: dict[str, Any] | None = None):
        return await self._async_show_state_form(user_input, "user_mode_1_standard_only", "mode_1_standard_only")

    async def async_step_user_mode_1_both(self, user_input: dict[str, Any] | None = None):
        return await self._async_show_state_form(user_input, "user_mode_1_both", "mode_1_both")

    async def async_step_user_correct(self, user_input: dict[str, Any] | None = None):
        return await self._async_show_state_form(user_input, "user_correct", "correct")

    async def _async_show_state_form(
        self, user_input: dict[str, Any] | None, step_id: str, state: str
    ):
        """Shared form logic for all config-file-state variants."""
        if user_input is not None:
            _LOGGER.debug("Creating config entry (config_file_state=%s)", state)
            return self.async_create_entry(
                title=NAME,
                data={},
                options={
                    CONF_ADVANCED_MODE: False,
                },
            )

        ctx = await async_get_config_flow_context(self.hass)

        schema = vol.Schema({
            vol.Required(
                "config_file_state",
                default=state,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=state, label=CONFIG_FILE_STATE_DISPLAY[state]),
                    ],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        })

        return self.async_show_form(
            step_id=step_id,
            data_schema=schema,
            description_placeholders={
                "default_config_version": ctx["default_config_version"],
                "total_integrations": str(ctx["total_integrations"]),
            },
        )
