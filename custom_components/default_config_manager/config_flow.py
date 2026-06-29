"""Config flow for Default Config Manager integration."""

from __future__ import annotations
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_COMPONENTS_TO_DISABLE,
    CONF_ADVANCED_MODE,
    DOMAIN,
    NAME,
)
from .helpers import get_default_config_components


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Default Config Manager."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title=NAME, data=user_input)

        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Default Config Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        # Read current options
        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        disabled_components = self._config_entry.options.get(
            CONF_COMPONENTS_TO_DISABLE, []
        )

        # Detect if default_config is still enabled in YAML
        yaml_config = self.hass.data.get("yaml_config", {})
        default_config_enabled = "default_config" in yaml_config

        # Get static default_config components from manifest (always the same set)
        static_components = await self.hass.async_add_executor_job(
            get_default_config_components
        )

        # Determine running components (status list only shows running ones)
        running_components = sorted(
            c for c in self.hass.config.components if c in static_components
        )

        # For now, treat all running static components as "static" section.
        # Conditional integrations (non-static but loaded via discovery) can be
        # added later by extending this logic.
        static_running = running_components
        conditional_running: list[str] = []

        # Build status text (two sections, running only)
        static_status_lines = [
            f"- {component}" for component in static_running
        ] or ["(none)"]
        conditional_status_lines = [
            f"- {component}" for component in conditional_running
        ] or ["(none)"]

        status_text = (
            "Static default_config integrations (running):\n"
            + "\n".join(static_status_lines)
            + "\n\nConditional integrations (running):\n"
            + "\n".join(conditional_status_lines)
        )

        # Handle user input
        if user_input is not None:
            new_advanced = user_input.get(CONF_ADVANCED_MODE, False)

            # First-time enable of advanced mode: show warning
            if new_advanced and not advanced_mode:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_schema(
                        default_config_enabled=default_config_enabled,
                        advanced_mode=new_advanced,
                        static_components=static_components,
                        disabled_components=disabled_components,
                    ),
                    description_placeholders={
                        "default_config_version": HA_VERSION,
                        "status": status_text,
                    },
                    errors={"base": "advanced_warning"},
                )

            # Persist options
            return self.async_create_entry(title="", data=user_input)

        # Initial form display
        return self.async_show_form(
            step_id="init",
            data_schema=self._build_schema(
                default_config_enabled=default_config_enabled,
                advanced_mode=advanced_mode,
                static_components=static_components,
                disabled_components=disabled_components,
            ),
            description_placeholders={
                "default_config_version": HA_VERSION,
                "status": status_text,
            },
            errors={"base": "default_config_enabled" if default_config_enabled else None},
        )

    def _build_schema(
        self,
        *,
        default_config_enabled: bool,
        advanced_mode: bool,
        static_components: list[str],
        disabled_components: list[str],
    ) -> vol.Schema:
        """Build the options schema for all modes."""
        # Mode 1: Basic (Config File) – default_config still in YAML
        if default_config_enabled:
            return vol.Schema(
                {
                    vol.Optional(
                        CONF_ADVANCED_MODE,
                        default=False,
                    ): cv.boolean,
                }
            )

        # Mode 2: Basic (Managed) – default_config removed, advanced off
        if not advanced_mode:
            return vol.Schema(
                {
                    vol.Optional(
                        CONF_ADVANCED_MODE,
                        default=False,
                    ): cv.boolean,
                }
            )

        # Mode 3: Advanced (Managed) – default_config removed, advanced on
        return vol.Schema(
            {
                vol.Optional(
                    CONF_ADVANCED_MODE,
                    default=True,
                ): cv.boolean,
                vol.Optional(
                    CONF_COMPONENTS_TO_DISABLE,
                    default=disabled_components,
                ): cv.multi_select(static_components),
            }
        )
