"""Init for Default Config Manager."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.loader import async_get_integration

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    CONF_COMPONENTS_TO_DISABLE,
    MODE_1,
    MODE_2,
    MODE_3,
)
from .helpers import get_static_integrations, get_conditional_integrations
from .repairs import create_integration_change_issue, clear_integration_change_issue

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Default Config Manager from a config entry."""
    _LOGGER.debug("async_setup_entry called for entry_id=%s", entry.entry_id)

    entry._hass = hass
    entry.async_on_unload(entry.add_update_listener(update_listener))

    # NOTE: yaml_config is only read here; something else must set hass.data[DOMAIN]["yaml_config"]
    yaml_config = hass.data.setdefault(DOMAIN, {}).get("yaml_config", False)
    _LOGGER.debug("yaml_config=%s", yaml_config)

    static_integrations = await get_static_integrations(hass)
    conditional_integrations = await get_conditional_integrations(hass)
    _LOGGER.debug("static_integrations=%s", static_integrations)
    _LOGGER.debug("conditional_integrations=%s", conditional_integrations)

    advanced_mode = entry.options.get(CONF_ADVANCED_MODE, False)
    disabled_components = entry.options.get(CONF_COMPONENTS_TO_DISABLE, [])
    _LOGGER.debug(
        "options loaded: advanced_mode=%s, disabled_components=%s",
        advanced_mode,
        disabled_components,
    )

    # Mode detection
    if yaml_config:
        mode_code = MODE_1
    elif advanced_mode:
        mode_code = MODE_3
    else:
        mode_code = MODE_2

    _LOGGER.info("Default Config Manager running in mode_code=%s", mode_code)

    if mode_code == MODE_1:
        _LOGGER.info("default_config is enabled in YAML; manager is inactive.")
        return True

    if mode_code == MODE_2:
        _LOGGER.info("Manager in Basic (Managed) mode; no component changes applied.")
        return True

    if mode_code == MODE_3:
        for component in static_integrations:
            if component in disabled_components:
                _LOGGER.info("Disabling default_config component: %s", component)
                clear_integration_change_issue(hass, component)

                integration = await async_get_integration(hass, component)
                result = await integration.async_unload()

                if result:
                    create_integration_change_issue(hass, component, "disabled")
                else:
                    _LOGGER.warning("Failed to unload component: %s", component)
            else:
                if component not in hass.config.components:
                    _LOGGER.info("Enabling default_config component: %s", component)
                    clear_integration_change_issue(hass, component)

                    result = await async_setup_component(hass, component, {})

                    if result:
                        create_integration_change_issue(hass, component, "enabled")
                    else:
                        _LOGGER.warning("Failed to set up component: %s", component)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Default Config Manager config entry."""
    _LOGGER.info("Unloading Default Config Manager")
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("update_listener triggered for entry_id=%s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
