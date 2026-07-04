"""Init for Default Config Manager."""

from __future__ import annotations

import asyncio
import logging

import homeassistant.components.default_config as ha_default_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component

from .const import (
    CONF_COMPONENTS_TO_DISABLE,
    DOMAIN,
    CONF_ADVANCED_MODE,
    MODE_1,
    MODE_2,
    MODE_3,
)
from .helpers import get_static_integrations

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


def _filter_disabled_list(disabled: list[str], manifest: list[str]) -> list[str]:
    """Return only disabled items that still exist in the manifest."""
    return [c for c in disabled if c in manifest]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Default Config Manager integration."""
    _LOGGER.debug("Setting up Default Config Manager")

    # Clear any stale restart-required issue
    _delete_restart_issue(hass)

    # Detect YAML default_config (Mode 1)
    yaml_config_enabled = "default_config" in hass.config.components
    _LOGGER.debug("yaml_config_enabled=%s", yaml_config_enabled)

    # Determine mode
    advanced_mode = False
    disabled_components: list[str] = []

    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.options.get(CONF_ADVANCED_MODE, False):
            advanced_mode = True
        raw = entry.options.get(CONF_COMPONENTS_TO_DISABLE, [])
        disabled_components.extend(raw)

    if yaml_config_enabled:
        mode_code = MODE_1
    elif advanced_mode:
        mode_code = MODE_3
    else:
        mode_code = MODE_2

    _LOGGER.info("Default Config Manager running in mode_code=%s", mode_code)

    # Mode 1: YAML default_config → do nothing
    if mode_code == MODE_1:
        _LOGGER.info("default_config is enabled in YAML; manager is inactive.")
        return True

    # Get default_config dependencies from manifest (static integrations)
    _LOGGER.debug("Getting default_config dependencies from manifest")
    components = await get_static_integrations(hass)
    _LOGGER.debug("Got default_config dependencies: %s", components)

    # Validate disabled list
    disabled_components = _filter_disabled_list(disabled_components, components)
    _LOGGER.debug("Validated disabled components: %s", disabled_components)

    # Mode 2: Basic (Managed) → no disabling, just set up everything
    if mode_code == MODE_2:
        enabled_components = components
        _LOGGER.debug("Mode 2 enabled components: %s", enabled_components)

    # Mode 3: Advanced (Managed) → disable selected components
    else:
        enabled_components = [c for c in components if c not in disabled_components]
        _LOGGER.debug("Mode 3 enabled components: %s", enabled_components)
        _LOGGER.debug("Mode 3 disabled components: %s", disabled_components)

    # Set up only enabled components concurrently (same as factory startup)
    setup_tasks = []
    for component in enabled_components:
        _LOGGER.debug("Setting up default_config dependency: %s", component)
        setup_tasks.append(async_setup_component(hass, component, config))

    if setup_tasks:
        await asyncio.gather(*setup_tasks)

    _LOGGER.debug("Setup of default_config dependencies complete")

    # Run built-in default_config conditional setup
    _LOGGER.debug("Running built-in default_config conditional setup")
    await ha_default_config.async_setup(hass, config)

    _LOGGER.debug("Default Config Manager setup complete")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry for Default Config Manager."""
    _LOGGER.debug("Setting up Default Config Manager entry")
    entry.async_on_unload(entry.add_update_listener(update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry for Default Config Manager."""
    _LOGGER.debug("Unloading Default Config Manager entry")
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("Validating updated disabled components")

    components = await get_static_integrations(hass)

    raw = entry.options.get(CONF_COMPONENTS_TO_DISABLE, [])
    cleaned = _filter_disabled_list(raw, components)

    if cleaned != raw:
        _LOGGER.debug("Pruned invalid disabled components: %s", set(raw) - set(cleaned))
        hass.config_entries.async_update_entry(
            entry,
            options={CONF_COMPONENTS_TO_DISABLE: cleaned},
        )
