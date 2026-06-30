"""__init__.py for Default Config Manager."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .helpers import get_static_integrations, get_conditional_integrations
from .repairs import create_integration_change_issue, clear_integration_change_issue
from .options_flow import DefaultConfigManagerOptionsFlow

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Default Config Manager from a config entry."""
    _LOGGER.debug("async_setup_entry called for entry_id=%s", entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    yaml_config = hass.data.setdefault(DOMAIN, {}).get("yaml_config", False)
    _LOGGER.debug("yaml_config=%s", yaml_config)

    static_integrations = await get_static_integrations(hass)
    conditional_integrations = await get_conditional_integrations(hass)
    _LOGGER.debug("static_integrations=%s", static_integrations)
    _LOGGER.debug("conditional_integrations=%s", conditional_integrations)

    advanced_mode = entry.options.get("advanced_mode", False)
    disabled_components = entry.options.get("components_to_disable", [])
    _LOGGER.debug(
        "options loaded: advanced_mode=%s, disabled_components=%s",
        advanced_mode,
        disabled_components,
    )

    if yaml_config:
        _LOGGER.info("default_config is enabled in YAML; manager is inactive.")
        return True

    if advanced_mode:
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


async def async_get_options_flow(config_entry: ConfigEntry):
    """Return the options flow handler."""
    _LOGGER.debug("async_get_options_flow called for entry_id=%s", config_entry.entry_id)
    return DefaultConfigManagerOptionsFlow(config_entry)
