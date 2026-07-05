"""Init for Default Config Manager."""

from __future__ import annotations

import asyncio
import logging

import homeassistant.components.default_config as ha_default_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component

from .const import (
    DOMAIN,
    CONF_ADVANCED_MODE,
    MODE_1,
    MODE_2,
    MODE_3,
)
from .helpers import get_static_integrations

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


def _create_restart_issue(hass: HomeAssistant) -> None:
    ir.async_create_issue(
        hass,
        DOMAIN,
        "restart_required",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="restart_required",
    )


def _delete_restart_issue(hass: HomeAssistant) -> None:
    ir.async_delete_issue(hass, DOMAIN, "restart_required")


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Default Config Manager integration."""
    _LOGGER.debug("Setting up Default Config Manager")

    _delete_restart_issue(hass)

    yaml_config_enabled = "default_config" in hass.config.components
    components = await get_static_integrations(hass)
    
    advanced_mode = False
    disabled_components: list[str] = []

    # Read config entries and check device registry native states
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.options.get(CONF_ADVANCED_MODE, False):
            advanced_mode = True
            device_registry = dr.async_get(hass)
            
            # The Registry Lookup: Find which proxy devices the user disabled natively
            for component in components:
                device = device_registry.async_get_device(
                    identifiers={(DOMAIN, f"{entry.entry_id}_{component}")}
                )
                if device and device.disabled_by:
                    disabled_components.append(component)

    if yaml_config_enabled:
        mode_code = MODE_1
    elif advanced_mode:
        mode_code = MODE_3
    else:
        mode_code = MODE_2

    _LOGGER.info("Default Config Manager running in mode_code=%s", mode_code)

    if mode_code == MODE_1:
        return True

    if mode_code == MODE_2:
        enabled_components = components
    else:
        enabled_components = [c for c in components if c not in disabled_components]
        _LOGGER.debug("Mode 3 native disabled components: %s", disabled_components)

    setup_tasks = []
    for component in enabled_components:
        setup_tasks.append(async_setup_component(hass, component, config))

    if setup_tasks:
        await asyncio.gather(*setup_tasks)

    await ha_default_config.async_setup(hass, config)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry for Default Config Manager."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry for Default Config Manager."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Options updated. Creating restart issue to apply changes.")
    
    # Whenever the user toggles Advanced Mode, require a restart
    _create_restart_issue(hass)
    
    # Reload the config entry to trigger sensor.py cleanup/generation immediately
    await hass.config_entries.async_reload(entry.entry_id)
