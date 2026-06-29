"""Default Config Manager integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    CONF_COMPONENTS_TO_DISABLE,
    CONF_ADVANCED_MODE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration from YAML (only used to detect default_config)."""

    # Store YAML config so the options flow can detect if default_config is present
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["yaml_config"] = config

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Default Config Manager from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["entry"] = entry

    # Read options
    advanced_mode: bool = entry.options.get(CONF_ADVANCED_MODE, False)
    disabled_components: list[str] = entry.options.get(
        CONF_COMPONENTS_TO_DISABLE, []
    )

    # Apply disable rules only in advanced mode
    if advanced_mode and disabled_components:
        await _apply_disable_rules(hass, disabled_components)

    # Register reload handler
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    return True


async def async_update_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Handle options updates (reload logic)."""

    _LOGGER.debug("Default Config Manager: options updated, reloading disable rules")

    advanced_mode: bool = entry.options.get(CONF_ADVANCED_MODE, False)
    disabled_components: list[str] = entry.options.get(
        CONF_COMPONENTS_TO_DISABLE, []
    )

    if advanced_mode and disabled_components:
        await _apply_disable_rules(hass, disabled_components)
    else:
        _LOGGER.debug(
            "Default Config Manager: advanced mode disabled or no components selected"
        )


async def _apply_disable_rules(
    hass: HomeAssistant,
    disabled_components: list[str],
) -> None:
    """Disable selected default_config components."""

    if not disabled_components:
        return

    for component in disabled_components:
        if component in hass.config.components:
            _LOGGER.info(
                "Default Config Manager: disabling default_config component '%s'",
                component,
            )
            await _disable_component(hass, component)
        else:
            _LOGGER.debug(
                "Default Config Manager: component '%s' is not running; nothing to disable",
                component,
            )


async def _disable_component(hass: HomeAssistant, component: str) -> None:
    """Unload a running component cleanly."""

    unload_ok = await hass.config_entries.async_unload(component)

    if unload_ok:
        _LOGGER.info(
            "Default Config Manager: component '%s' unloaded successfully",
            component,
        )
    else:
        _LOGGER.warning(
            "Default Config Manager: failed to unload component '%s'",
            component,
        )

