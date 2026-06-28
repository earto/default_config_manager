from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class DefaultConfigManagerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Default Config Manager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        # Single instance – if one exists, abort
        existing_entries = self._async_current_entries()
        if existing_entries:
            return self.async_abort(reason="single_instance_allowed")

        return self.async_create_entry(
            title="Default Config Manager",
            data={},
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Default Config Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # Important: do NOT assign to self.config_entry (read‑only property)
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Store options on the config entry
            return self.async_create_entry(title="", data=user_input)

        # Build your options schema here (placeholder for now)
        return self.async_show_form(
            step_id="init",
            data_schema=None,  # replace with actual vol.Schema when you’re ready
        )

