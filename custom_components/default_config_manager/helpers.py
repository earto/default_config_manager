"""Helpers for Default Config Manager."""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import List
import homeassistant.components as ha_components
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration
from .const import (
    DOMAIN,
    CONFIG_STATE_MODE_0,
    CONFIG_STATE_MODE_1_STANDARD_ONLY,
    CONFIG_STATE_MODE_1_BOTH,
    CONFIG_STATE_CORRECT,
)

_LOGGER = logging.getLogger(__name__)


async def get_standard_integrations(hass: HomeAssistant) -> List[str]:
    """Return the list of standard default_config integrations."""
    try:
        default_config = await async_get_integration(hass, "default_config")
        return sorted(default_config.dependencies)
    except Exception as err:
        _LOGGER.error("Failed to load default_config manifest: %s", err)
        return []


async def get_default_config_version(hass: HomeAssistant) -> str:
    """Return the Home Assistant Core version."""
    try:
        return hass.config.as_dict().get("version", "unknown")
    except Exception as err:
        _LOGGER.error("Failed to read HA core version: %s", err)
        return "unknown"


async def async_get_config_file_state(hass: HomeAssistant) -> str:
    """Determine configuration.yaml state for display in config_flow.py."""
    yaml_config_enabled = "default_config" in hass.config.components
    launched_via_yaml = hass.data.get(DOMAIN, {}).get("launched_via_yaml", False)

    if yaml_config_enabled and launched_via_yaml:
        return CONFIG_STATE_MODE_1_BOTH
    if yaml_config_enabled and not launched_via_yaml:
        return CONFIG_STATE_MODE_1_STANDARD_ONLY
    if not yaml_config_enabled and not launched_via_yaml:
        return CONFIG_STATE_MODE_0
    return CONFIG_STATE_CORRECT


async def async_get_config_flow_context(hass: HomeAssistant) -> dict:
    """Gather display data config_flow.py needs to render."""
    default_config_version = await get_default_config_version(hass)
    integrations = await get_standard_integrations(hass)

    return {
        "default_config_version": default_config_version,
        "total_integrations": len(integrations),
    }
