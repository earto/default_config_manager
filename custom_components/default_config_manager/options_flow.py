"""Options flow for Default Config Manager."""

from __future__ import annotations

from typing import Any

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

import logging

_LOGGER = logging.getLogger(__name__)


class DefaultConfigManagerOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Default Config Manager."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        _LOGGER.debug(
            "OptionsFlow __init__ called for entry_id=%s",
            config_entry.entry_id,
        )
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        _LOGGER.debug("OptionsFlow async_step_init called, user_input=%s", user_input)
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Options form."""
        _LOGGER.debug("OptionsFlow async_step_user called, user_input=%s", user_input)

        if user_input is not None:
            _LOGGER.debug("OptionsFlow creating entry with data=%s", user_input)
            return self.async_create_entry(
                title="Options",
                data=user_input,
            )

        hass = self._config_entry._hass

        advanced_mode = self._config_entry.options.get(CONF_ADVANCED_MODE, False)
        disabled_components = self._config_entry.options.get(
            CONF_COMPONENTS_TO_DISABLE,
            [],
        )

        yaml_config_enabled = hass.data.setdefault(DOMAIN, {}).get("yaml_config", False)
        _LOGGER.debug("OptionsFlow yaml_config_enabled=%s", yaml_config_enabled)

        # Determine internal mode code (1/2/3)
        if yaml_config_enabled:
            mode_code = MODE_1
        elif advanced_mode:
            mode_code = MODE_3
        else:
            mode_code = MODE_2

        mode_display = MODE_DISPLAY[mode_code]
        _LOGGER.debug(
            "OptionsFlow resolved mode_code=%s, mode_display=%s",
            mode_code,
            mode_display,
        )

        default_config_version = await get_default_config_version(hass)
        _LOGGER.debug(
            "OptionsFlow default_config_version=%s",
            default_config_version,
        )

        static_integrations = await get_static_integrations(hass)
        _LOGGER.debug("OptionsFlow static_integrations=%s", static_integrations)

        # Header fields: Mode first, Version second
        schema_dict: dict[Any, Any] = {
            vol.Optional(
                "mode",
                description={"suggested_value": mode_display},
            ): str,
            vol.Optional(
                "default_config version",
                description={"suggested_value": default_config_version},
            ): str,
        }

        # Advanced Options switch (Mode 2 & 3)
        if mode_code in (MODE_2, MODE_3):
            schema_dict[vol.Optional(
                "Advanced Options",
                default=advanced_mode,
            )] = bool

        # Disable list (Mode 3 only)
        if mode_code == MODE_3:
            schema_dict[vol.Optional(
                CONF_COMPONENTS_TO_DISABLE,
                default=disabled_components,
            )] = cv.multi_select({item: item for item in static_integrations})

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )
