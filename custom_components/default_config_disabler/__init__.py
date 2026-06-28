"""The Default Config Manager integration."""

from __future__ import annotations

import logging

import homeassistant.components.default_config as ha_default_config
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.typing import ConfigType
from homeassistant.setup import async_setup_component

from .const import CONF_COMPONENTS_TO_DISABLE, DOMAIN
from .helpers import get_default_config_components

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

    # Clear any stale restart-required issue
    _delete_restart_issue(hass)

    # Get the real default_config dependencies from its manifest
    _LOGGER.debug("Getting default_config dependencies from manifest")
    components = await hass.async_add_executor_job(get_default_config_components)
    _LOGGER.debug("Got default_config dependencies: %s", components)

    # Collect all disabled components from config entries
    disabled_components: list[str] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        disabled_components.extend(entry.options.get(CONF_COMPONENTS_TO_DISABLE, []))

    _LOGGER.debug("Disabled components: %s", disabled_components)

    # Filter out disabled components
    enabled_components = [c for c in components if c not in disabled_components]
    _LOGGER.debug("Enabled components to set up: %s", enabled_components)

    # Set up only the enabled components using HA's own setup mechanism
    for component in enabled_components:
        _LOGGER.debug("Setting up default_config dependency: %s", component)
        await async_setup_component(hass, component, config)

    _LOGGER.debug("Setup of default_config dependencies complete")

    # Run the built-in default_config's conditional setup logic
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
    # Nothing to unload explicitly; components are managed at startup
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.warning("Updated disabled components. Restart Home Assistant to apply changes")
    _create_restart_issue(hass)
