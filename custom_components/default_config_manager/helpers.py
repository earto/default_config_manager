"""Helpers for Default Config Manager."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

import homeassistant.components as ha_components
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

_LOGGER = logging.getLogger(__name__)


async def get_static_integrations(hass: HomeAssistant) -> List[str]:
    """Return the list of static default_config integrations."""
    try:
        default_config = await async_get_integration(hass, "default_config")
        return sorted(default_config.dependencies)
    except Exception as err:
        _LOGGER.error("Failed to load default_config manifest: %s", err)
        return []

    return await hass.async_add_executor_job(
        _load_default_config_dependencies,
        components_path,
    )


async def get_conditional_integrations(hass: HomeAssistant) -> List[str]:
    """Return conditional integrations enabled indirectly by default_config."""
    static_components = await get_static_integrations(hass)
    running_components = list(hass.config.components)

    return sorted(
        component
        for component in running_components
        if component not in static_components
    )


async def get_default_config_version(hass: HomeAssistant) -> str:
    """Return the Home Assistant Core version."""
    try:
        return hass.config.as_dict().get("version", "unknown")
    except Exception as err:
        _LOGGER.error("Failed to read HA core version: %s", err)
        return "unknown"
